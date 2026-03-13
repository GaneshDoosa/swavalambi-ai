"""
jobs_agent.py — Jobs Agent for job matching.
"""

from agents.base_agent import BaseAgent


class JobsAgent(BaseAgent):
    """AI Agent for job matching."""
    
    def _build_text_for_embedding(self, doc: dict) -> str:
        location = doc.get('location', '')
        return f"{doc['title']} {doc['description']} {doc.get('company', '')} {' '.join(doc.get('skills', []))} {location}"
    
    def _build_query_text(self, user_profile: dict) -> str:
        """Build comprehensive query text with profession-related terms"""
        skill = user_profile.get('skill', '').lower()
        state = user_profile.get('state', '')
        
        # Map professions to more specific terms
        profession_mapping = {
            'carpenter': 'carpenter carpentry woodwork wood furniture construction building',
            'plumber': 'plumber plumbing pipe sanitary water construction building worker',
            'welder': 'welder welding metal fabrication steel construction building manufacturing',
            'beautician': 'beautician beauty salon cosmetic makeup hair spa skincare wellness',
            'tailor': 'tailor tailoring sewing stitching garment textile fashion apparel clothing'
        }
        
        # Get expanded terms for the profession
        expanded_skill = profession_mapping.get(skill, skill)
        
        query_parts = [
            expanded_skill,
            'job employment',
            state
        ]
        
        return ' '.join(filter(None, query_parts))
    
    def calculate_eligibility_score(self, job: dict, user_profile: dict) -> float:
        """Calculate eligibility score — profession filtering is done at SQL level via ai_classified_job"""
        score = 0.5  # Base score for all results (already filtered by profession in SQL)
        
        # Boost if keywords also match in text
        user_skill = user_profile.get("skill", "").lower()
        job_title = job.get("title", "").lower()
        job_skills = [s.lower() for s in job.get("skills", [])]
        
        if user_skill in job_title or any(user_skill in s for s in job_skills):
            score += 0.2
        
        # Skill level bonus
        if user_profile.get("skill_level", 0) >= 3:
            score += 0.2
        elif user_profile.get("skill_level", 0) >= 1:
            score += 0.1
        
        # Location bonus
        user_location = user_profile.get("preferred_location", user_profile.get("state", "")).lower()
        job_location = job.get("location", "").lower()
        if user_location and user_location != "all india" and (user_location in job_location or job_location in user_location):
            score += 0.1
        
        return min(score, 1.0)
    
    def search_jobs(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None, filters: dict = None) -> list[dict]:
        # Fetch results - profession already filtered at SQL level
        results = self.search(user_profile, limit * 3, query_embedding=query_embedding, filters=filters)
        
        # Format results for UI compatibility
        for job in results:
            # Format salary from min_salary and max_salary
            min_sal = job.get('min_salary', 0)
            max_sal = job.get('max_salary', 0)
            
            if min_sal and max_sal:
                job['salary'] = f"₹{int(min_sal):,} - ₹{int(max_sal):,}"
            elif min_sal:
                job['salary'] = f"₹{int(min_sal):,}+"
            elif max_sal:
                job['salary'] = f"Up to ₹{int(max_sal):,}"
            else:
                job['salary'] = "Salary not specified"
            
            # Add job application URL
            job_id = job.get('id', '')
            if job_id:
                job['apply_url'] = f"https://betacloud.ncs.gov.in/job-listing/applying/{job_id}"
            else:
                job['apply_url'] = ""
        
        # Deduplicate by (company, title, location)
        seen = set()
        unique_jobs = []
        
        for job in results:
            key = (job.get('company', ''), job.get('title', ''), job.get('location', ''))
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        # Return top results (already sorted by base_agent with location priority)
        return unique_jobs[:limit]
