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
        """Calculate eligibility score — profession filtering is done at SQL level via ai_classified_scheme"""
        score = 0.4  # Base score for all results (already filtered by profession in SQL)
        
        # Intent matching bonus
        user_intent = user_profile.get("intent", "").lower()
        scheme_desc = scheme.get("description", "").lower()
        scheme_tags = [t.lower() for t in scheme.get("tags", [])]
        
        intent_keywords = {
            "job": ["employment", "job", "placement"],
            "upskill": ["training", "skill", "course", "education", "development"],
            "loan": ["loan", "credit", "financial", "subsidy", "assistance"]
        }
        
        if user_intent in intent_keywords:
            if any(kw in scheme_desc or kw in ' '.join(scheme_tags) for kw in intent_keywords[user_intent]):
                score += 0.3
        
        # Skill level bonus
        if user_profile.get("skill_level", 0) >= 3:
            score += 0.2
        elif user_profile.get("skill_level", 0) >= 1:
            score += 0.1
        
        # State preference bonus
        user_state = user_profile.get("state", "").lower()
        scheme_state = scheme.get("state", "").lower()
        if not scheme_state or scheme_state == "all india" or scheme_state == "all" or user_state in scheme_state:
            score += 0.1
        
        return min(score, 1.0)
    
    def search_schemes(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None, filters: dict = None) -> list[dict]:
        # Fetch results - profession already filtered at SQL level, location-sorted by base_agent
        results = self.search(user_profile, limit, query_embedding=query_embedding, filters=filters)
        
        # Add full URL for each scheme
        for scheme in results:
            slug = scheme.get('url', '')
            if slug:
                scheme['url'] = f"https://www.myscheme.gov.in/schemes/{slug}"
        
        return results[:limit]
