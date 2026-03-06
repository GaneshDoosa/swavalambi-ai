"""
provider_factory.py — Singleton factory for embedding providers
"""

import os
from typing import Optional
from .embedding_providers import BedrockTitanEmbeddingProvider

# Global singleton instance
_embedding_provider_instance: Optional[BedrockTitanEmbeddingProvider] = None


def get_embedding_provider() -> BedrockTitanEmbeddingProvider:
    """
    Get or create the singleton embedding provider instance.
    
    This ensures only one provider instance exists across the entire application,
    which means:
    - Single cache shared across all agents
    - Cache file loaded only once
    - No duplicate initialization logs
    
    Returns:
        Singleton BedrockTitanEmbeddingProvider instance
    """
    global _embedding_provider_instance
    
    if _embedding_provider_instance is None:
        _embedding_provider_instance = BedrockTitanEmbeddingProvider(
            region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            model=os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0"),
            use_cache=True,
            cache_file=os.getenv("EMBEDDING_CACHE_FILE", "/tmp/embedding_cache.pkl")
        )
    
    return _embedding_provider_instance


def reset_embedding_provider():
    """Reset the singleton instance (useful for testing)"""
    global _embedding_provider_instance
    _embedding_provider_instance = None
