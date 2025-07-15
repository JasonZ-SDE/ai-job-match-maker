import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from data_loader.load_jobs import Job, Base
from user_profile.profile_manager import ProfileManager
from ai_agent.job_matcher import JobMatcher, JobMatchResult

load_dotenv(override=True)

console = Console()


class ScoringWorkflow:
    """Manages the workflow for scoring jobs using AI analysis."""
    
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.setup_database()
        self.job_matcher = JobMatcher()
        self.profile_manager = ProfileManager()
        
    def setup_database(self):
        """Initialize database connection."""
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PASSWORD')
        DB_HOST = os.getenv('DB_HOST')
        DB_PORT = os.getenv('DB_PORT')
        DB_NAME = os.getenv('DB_NAME')
        
        self.engine = create_engine(
            f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def get_unscored_jobs(self, limit: Optional[int] = None) -> List[Job]:
        """Get jobs that haven't been scored yet."""
        query = self.session.query(Job).filter(Job.match_score.is_(None))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_jobs_for_rescoring(self, limit: Optional[int] = None) -> List[Job]:
        """Get all jobs for re-scoring (regardless of current score)."""
        query = self.session.query(Job)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update_job_score(self, job: Job, result: JobMatchResult) -> None:
        """Update a job's match score and reasoning in the database."""
        job.match_score = result.score
        job.match_reasoning = result.reasoning
        job.scored_at = datetime.now()
        self.session.commit()
    
    def score_jobs(self, 
                   rescore: bool = False, 
                   limit: Optional[int] = None,
                   job_ids: Optional[List[str]] = None) -> dict:
        """
        Score jobs using AI analysis.
        
        Args:
            rescore: If True, re-score all jobs. If False, only score unscored jobs.
            limit: Maximum number of jobs to process
            job_ids: Specific job IDs to score (overrides other filters)
            
        Returns:
            Dictionary with scoring statistics
        """
        
        # Load user profile
        user_profile = self.profile_manager.load_profile()
        if not user_profile:
            console.print("❌ No user profile found. Please create one first.", style="red")
            return {"error": "No user profile found"}
        
        console.print(f"👤 Using profile for: {user_profile.current_title}", style="blue")
        
        # Get jobs to score
        if job_ids:
            jobs = self.session.query(Job).filter(Job.job_id.in_(job_ids)).all()
            console.print(f"🎯 Scoring {len(jobs)} specific jobs", style="blue")
        elif rescore:
            jobs = self.get_jobs_for_rescoring(limit)
            console.print(f"🔄 Re-scoring {len(jobs)} jobs", style="blue")
        else:
            jobs = self.get_unscored_jobs(limit)
            console.print(f"🆕 Scoring {len(jobs)} unscored jobs", style="blue")
        
        if not jobs:
            console.print("✅ No jobs to score!", style="green")
            return {"total_jobs": 0, "processed": 0, "errors": 0}
        
        # Process jobs in batches
        processed = 0
        errors = 0
        score_distribution = {i: 0 for i in range(11)}  # 0-10 score counts
        
        with Progress() as progress:
            task = progress.add_task("Scoring jobs...", total=len(jobs))
            
            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i:i + self.batch_size]
                
                for job in batch:
                    try:
                        # Convert job to dictionary for analysis
                        job_data = {
                            "job_id": job.job_id,
                            "title": job.title,
                            "company": job.company,
                            "job_info": job.job_info,
                            "job_tags": job.job_tags or [],
                            "job_description": job.job_description,
                            "linkedin_url": job.linkedin_url,
                            "apply_url": job.apply_url
                        }
                        
                        # Analyze the job
                        result = self.job_matcher.analyze_job_match(job_data, user_profile)
                        
                        # Update the database
                        self.update_job_score(job, result)
                        
                        # Track statistics
                        processed += 1
                        score_distribution[result.score] += 1
                        
                        progress.update(task, advance=1)
                        
                    except Exception as e:
                        console.print(f"❌ Error processing job {job.job_id}: {e}", style="red")
                        errors += 1
                        progress.update(task, advance=1)
        
        # Display results
        self.display_scoring_results(processed, errors, score_distribution)
        
        return {
            "total_jobs": len(jobs),
            "processed": processed,
            "errors": errors,
            "score_distribution": score_distribution
        }
    
    def display_scoring_results(self, processed: int, errors: int, score_distribution: dict):
        """Display scoring results in a nice table."""
        console.print(f"\n✅ Scoring completed! Processed: {processed}, Errors: {errors}", style="green bold")
        
        # Create score distribution table
        table = Table(title="Score Distribution")
        table.add_column("Score", style="cyan", no_wrap=True)
        table.add_column("Count", style="magenta")
        table.add_column("Percentage", style="green")
        
        total_scored = sum(score_distribution.values())
        for score in range(10, -1, -1):  # Display 10 to 0
            count = score_distribution[score]
            percentage = (count / total_scored * 100) if total_scored > 0 else 0
            table.add_row(
                str(score),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(table)
    
    def get_scoring_stats(self) -> dict:
        """Get overall scoring statistics."""
        total_jobs = self.session.query(Job).count()
        scored_jobs = self.session.query(Job).filter(Job.match_score.isnot(None)).count()
        unscored_jobs = total_jobs - scored_jobs
        
        # Get score distribution
        scored_jobs_list = self.session.query(Job.match_score).filter(Job.match_score.isnot(None)).all()
        score_distribution = {i: 0 for i in range(11)}
        for job in scored_jobs_list:
            if job.match_score is not None:
                score_distribution[job.match_score] += 1
        
        return {
            "total_jobs": total_jobs,
            "scored_jobs": scored_jobs,
            "unscored_jobs": unscored_jobs,
            "score_distribution": score_distribution
        }
    
    def display_stats(self):
        """Display current scoring statistics."""
        stats = self.get_scoring_stats()
        
        console.print(f"\n📊 Scoring Statistics", style="blue bold")
        console.print(f"Total Jobs: {stats['total_jobs']}")
        console.print(f"Scored Jobs: {stats['scored_jobs']}")
        console.print(f"Unscored Jobs: {stats['unscored_jobs']}")
        
        if stats['scored_jobs'] > 0:
            # Create distribution table
            table = Table(title="Current Score Distribution")
            table.add_column("Score", style="cyan")
            table.add_column("Count", style="magenta")
            table.add_column("Percentage", style="green")
            
            for score in range(10, -1, -1):
                count = stats['score_distribution'][score]
                percentage = (count / stats['scored_jobs'] * 100) if stats['scored_jobs'] > 0 else 0
                table.add_row(
                    str(score),
                    str(count),
                    f"{percentage:.1f}%"
                )
            
            console.print(table)
    
    def close(self):
        """Close database session."""
        self.session.close()


# Utility functions for CLI usage
def score_all_unscored_jobs(batch_size: int = 10, limit: Optional[int] = None):
    """Score all unscored jobs."""
    workflow = ScoringWorkflow(batch_size=batch_size)
    try:
        return workflow.score_jobs(rescore=False, limit=limit)
    finally:
        workflow.close()


def rescore_all_jobs(batch_size: int = 10, limit: Optional[int] = None):
    """Re-score all jobs (including previously scored ones)."""
    workflow = ScoringWorkflow(batch_size=batch_size)
    try:
        return workflow.score_jobs(rescore=True, limit=limit)
    finally:
        workflow.close()


def score_specific_jobs(job_ids: List[str], batch_size: int = 10):
    """Score specific jobs by ID."""
    workflow = ScoringWorkflow(batch_size=batch_size)
    try:
        return workflow.score_jobs(job_ids=job_ids)
    finally:
        workflow.close()


def show_scoring_stats():
    """Display current scoring statistics."""
    workflow = ScoringWorkflow()
    try:
        workflow.display_stats()
    finally:
        workflow.close()


if __name__ == "__main__":
    # Simple CLI interface
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python scoring_workflow.py <command> [options]")
        print("Commands:")
        print("  score-new [limit]    - Score unscored jobs")
        print("  rescore-all [limit]  - Re-score all jobs")
        print("  stats               - Show scoring statistics")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "score-new":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        score_all_unscored_jobs(limit=limit)
    elif command == "rescore-all":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        rescore_all_jobs(limit=limit)
    elif command == "stats":
        show_scoring_stats()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)