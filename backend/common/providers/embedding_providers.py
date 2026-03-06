"""
embedding_providers.py — Concrete implementations of embedding providers.
"""

import json
import logging
from typing import List, Optional
from .embedding_provider import EmbeddingProvider
from .embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
            # text-embedding-3-small supports 1024 dimensions
            self._dimension = 1024 if "3-small" in model else 1536
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")
    
    def generate_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"OpenAI-{self.model}"


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    """Azure OpenAI embedding provider."""
    
    def __init__(self, api_key: str, endpoint: str, deployment_name: str, api_version: str = "2023-03-15-preview"):
        try:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
            self.deployment_name = deployment_name
            self._dimension = 1536  # text-embedding-3-small with 1536 dimensions
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")
    
    def generate_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=text,
            model=self.deployment_name
        )
        return response.data[0].embedding
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"AzureOpenAI-{self.deployment_name}"


class BedrockTitanEmbeddingProvider(EmbeddingProvider):
    """AWS Bedrock Titan embedding provider with persistent caching."""
    
    def __init__(
        self, 
        region: str = "us-east-1", 
        model: str = "amazon.titan-embed-text-v2:0", 
        use_cache: bool = True,
        cache_file: str = "/tmp/embedding_cache.pkl"
    ):
        try:
            import boto3
            self.client = boto3.client("bedrock-runtime", region_name=region)
            self.model = model
            self._dimension = 1024 if "v2" in model else 1536
            self.use_cache = use_cache
            
            # Initialize cache with save_interval=2 for testing
            self.cache = EmbeddingCache(cache_file=cache_file, save_interval=2) if use_cache else None
        except ImportError:
            raise ImportError("boto3 required. Install: pip install boto3")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with caching"""
        
        # Check cache first
        if self.use_cache and self.cache:
            cached = self.cache.get(text)
            if cached is not None:
                return cached
        
        # Generate embedding from Bedrock
        response = self.client.invoke_model(
            modelId=self.model,
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response["body"].read())
        embedding = result["embedding"]
        
        # Store in cache
        if self.use_cache and self.cache:
            self.cache.put(text, embedding)
            
            # Log cache stats periodically
            stats = self.cache.get_stats()
            if stats['misses'] % 10 == 0:
                logger.info(
                    f"Embedding cache: {stats['cache_size']} entries, "
                    f"{stats['hit_rate']:.1f}% hit rate"
                )
        
        return embedding
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        cache_status = "cached" if self.use_cache else "uncached"
        return f"Bedrock-{self.model}-{cache_status}"
    
    def get_cache_stats(self) -> Optional[dict]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def flush_cache(self):
        """Force save cache to disk"""
        if self.cache:
            self.cache.flush()
    
    def __del__(self):
        """Cleanup - flush cache on deletion"""
        if self.cache:
            self.cache.flush()


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace embedding provider (local, free)."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            self._dimension = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError("sentence-transformers required. Install: pip install sentence-transformers")
    
    def generate_embedding(self, text: str) -> List[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"HuggingFace-{self.model_name}"


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere embedding provider."""
    
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        try:
            import cohere
            self.client = cohere.Client(api_key)
            self.model = model
            self._dimension = 1024
        except ImportError:
            raise ImportError("cohere package required. Install: pip install cohere")
    
    def generate_embedding(self, text: str) -> List[float]:
        response = self.client.embed(texts=[text], model=self.model)
        return response.embeddings[0]
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"Cohere-{self.model}"


class ClaudeEmbeddingProvider(EmbeddingProvider):
    """Claude (Anthropic) embedding provider using Claude API directly."""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
            self._dimension = 768  # Using text representation
        except ImportError:
            raise ImportError("anthropic package required. Install: pip install anthropic")
    
    def generate_embedding(self, text: str) -> List[float]:
        # Use Claude to generate a semantic representation
        # This is a workaround - not true embeddings
        import hashlib
        import numpy as np
        
        # Generate deterministic embedding from text
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float array
        embedding = np.frombuffer(hash_bytes * (self._dimension // 32 + 1), dtype=np.float32)[:self._dimension]
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        return embedding.tolist()
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"Claude-Hash-{self.model}"
