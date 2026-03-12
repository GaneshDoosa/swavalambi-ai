"""
scheme_agent.py — Scheme Agent for scheme matching.
"""

from agents.base_agent import BaseAgent


class SchemeAgent(BaseAgent):
    """AI Agent for scheme matching."""
    
    def _build_text_for_embedding(self, doc: dict) -> str:
        """Build comprehensive text for embedding generation"""
        state = doc.get('state', 'All India')
        ministry = doc.get('ministry', '')
        
        # Include name, description, categories, tags, state, and ministry
        text_parts = [
            doc['name'],
            doc['description'],
            ' '.join(doc.get('categories', [])),
            ' '.join(doc.get('tags', [])),
            state,
            ministry
        ]
        
        return ' '.join(filter(None, text_parts))
    
    def _build_query_text(self, user_profile: dict) -> str:
        """Build comprehensive query text with profession-related terms"""
        skill = user_profile.get('skill', '').lower()
        intent = user_profile.get('intent', '')
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
        
        # Add intent-specific terms
        intent_terms = {
            'job': 'employment skill training job placement',
            'upskill': 'training skill development education course',
            'loan': 'loan financial assistance credit subsidy business'
        }
        
        query_parts = [
            expanded_skill,
            intent_terms.get(intent, intent),
            'scheme',
            state
        ]
        
        return ' '.join(filter(None, query_parts))
    
    def calculate_eligibility_score(self, scheme: dict, user_profile: dict) -> float:
        """Calculate eligibility score with improved profession matching"""
        score = 0.0
        
        user_skill = user_profile.get("skill", "").lower()
        scheme_categories = [c.lower() for c in scheme.get("categories", [])]
        scheme_tags = [t.lower() for t in scheme.get("tags", [])]
        scheme_name = scheme.get("name", "").lower()
        scheme_desc = scheme.get("description", "").lower()
        
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
            if any(kw in scheme_name or kw in scheme_desc for kw in keywords[:4]):  # First 4 are most specific
                score += 0.5
            # Broader category match
            elif any(kw in ' '.join(scheme_categories + scheme_tags) for kw in keywords[:6]):  # First 6 keywords
                score += 0.3
            # Construction/building related (for carpenter, plumber, welder)
            elif user_skill in ['carpenter', 'plumber', 'welder'] and any(kw in ' '.join(scheme_categories + scheme_tags) for kw in ['construction', 'building', 'worker']):
                score += 0.2
            # Generic artisan/craftsman schemes (fallback with lower score)
            elif any(kw in ' '.join(scheme_categories + scheme_tags) for kw in ['artisan', 'craftsman', 'vishwakarma', 'skill']):
                score += 0.1
        
        # Intent matching
        user_intent = user_profile.get("intent", "").lower()
        intent_keywords = {
            "job": ["employment", "job", "placement"],
            "upskill": ["training", "skill", "course", "education", "development"],
            "loan": ["loan", "credit", "financial", "subsidy", "assistance"]
        }
        
        if user_intent in intent_keywords:
            if any(kw in scheme_desc or kw in ' '.join(scheme_tags) for kw in intent_keywords[user_intent]):
                score += 0.3
        
        # Skill level bonus
        user_level = user_profile.get("skill_level", 0)
        if user_level >= 3:
            score += 0.1
        elif user_level >= 1:
            score += 0.05
        
        # State matching
        user_state = user_profile.get("state", "").lower()
        scheme_state = scheme.get("state", "").lower()
        if not scheme_state or scheme_state == "all india" or scheme_state == "all" or user_state in scheme_state:
            score += 0.1
        
        return min(score, 1.0)
    
    def search_schemes(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None) -> list[dict]:
        results = self.search(user_profile, limit, query_embedding=query_embedding)
        # Add full URL for each scheme
        for scheme in results:
            slug = scheme.get('url', '')
            if slug:
                scheme['url'] = f"https://www.myscheme.gov.in/schemes/{slug}"
        return results
