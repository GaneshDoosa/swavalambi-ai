"""
embedding_cache.py — Persistent cache for embeddings
"""

import logging
import hashlib
import pickle
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Persistent cache for embeddings with file system backup"""
    
    def __init__(self, cache_file: str = "/tmp/embedding_cache.pkl", save_interval: int = 50):
        """
        Initialize embedding cache
        
        Args:
            cache_file: Path to cache file (default: /tmp/embedding_cache.pkl)
            save_interval: Save to disk every N new entries
        """
        self.cache_file = Path(cache_file)
        self.save_interval = save_interval
        self._cache: Dict[str, List[float]] = {}
        self._hits = 0
        self._misses = 0
        self._save_counter = 0
        self._dirty = False
        
        # Load cache from disk
        self._load_from_disk()
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text using MD5 hash"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_from_disk(self):
        """Load cache from disk on startup"""
        if not self.cache_file.exists():
            logger.info(f"No cache file found at {self.cache_file}, starting with empty cache")
            return
        
        try:
            with open(self.cache_file, 'rb') as f:
                self._cache = pickle.load(f)
            logger.info(f"Loaded {len(self._cache)} embeddings from cache: {self.cache_file}")
        except Exception as e:
            logger.warning(f"Failed to load cache from {self.cache_file}: {e}. Starting with empty cache.")
            self._cache = {}
    
    def _save_to_disk(self):
        """Save cache to disk"""
        if not self._dirty:
            return
        
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
            
            self._dirty = False
            logger.info(f"Saved {len(self._cache)} embeddings to cache: {self.cache_file}")
        except Exception as e:
            # Silently fail if filesystem is not writable
            logger.debug(f"Failed to save cache to {self.cache_file}: {e}")
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache
        
        Args:
            text: Text to get embedding for
            
        Returns:
            Cached embedding or None if not found
        """
        cache_key = self._get_cache_key(text)
        
        if cache_key in self._cache:
            self._hits += 1
            logger.info(f"✅ Cache HIT for: '{text[:60]}...'")
            
            # Log stats every 10 hits
            if self._hits % 10 == 0:
                stats = self.get_stats()
                logger.info(
                    f"📊 Cache Stats: {stats['cache_size']} entries, "
                    f"{stats['hit_rate']:.1f}% hit rate "
                    f"({stats['hits']} hits / {stats['total_requests']} total)"
                )
            
            return self._cache[cache_key]
        
        self._misses += 1
        logger.info(f"❌ Cache MISS for: '{text[:60]}...'")
        return None
    
    def put(self, text: str, embedding: List[float]):
        """
        Store embedding in cache
        
        Args:
            text: Text that was embedded
            embedding: The embedding vector
        """
        cache_key = self._get_cache_key(text)
        self._cache[cache_key] = embedding
        self._dirty = True
        self._save_counter += 1
        
        # Periodic save to disk
        if self._save_counter >= self.save_interval:
            self._save_to_disk()
            self._save_counter = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "cache_file": str(self.cache_file),
            "dirty": self._dirty
        }
    
    def clear(self):
        """Clear the cache"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._dirty = True
        self._save_to_disk()
        logger.info("Cache cleared")
    
    def flush(self):
        """Force save cache to disk"""
        self._save_to_disk()
    
    def __del__(self):
        """Save cache on cleanup"""
        if self._dirty:
            self._save_to_disk()
