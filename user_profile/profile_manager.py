from pathlib import Path
from typing import List, Optional
import json
from pydantic import BaseModel, Field
from datetime import datetime


class UserProfile(BaseModel):
    """User profile containing professional background and job search goals."""
    
    # Professional Background
    current_title: str = Field(description="Current job title")
    years_experience: int = Field(description="Total years of professional experience")
    professional_experience: str = Field(description="Detailed description of previous work experiences, projects, and achievements")
    languages: List[str] = Field(description="Programming languages (e.g., Python, JavaScript, Java)")
    technologies: List[str] = Field(description="Frameworks and technologies (e.g., React, Django, TensorFlow)")
    infrastructure: List[str] = Field(description="Infrastructure and tools (e.g., AWS, Docker, Kubernetes)")
    education: str = Field(description="Educational background")
    
    # Career Goals
    target_roles: List[str] = Field(description="Desired job titles/roles")
    match_goal: str = Field(description="Specific goal or intention for job matching (e.g., 'Find a senior role at a fast-growing tech company with ML opportunities')")
    location_preferences: List[str] = Field(description="Preferred work locations/remote preferences")
    salary_range: Optional[str] = Field(default=None, description="Desired salary range")
    work_preferences: List[str] = Field(default_factory=list, description="Work style preferences (remote, hybrid, on-site)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def model_dump_json_pretty(self) -> str:
        """Return pretty-printed JSON string."""
        return json.dumps(self.model_dump(), indent=2, default=str)


class ProfileManager:
    """Manages user profile storage and retrieval."""
    
    def __init__(self, profile_path: Optional[Path] = None):
        self.profile_path = profile_path or Path.cwd() / "user_profile.json"
    
    def save_profile(self, profile: UserProfile) -> None:
        """Save user profile to JSON file."""
        profile.updated_at = datetime.now()
        with open(self.profile_path, 'w') as f:
            f.write(profile.model_dump_json_pretty())
        print(f"✅ Profile saved to {self.profile_path}")
    
    def load_profile(self) -> Optional[UserProfile]:
        """Load user profile from JSON file."""
        if not self.profile_path.exists():
            return None
        
        try:
            with open(self.profile_path, 'r') as f:
                data = json.load(f)
            return UserProfile(**data)
        except Exception as e:
            print(f"❌ Error loading profile: {e}")
            return None
    
    def profile_exists(self) -> bool:
        """Check if profile file exists."""
        return self.profile_path.exists()
    
    def delete_profile(self) -> None:
        """Delete the profile file."""
        if self.profile_path.exists():
            self.profile_path.unlink()
            print(f"✅ Profile deleted from {self.profile_path}")
    
    def load_from_background_json(self, json_path: Optional[Path] = None) -> Optional[UserProfile]:
        """Load user profile from background JSON file."""
        if json_path is None:
            json_path = Path(__file__).parent / "user_background.json"
        
        if not json_path.exists():
            print(f"❌ Background JSON file not found: {json_path}")
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return UserProfile(**data)
        except Exception as e:
            print(f"❌ Error loading background JSON: {e}")
            return None
    
    def create_sample_profile(self) -> UserProfile:
        """Create a sample profile for testing."""
        return UserProfile(
            current_title="Senior Software Engineer",
            years_experience=5,
            professional_experience="""
• Software Engineer at TechCorp (2019-2023): Built scalable microservices using Python and Django, managed AWS infrastructure, led team of 3 developers
• Full-Stack Developer at StartupXYZ (2017-2019): Developed React frontend and Node.js backend for e-commerce platform, implemented CI/CD pipelines
• Junior Developer at DevCo (2016-2017): Created REST APIs, worked with PostgreSQL databases, participated in agile development process
• Key Projects: Built ML recommendation system serving 100K+ users, architected event-driven system processing 1M+ events/day
            """.strip(),
            languages=[
                "Python", "JavaScript", "TypeScript", "SQL", "Go"
            ],
            technologies=[
                "React", "Node.js", "Django", "FastAPI", "PostgreSQL", 
                "Redis", "REST APIs", "GraphQL", "Machine Learning", "TensorFlow"
            ],
            infrastructure=[
                "AWS", "Docker", "Kubernetes", "Git", "CI/CD", 
                "Terraform", "Linux", "Nginx", "Monitoring"
            ],
            education="Bachelor's in Computer Science",
            target_roles=[
                "Senior Software Engineer", "Staff Software Engineer", 
                "Technical Lead", "Engineering Manager"
            ],
            match_goal="Find a senior engineering role at a fast-growing tech company with opportunities to lead technical initiatives and work with cutting-edge technologies",
            location_preferences=["Remote", "San Francisco", "Seattle", "New York"],
            salary_range="$150,000 - $220,000",
            work_preferences=["Remote", "Hybrid"]
        )


def get_profile_summary(profile: UserProfile) -> str:
    """Generate a concise text summary of the user profile for AI prompts."""
    summary = f"""
Professional Background:
- Current Role: {profile.current_title} with {profile.years_experience} years experience
- Education: {profile.education}
- Programming Languages: {', '.join(profile.languages)}
- Technologies: {', '.join(profile.technologies[:8])}{'...' if len(profile.technologies) > 8 else ''}
- Infrastructure: {', '.join(profile.infrastructure[:8])}{'...' if len(profile.infrastructure) > 8 else ''}

Professional Experience:
{profile.professional_experience}

Career Goals:
- Match Goal: {profile.match_goal}
- Target Roles: {', '.join(profile.target_roles)}
- Location Preferences: {', '.join(profile.location_preferences)}
- Salary Range: {profile.salary_range or 'Not specified'}
- Work Style: {', '.join(profile.work_preferences) if profile.work_preferences else 'Flexible'}
""".strip()
    
    return summary