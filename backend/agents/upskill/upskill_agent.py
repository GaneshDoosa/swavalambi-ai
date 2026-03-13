"""
upskill_agent.py — Upskill Agent for training/course matching.
"""

from agents.base_agent import BaseAgent


class UpskillAgent(BaseAgent):
    """AI Agent for training/course matching."""
    
    def _build_text_for_embedding(self, doc: dict) -> str:
        location = doc.get('location', '')
        return f"{doc['name']} {doc['description']} {' '.join(doc.get('skills', []))} {doc.get('provider', '')} {location}"
    
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
            'training course education skill development',
            state
        ]
        
        return ' '.join(filter(None, query_parts))
    
    def calculate_eligibility_score(self, course: dict, user_profile: dict) -> float:
        """Calculate eligibility score — profession filtering is done at SQL level via ai_classified_training"""
        score = 0.5  # Base score for all results (already filtered by profession in SQL)
        
        # Boost if skill keywords match
        user_skill = user_profile.get("skill", "").lower()
        course_name = course.get("name", "").lower()
        course_skills = [s.lower() for s in course.get("skills", [])]
        
        if user_skill in course_name or any(user_skill in s for s in course_skills):
            score += 0.2
        
        # Skill level bonus (favor training for lower skill levels)
        if user_profile.get("skill_level", 0) < 3:
            score += 0.2
        else:
            score += 0.1
        
        # Location bonus
        user_location = user_profile.get("preferred_location", user_profile.get("state", "")).lower()
        course_location = course.get("location", "").lower()
        
        if not course_location or "online" in course_location:
            score += 0.1  # Bonus for online accessibility
        elif user_location and user_location != "all india" and (user_location in course_location or course_location in user_location):
            score += 0.1  # Bonus for location match
        
        return min(score, 1.0)
    
    def search_courses(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None, filters: dict = None) -> list[dict]:
        # Fetch results - profession already filtered at SQL level, location-sorted by base_agent
        results = self.search(user_profile, limit, query_embedding=query_embedding, filters=filters)
        
        # Format results for UI compatibility
        for center in results:
            # Map skills to courses (UI expects 'courses' field)
            center['courses'] = center.get('skills', [])
            
            # Map provider to center_type (UI expects 'center_type' field)
            center['center_type'] = center.get('provider', 'Training Center')
            
            # Add URL (UI expects 'url' field)
            # Generate URL from contact/email if available
            contact = center.get('contact', '')
            email = center.get('email', '')
            if email:
                center['url'] = f"mailto:{email}"
            elif contact:
                center['url'] = f"tel:{contact.replace(' ', '')}"
            else:
                center['url'] = ""
            
            # Keep contact info for display
            if contact:
                center['contact_url'] = f"tel:{contact.replace(' ', '')}"
            if email:
                center['email_url'] = f"mailto:{email}"
        
        return results[:limit]
