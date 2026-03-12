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
        """Calculate eligibility score with improved profession matching"""
        score = 0.0
        
        user_skill = user_profile.get("skill", "").lower()
        course_skills = [s.lower() for s in course.get("skills", [])]
        course_name = course.get("name", "").lower()
        course_description = course.get("description", "").lower()
        
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
            if any(kw in course_name or kw in course_description for kw in keywords[:4]):  # First 4 are most specific
                score += 0.6
            # Broader category match in skills or description
            elif any(kw in ' '.join(course_skills) or kw in course_description for kw in keywords[:6]):  # First 6 keywords
                score += 0.4
            # Construction/building related (for carpenter, plumber, welder)
            elif user_skill in ['carpenter', 'plumber', 'welder'] and any(kw in course_name or kw in course_description or kw in ' '.join(course_skills) for kw in ['construction', 'building', 'worker']):
                score += 0.3
            # Generic skill match (fallback with lower score)
            elif user_skill in course_name or any(user_skill in s for s in course_skills):
                score += 0.2
        else:
            # Fallback for unmapped professions
            if user_skill in course_name or any(user_skill in s for s in course_skills):
                score += 0.5
        
        user_level = user_profile.get("skill_level", 0)
        if user_level < 3:
            score += 0.3
        else:
            score += 0.1
        
        # Check both state and preferred_location fields
        user_location = user_profile.get("preferred_location", user_profile.get("state", "")).lower()
        course_location = course.get("location", "").lower()
        
        # Location matching with online course consideration
        if not course_location or "online" in course_location:
            score += 0.2  # Online courses are always accessible
        elif user_location and user_location != "all india":
            if user_location in course_location or course_location in user_location:
                score += 0.2  # Location match bonus
        
        return min(score, 1.0)
    
    def search_courses(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None) -> list[dict]:
        results = self.search(user_profile, limit, query_embedding=query_embedding)
        
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
        
        return results
