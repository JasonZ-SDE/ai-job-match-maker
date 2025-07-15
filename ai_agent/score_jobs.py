#!/usr/bin/env python3
"""
CLI interface for AI job scoring workflow.

This script provides command-line access to the job scoring system,
allowing users to score jobs, manage profiles, and view statistics.
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from user_profile.profile_manager import ProfileManager, UserProfile
from ai_agent.scoring_workflow import ScoringWorkflow, show_scoring_stats

console = Console()


def create_profile_interactive() -> UserProfile:
    """Interactive profile creation."""
    console.print("\n🧑‍💼 Creating your professional profile...", style="blue bold")
    
    current_title = Prompt.ask("Current job title")
    years_experience = int(Prompt.ask("Years of experience", default="3"))
    
    console.print("\nEnter your professional experience (detailed work history):")
    console.print("Include previous roles, key projects, achievements, technologies used, etc.")
    console.print("(Press Enter twice when finished)")
    
    # Collect multiline input
    lines = []
    while True:
        line = input("Professional experience: " if not lines else "                     ")
        if line == "" and lines:  # Empty line and we have content
            break
        lines.append(line)
    
    professional_experience = "\n".join(lines)
    
    console.print("\nEnter your programming languages (comma-separated):")
    languages_input = Prompt.ask("Languages (e.g., Python, JavaScript, Java)")
    languages = [lang.strip() for lang in languages_input.split(",")]
    
    console.print("\nEnter your technologies/frameworks (comma-separated):")
    technologies_input = Prompt.ask("Technologies (e.g., React, Django, PostgreSQL)")
    technologies = [tech.strip() for tech in technologies_input.split(",")]
    
    console.print("\nEnter your infrastructure/tools (comma-separated):")
    infrastructure_input = Prompt.ask("Infrastructure (e.g., AWS, Docker, Kubernetes)")
    infrastructure = [infra.strip() for infra in infrastructure_input.split(",")]
    
    education = Prompt.ask("Education background")
    
    console.print("\nEnter target roles (comma-separated):")
    roles_input = Prompt.ask("Target roles")
    target_roles = [role.strip() for role in roles_input.split(",")]
    
    console.print("\nEnter location preferences (comma-separated):")
    locations_input = Prompt.ask("Location preferences", default="Remote")
    location_preferences = [loc.strip() for loc in locations_input.split(",")]
    
    # Optional fields
    salary_range = Prompt.ask("Salary range (optional)", default="")
    
    # Work preferences
    console.print("\nEnter work preferences (comma-separated, optional):")
    work_prefs_input = Prompt.ask("Work preferences", default="Remote,Hybrid")
    work_preferences = [pref.strip() for pref in work_prefs_input.split(",") if pref.strip()]
    
    return UserProfile(
        current_title=current_title,
        years_experience=years_experience,
        professional_experience=professional_experience,
        languages=languages,
        technologies=technologies,
        infrastructure=infrastructure,
        education=education,
        target_roles=target_roles,
        location_preferences=location_preferences,
        salary_range=salary_range if salary_range else None,
        work_preferences=work_preferences
    )


def handle_profile_command(args):
    """Handle profile-related commands."""
    pm = ProfileManager()
    
    if args.profile_action == "create":
        if pm.profile_exists() and not Confirm.ask("Profile already exists. Overwrite?"):
            console.print("❌ Profile creation cancelled.", style="red")
            return
        
        if args.sample:
            profile = pm.create_sample_profile()
            console.print("✅ Created sample profile", style="green")
        elif args.from_json:
            profile = pm.load_from_background_json()
            if not profile:
                console.print("❌ Failed to load from background JSON", style="red")
                return
            console.print("✅ Created profile from background JSON", style="green")
        else:
            profile = create_profile_interactive()
        
        pm.save_profile(profile)
        console.print("✅ Profile saved successfully!", style="green")
        
    elif args.profile_action == "view":
        profile = pm.load_profile()
        if not profile:
            console.print("❌ No profile found. Create one first.", style="red")
            return
        
        # Display profile in a table
        table = Table(title="Your Professional Profile")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Current Title", profile.current_title)
        table.add_row("Experience", f"{profile.years_experience} years")
        table.add_row("Education", profile.education)
        table.add_row("Professional Experience", profile.professional_experience[:200] + "..." if len(profile.professional_experience) > 200 else profile.professional_experience)
        table.add_row("Languages", ", ".join(profile.languages))
        table.add_row("Technologies", ", ".join(profile.technologies[:8]) + ("..." if len(profile.technologies) > 8 else ""))
        table.add_row("Infrastructure", ", ".join(profile.infrastructure[:8]) + ("..." if len(profile.infrastructure) > 8 else ""))
        table.add_row("Target Roles", ", ".join(profile.target_roles))
        table.add_row("Locations", ", ".join(profile.location_preferences))
        if profile.salary_range:
            table.add_row("Salary Range", profile.salary_range)
        if profile.work_preferences:
            table.add_row("Work Style", ", ".join(profile.work_preferences))
        
        console.print(table)
        
    elif args.profile_action == "delete":
        if not pm.profile_exists():
            console.print("❌ No profile found.", style="red")
            return
        
        if Confirm.ask("Are you sure you want to delete your profile?"):
            pm.delete_profile()
            console.print("✅ Profile deleted.", style="green")
        else:
            console.print("❌ Profile deletion cancelled.", style="red")


def handle_score_command(args):
    """Handle scoring-related commands."""
    pm = ProfileManager()
    if not pm.profile_exists():
        console.print("❌ No profile found. Create one first with: score_jobs.py profile create", style="red")
        return
    
    workflow = ScoringWorkflow(batch_size=args.batch_size)
    
    try:
        if args.score_action == "new":
            console.print("🎯 Scoring unscored jobs...", style="blue")
            result = workflow.score_jobs(rescore=False, limit=args.limit)
            
        elif args.score_action == "all":
            console.print("🔄 Re-scoring all jobs...", style="blue")
            result = workflow.score_jobs(rescore=True, limit=args.limit)
            
        elif args.score_action == "ids":
            if not args.job_ids:
                console.print("❌ Job IDs required for this command", style="red")
                return
            job_ids = args.job_ids.split(",")
            console.print(f"🎯 Scoring specific jobs: {job_ids}", style="blue")
            result = workflow.score_jobs(job_ids=job_ids)
        
        if result.get("error"):
            console.print(f"❌ Error: {result['error']}", style="red")
        else:
            console.print(f"✅ Scoring completed! Processed: {result['processed']}, Errors: {result['errors']}", style="green")
            
    finally:
        workflow.close()


def handle_stats_command():
    """Handle statistics command."""
    show_scoring_stats()


def main():
    parser = argparse.ArgumentParser(
        description="AI Job Scoring CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Profile management
  score_jobs.py profile create              # Create profile interactively
  score_jobs.py profile create --sample     # Create sample profile
  score_jobs.py profile create --from-json  # Create profile from user_background.json
  score_jobs.py profile view               # View current profile
  score_jobs.py profile delete             # Delete profile
  
  # Job scoring
  score_jobs.py score new                  # Score unscored jobs
  score_jobs.py score new --limit 50       # Score up to 50 unscored jobs
  score_jobs.py score all                  # Re-score all jobs
  score_jobs.py score ids --job-ids "123,456,789"  # Score specific jobs
  
  # Statistics
  score_jobs.py stats                      # Show scoring statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Profile commands
    profile_parser = subparsers.add_parser("profile", help="Manage user profile")
    profile_parser.add_argument("profile_action", choices=["create", "view", "delete"], 
                               help="Profile action")
    profile_parser.add_argument("--sample", action="store_true", 
                               help="Create sample profile (for create action)")
    profile_parser.add_argument("--from-json", action="store_true", 
                               help="Create profile from user_background.json file")
    
    # Scoring commands
    score_parser = subparsers.add_parser("score", help="Score jobs using AI")
    score_parser.add_argument("score_action", choices=["new", "all", "ids"], 
                             help="Scoring action")
    score_parser.add_argument("--limit", type=int, 
                             help="Maximum number of jobs to process")
    score_parser.add_argument("--batch-size", type=int, default=10, 
                             help="Batch size for processing (default: 10)")
    score_parser.add_argument("--job-ids", type=str, 
                             help="Comma-separated job IDs (for 'ids' action)")
    
    # Stats command
    subparsers.add_parser("stats", help="Show scoring statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "profile":
            handle_profile_command(args)
        elif args.command == "score":
            handle_score_command(args)
        elif args.command == "stats":
            handle_stats_command()
    except KeyboardInterrupt:
        console.print("\n❌ Operation cancelled by user.", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()