"""
base_agent.py — Base Agent for vector search with pluggable providers.
"""

import logging
from typing import Optional
from common.providers.embedding_provider import EmbeddingProvider
from common.stores.vector_store import VectorStore

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base AI Agent for vector search with pluggable embedding and vector store."""
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        index_name: str
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.index_name = index_name
        
        logger.info(f"BaseAgent initialized with {embedding_provider.get_provider_name()} and {vector_store.get_store_name()}")
    
    def create_index(self):
        """Create vector index."""
        dimension = self.embedding_provider.get_dimension()
        self.vector_store.create_index(self.index_name, dimension)
    
    def index_document(self, doc: dict):
        """Index a single document."""
        text = self._build_text_for_embedding(doc)
        embedding = self.embedding_provider.generate_embedding(text)
        
        metadata = {k: v for k, v in doc.items() if k != 'embedding'}
        self.vector_store.index_document(
            self.index_name,
            doc.get('id', doc.get('scheme_id', doc.get('job_id'))),
            embedding,
            metadata
        )
    
    def _build_text_for_embedding(self, doc: dict) -> str:
        """Build text for embedding - override in subclass."""
        raise NotImplementedError
    
    def calculate_eligibility_score(self, doc: dict, user_profile: dict) -> float:
        """Calculate eligibility score - override in subclass."""
        raise NotImplementedError
    
    def search(self, user_profile: dict, limit: int = 10, query_embedding: list[float] = None, filters: dict = None) -> list[dict]:
        """Search using vector similarity - profession filtering done at SQL level."""
        import time
        
        if query_embedding is None:
            logger.info(f"[{self.index_name}] Generating embedding for this request")
            query_text = self._build_query_text(user_profile)
            query_embedding = self.embedding_provider.generate_embedding(query_text)
        else:
            logger.debug(f"[{self.index_name}] Reusing embedding from orchestrator")
        
        # Add profession filter from user profile if available
        if filters is None:
            filters = {}
        
        if user_profile.get('skill'):
            # Map skill to profession category
            skill_lower = user_profile['skill'].lower()
            profession_mapping = {
                'plumber': 'plumber',
                'welder': 'welder',
                'beautician': 'beautician',
                'tailor': 'tailor',
                'electrician': 'electrician',
                'carpenter': 'carpenter'
            }
            
            for key, value in profession_mapping.items():
                if key in skill_lower:
                    filters['profession'] = value
                    logger.info(f"[{self.index_name}] Adding profession filter: {value}")
                    break
        
        # Vector search with profession filter
        vector_start = time.time()
        results = self.vector_store.search(self.index_name, query_embedding, limit=limit * 2, filters=filters)  # Fetch 2x for location sorting
        vector_time = time.time() - vector_start
        
        # Apply location-based sorting
        from common.utils.location_helper import parse_location
        
        preferred_location = user_profile.get('preferred_location', user_profile.get('state', '')).strip()
        user_city, user_state = parse_location(preferred_location) if preferred_location else ('', '')
        
        if user_city or user_state:
            logger.info(f"[{self.index_name}] Location filter - city: '{user_city}', state: '{user_state}'")
            
            # Split into location matches and non-matches
            location_matches = []
            other_results = []
            
            for result in results:
                is_match = False
                
                if self.index_name == 'schemes':
                    # Schemes: match against state
                    result_state = result.get('state', '').lower()
                    
                    if user_state and (user_state in result_state or result_state in user_state or result_state == 'all' or 'all india' in result_state):
                        is_match = True
                        
                elif self.index_name == 'upskill':
                    # Upskill: location is "CITY, STATE" - check both
                    result_location = result.get('location', '').lower()
                    
                    if ',' in result_location:
                        location_parts = [part.strip() for part in result_location.split(',')]
                        # Match if user city/state is in any part
                        if (user_city and any(user_city in part or part in user_city for part in location_parts)) or \
                           (user_state and any(user_state in part or part in user_state for part in location_parts)):
                            is_match = True
                    else:
                        if (user_city and (user_city in result_location or result_location in user_city)) or \
                           (user_state and (user_state in result_location or result_location in user_state)):
                            is_match = True
                            
                else:
                    # Jobs: match against city
                    result_location = result.get('location', '').lower()
                    if user_city and (user_city in result_location or result_location in user_city or result_location == 'all india'):
                        is_match = True
                
                if is_match:
                    location_matches.append(result)
                else:
                    other_results.append(result)
            
            # Sort location matches by vector score
            location_matches.sort(key=lambda x: x.get('vector_score', 0), reverse=True)
            other_results.sort(key=lambda x: x.get('vector_score', 0), reverse=True)
            
            # Combine: ALL location matches first, then others
            results = location_matches + other_results
            
            logger.info(f"[{self.index_name}] Location sorting: {len(location_matches)} local matches (shown first), {len(other_results)} others")
        else:
            # No location preference, just sort by vector score
            results.sort(key=lambda x: x.get('vector_score', 0), reverse=True)
        
        logger.info(f"[{self.index_name}] Search timing: vector={vector_time:.3f}s, returned {len(results[:limit])} results")
        
        return results[:limit]
    
    def _build_query_text(self, user_profile: dict) -> str:
        """Build query text - override in subclass."""
        raise NotImplementedError
