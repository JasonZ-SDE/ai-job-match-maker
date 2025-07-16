#!/usr/bin/env python3
"""
Reset AI job scores and reasoning in the database.

This script removes all AI-generated scores, reasoning, and timestamps
from the job table, effectively resetting the scoring system.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_loader.load_jobs import Job, Base

# Load environment variables
load_dotenv(override=True)

console = Console()


class ScoreResetter:
    """Manages resetting AI scores and reasoning in the database."""
    
    def __init__(self):
        self.setup_database()
    
    def setup_database(self):
        """Initialize database connection."""
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PASSWORD')
        DB_HOST = os.getenv('DB_HOST')
        DB_PORT = os.getenv('DB_PORT')
        DB_NAME = os.getenv('DB_NAME')
        
        if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
            console.print("❌ Database environment variables not properly set", style="red")
            sys.exit(1)
        
        self.engine = create_engine(
            f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def get_scoring_stats(self) -> dict:
        """Get current scoring statistics."""
        total_jobs = self.session.query(Job).count()
        scored_jobs = self.session.query(Job).filter(Job.match_score.isnot(None)).count()
        
        return {
            "total_jobs": total_jobs,
            "scored_jobs": scored_jobs,
            "unscored_jobs": total_jobs - scored_jobs
        }
    
    def reset_all_scores(self) -> dict:
        """Reset all AI scores and reasoning in the database."""
        try:
            # Get stats before reset
            before_stats = self.get_scoring_stats()
            
            # Update all jobs to clear scoring fields
            stmt = update(Job).values(
                match_score=None,
                match_reasoning=None,
                scored_at=None
            )
            
            result = self.session.execute(stmt)
            self.session.commit()
            
            # Get stats after reset
            after_stats = self.get_scoring_stats()
            
            return {
                "success": True,
                "rows_updated": result.rowcount,
                "before_stats": before_stats,
                "after_stats": after_stats
            }
            
        except Exception as e:
            self.session.rollback()
            console.print(f"❌ Error resetting scores: {e}", style="red")
            return {
                "success": False,
                "error": str(e)
            }
    
    def reset_scores_by_criteria(self, min_score: int = None, max_score: int = None) -> dict:
        """Reset scores for jobs matching specific criteria."""
        try:
            # Build query based on criteria
            query = self.session.query(Job).filter(Job.match_score.isnot(None))
            
            if min_score is not None:
                query = query.filter(Job.match_score >= min_score)
            if max_score is not None:
                query = query.filter(Job.match_score <= max_score)
            
            # Count jobs that will be reset
            jobs_to_reset = query.count()
            
            if jobs_to_reset == 0:
                return {
                    "success": True,
                    "rows_updated": 0,
                    "message": "No jobs match the specified criteria"
                }
            
            # Update matching jobs
            stmt = update(Job).where(
                Job.match_score.isnot(None)
            ).values(
                match_score=None,
                match_reasoning=None,
                scored_at=None
            )
            
            if min_score is not None:
                stmt = stmt.where(Job.match_score >= min_score)
            if max_score is not None:
                stmt = stmt.where(Job.match_score <= max_score)
            
            result = self.session.execute(stmt)
            self.session.commit()
            
            return {
                "success": True,
                "rows_updated": result.rowcount,
                "jobs_to_reset": jobs_to_reset
            }
            
        except Exception as e:
            self.session.rollback()
            console.print(f"❌ Error resetting scores by criteria: {e}", style="red")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close(self):
        """Close database session."""
        self.session.close()


def main():
    """Main CLI interface for score resetting."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset AI job scores and reasoning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  reset_scores.py                    # Reset all scores (with confirmation)
  reset_scores.py --force            # Reset all scores without confirmation
  reset_scores.py --min-score 0      # Reset scores 0 and above
  reset_scores.py --max-score 3      # Reset scores 3 and below
  reset_scores.py --min-score 0 --max-score 3  # Reset scores 0-3
  reset_scores.py --stats            # Show current scoring statistics only
        """
    )
    
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompt")
    parser.add_argument("--min-score", type=int, choices=range(11),
                       help="Reset scores >= this value (0-10)")
    parser.add_argument("--max-score", type=int, choices=range(11),
                       help="Reset scores <= this value (0-10)")
    parser.add_argument("--stats", action="store_true",
                       help="Show current scoring statistics only")
    
    args = parser.parse_args()
    
    # Validate score range
    if args.min_score is not None and args.max_score is not None:
        if args.min_score > args.max_score:
            console.print("❌ min-score cannot be greater than max-score", style="red")
            sys.exit(1)
    
    resetter = ScoreResetter()
    
    try:
        # Show current statistics
        stats = resetter.get_scoring_stats()
        console.print(f"\n📊 Current Statistics:", style="blue bold")
        console.print(f"Total Jobs: {stats['total_jobs']}")
        console.print(f"Scored Jobs: {stats['scored_jobs']}")
        console.print(f"Unscored Jobs: {stats['unscored_jobs']}")
        
        if args.stats:
            return
        
        # Determine operation type
        if args.min_score is not None or args.max_score is not None:
            # Criteria-based reset
            criteria_desc = []
            if args.min_score is not None:
                criteria_desc.append(f"score >= {args.min_score}")
            if args.max_score is not None:
                criteria_desc.append(f"score <= {args.max_score}")
            criteria_str = " AND ".join(criteria_desc)
            
            console.print(f"\n🎯 Resetting scores for jobs with: {criteria_str}", style="yellow")
            
            if not args.force:
                if not Confirm.ask("Are you sure you want to reset these scores?"):
                    console.print("❌ Reset cancelled", style="red")
                    return
            
            result = resetter.reset_scores_by_criteria(args.min_score, args.max_score)
            
        else:
            # Reset all scores
            if stats['scored_jobs'] == 0:
                console.print("\n✅ No scored jobs to reset", style="green")
                return
            
            console.print(f"\n⚠️  About to reset ALL {stats['scored_jobs']} scored jobs", style="yellow bold")
            
            if not args.force:
                if not Confirm.ask("Are you sure you want to reset ALL scores?"):
                    console.print("❌ Reset cancelled", style="red")
                    return
            
            result = resetter.reset_all_scores()
        
        # Display results
        if result["success"]:
            console.print(f"\n✅ Successfully reset {result['rows_updated']} job scores", style="green bold")
            
            # Show updated stats if full reset
            if "after_stats" in result:
                console.print(f"📊 After Reset - Scored Jobs: {result['after_stats']['scored_jobs']}")
        else:
            console.print(f"\n❌ Reset failed: {result.get('error', 'Unknown error')}", style="red")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n❌ Reset cancelled by user", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        sys.exit(1)
    finally:
        resetter.close()


if __name__ == "__main__":
    main()