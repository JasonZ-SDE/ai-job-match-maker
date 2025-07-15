import json
import os
from typing import Optional
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv
from user_profile.profile_manager import UserProfile, get_profile_summary

load_dotenv(override=True)


@dataclass
class JobMatchResult:
    """Result of job matching analysis."""
    score: int  # 0-10
    reasoning: str
    
    def __post_init__(self):
        # Ensure score is within valid range
        self.score = max(0, min(10, self.score))


class JobMatcher:
    """AI-powered job matching engine using OpenAI GPT."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
    def analyze_job_match(self, job_data: dict, user_profile: UserProfile) -> JobMatchResult:
        """
        Analyze how well a job matches the user's profile and goals.
        
        Args:
            job_data: Dictionary containing job information
            user_profile: User's professional profile and goals
            
        Returns:
            JobMatchResult with score (0-10) and reasoning
        """
        
        # Prepare job information
        job_info = f"""
Job Title: {job_data.get('title', 'N/A')}
Company: {job_data.get('company', 'N/A')}
Location/Type: {job_data.get('job_info', 'N/A')}
Job Tags: {', '.join(job_data.get('job_tags', [])) if job_data.get('job_tags') else 'None'}
Job Description: {job_data.get('job_description', 'N/A')[:2000]}...  # Truncate for token limits
""".strip()
        
        # Get user profile summary
        profile_summary = get_profile_summary(user_profile)
        
        # Create the analysis prompt
        prompt = f"""
You are an expert career counselor and job matching specialist. Analyze how well this job matches the candidate's profile and career goals.

CANDIDATE PROFILE:
{profile_summary}

JOB POSTING:
{job_info}

ANALYSIS INSTRUCTIONS:
1. CRITICAL LOCATION REQUIREMENT: The candidate strongly prefers REMOTE work only. If the job posting does not explicitly mention "Remote", "Work from home", "WFH", or similar remote work options, this is a MAJOR disqualifying factor.

2. Evaluate the job match across these dimensions:
   - Location/Work Style: MOST IMPORTANT - Does it explicitly offer remote work? If not remote, this is a critical mismatch.
   - Role Alignment: How well does the job title/responsibilities match target roles?
   - Skills Match: How many required/preferred skills does the candidate have?
   - Experience Level: Is the job appropriate for the candidate's experience level?
   - Career Growth: Does it provide advancement opportunities?
   - Compensation Alignment: Does it likely meet salary expectations?

3. SCORING RULES:
   - If job is NOT explicitly remote: Score 0-2 (Poor match) regardless of other factors
   - If job IS explicitly remote: Score based on other factors (3-10 possible)
   - 0-2: Poor match (major misalignments, especially non-remote)
   - 3-4: Below average match (some significant gaps)
   - 5-6: Average match (mixed alignment)
   - 7-8: Good match (mostly aligned)
   - 9-10: Excellent match (highly aligned)

4. Provide concise reasoning (MAX 250 words) explaining:
   - FIRST: Address remote work requirement and impact on score
   - Key strengths of the match
   - Potential concerns or gaps
   - Overall recommendation

Respond in this exact JSON format:
{{
    "score": <integer 0-10>,
    "reasoning": "<concise analysis explaining the score - maximum 250 words>"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model for job analysis
                messages=[
                    {"role": "system", "content": "You are an expert career counselor specializing in job matching analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=1000
            )
            
            # Parse the response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from the response
            if content.startswith("```json"):
                content = content[7:-3]  # Remove ```json and ```
            elif content.startswith("```"):
                content = content[3:-3]  # Remove ``` markers
                
            result_data = json.loads(content)
            
            return JobMatchResult(
                score=int(result_data["score"]),
                reasoning=result_data["reasoning"]
            )
            
        except Exception as e:
            print(f"❌ Error analyzing job match: {e}")
            # Return default result on error
            return JobMatchResult(
                score=0,
                reasoning=f"Error occurred during analysis: {str(e)}"
            )
    
    def batch_analyze_jobs(self, jobs_data: list, user_profile: UserProfile) -> list[JobMatchResult]:
        """
        Analyze multiple jobs in batch.
        
        Args:
            jobs_data: List of job dictionaries
            user_profile: User's professional profile
            
        Returns:
            List of JobMatchResult objects
        """
        results = []
        total_jobs = len(jobs_data)
        
        for i, job in enumerate(jobs_data, 1):
            print(f"🤖 Analyzing job {i}/{total_jobs}: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
            
            result = self.analyze_job_match(job, user_profile)
            results.append(result)
            
            print(f"   ✅ Score: {result.score}/10")
            
            # Rate limiting: small delay between requests
            if i < total_jobs:
                import time
                time.sleep(0.5)  # 500ms delay
        
        return results


# Utility function for testing
def test_job_matcher():
    """Test the job matcher with sample data."""
    from user_profile.profile_manager import ProfileManager
    
    # Load or create sample profile
    pm = ProfileManager()
    profile = pm.load_profile()
    if not profile:
        profile = pm.create_sample_profile()
        pm.save_profile(profile)
    
    # Sample job data
    sample_job = {
        "job_id": "test123",
        "title": "Senior Software Engineer",
        "company": "Tech Startup Inc.",
        "job_info": "Remote • Full-time • San Francisco, CA",
        "job_tags": ["Python", "React", "AWS", "Machine Learning"],
        "job_description": "We are seeking a Senior Software Engineer to join our growing team. You will work on cutting-edge AI applications using Python, React, and AWS. Requirements include 4+ years of experience, strong Python skills, and experience with machine learning frameworks.",
        "linkedin_url": "https://linkedin.com/jobs/test123",
        "apply_url": "https://company.com/careers/test123"
    }
    
    # Test the matcher
    matcher = JobMatcher()
    result = matcher.analyze_job_match(sample_job, profile)
    
    print(f"🎯 Match Score: {result.score}/10")
    print(f"📝 Reasoning: {result.reasoning}")
    
    return result


if __name__ == "__main__":
    test_job_matcher()