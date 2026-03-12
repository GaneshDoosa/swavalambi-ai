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
        """Calculate eligibility score with improved profession matching"""
        score = 0.0
        
        user_skill = user_profile.get("skill", "").lower()
        job_skills = [s.lower() for s in job.get("skills", [])]
        job_title = job.get("title", "").lower()
        job_description = job.get("description", "").lower()
        
        # Profession-specific scoring with more targeted matching
        profession_keywords = {
            'carpenter': ['carpenter', 'carpentry', 'woodwork', 'wood', 'furniture', 'joinery', 'cabinet', 'timber', 'construction', 'building'],
            'plumber': ['plumber', 'plumbing', 'pipe', 'sanitary', 'drainage', 'water supply', 'fitting', 'pipeline', 'construction', 'building'],
            'welder': ['welder', 'welding', 'metal', 'fabrication', 'steel', 'iron', 'construction', 'building', 'manufacturing'],
            'beautician': ['beautician', 'beauty', 'salon', 'cosmetic', 'makeup', 'hair', 'spa', 'skincare', 'grooming', 'wellness'],
            'tailor': ['tailor', 'tailoring', 'sewing', 'stitching', 'garment', 'textile', 'fashion', 'apparel', 'clothing', 'fabric']
        }
        
        # Check for profession match in various fields
        if user_skill in profession_keywords:
            keywords = profession_keywords[user_skill]
            
            # Direct profession match (highest score)
            if any(kw in job_title or kw in job_description for kw in keywords[:4]):  # First 4 are most specific
                score += 0.5
            # Broader category match in skills or description
            elif any(kw in ' '.join(job_skills) or kw in job_description for kw in keywords[:6]):  # First 6 keywords
                score += 0.3
            # Construction/building related (for carpenter, plumber, welder)
            elif user_skill in ['carpenter', 'plumber', 'welder'] and any(kw in job_title or kw in job_description or kw in ' '.join(job_skills) for kw in ['construction', 'building', 'worker']):
                score += 0.2
            # Generic skill match (fallback with lower score)
            elif user_skill in job_title or any(user_skill in s for s in job_skills):
                score += 0.1
        else:
            # Fallback for unmapped professions
            if user_skill in job_title or any(user_skill in s for s in job_skills):
                score += 0.4
        
        user_level = user_profile.get("skill_level", 0)
        if user_level >= 3:
            score += 0.2
        elif user_level >= 1:
            score += 0.1
        
        # Check both state and preferred_location fields
        user_location = user_profile.get("preferred_location", user_profile.get("state", "")).lower()
        job_location = job.get("location", "").lower()
        
        # Boost location matches significantly
        if user_location and user_location != "all india":
            if user_location in job_location or job_location in user_location:
                score += 0.4  # Strong boost for location match
        
        return min(score, 1.0)
    
    def search_jobs(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None, filters: dict = None) -> list[dict]:
        # Fetch more results initially to account for deduplication
        # If we want 'limit' unique results, fetch 3-4x that amount
        fetch_limit = limit * 4
        results = self.search(user_profile, fetch_limit, query_embedding=query_embedding, filters=filters)
        
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
        
        # Return only the requested limit after deduplication
        return unique_jobs[:limit]
