"""
embedding_cache.py — Persistent cache for embeddings
"""

import logging
import hashlib
import pickle
import threading
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Persistent cache for embeddings with file system backup"""
    
    def __init__(self, cache_file: str = "/tmp/embedding_cache.pkl", save_interval: int = 10):
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
        
        # Per-key locks for concurrent access to different keys
        self._key_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._key_locks_lock = threading.Lock()  # Lock for managing key locks
        
        # Global lock only for metadata operations (hits, misses, stats)
        self._metadata_lock = threading.Lock()
        
        logger.info(f"Initializing cache with file: {self.cache_file}")
        
        # Load cache from disk
        self._load_from_disk()
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text using MD5 hash"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_key_lock(self, cache_key: str) -> threading.Lock:
        """Get or create a lock for a specific cache key"""
        with self._key_locks_lock:
            return self._key_locks[cache_key]
    
    def _load_from_disk(self):
        """Load cache from disk on startup"""
        if not self.cache_file.exists():
            logger.info(f"No cache file found, starting with empty cache")
            return
        
        try:
            with open(self.cache_file, 'rb') as f:
                self._cache = pickle.load(f)
            logger.info(f"✅ Loaded {len(self._cache)} embeddings from cache")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}. Starting with empty cache")
            self._cache = {}
    
    def _save_to_disk(self):
        """
        Save cache to disk
        
        Gracefully handles failures - cache continues to work in-memory even if
        persistence fails (e.g., in read-only filesystems or when /tmp is unavailable)
        """
        if not self._dirty:
            return
        
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
            
            self._dirty = False
            logger.info(f"💾 Saved {len(self._cache)} embeddings to cache")
        except (PermissionError, OSError, IOError) as e:
            # Gracefully handle filesystem errors - cache continues in-memory
            logger.warning(f"Failed to save cache: {e}. Cache continues in-memory only")
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache (thread-safe per key)
        
        Args:
            text: Text to get embedding for
            
        Returns:
            Cached embedding or None if not found
        """
        cache_key = self._get_cache_key(text)
        key_lock = self._get_key_lock(cache_key)
        
        # Acquire lock for this specific key
        with key_lock:
            if cache_key in self._cache:
                # Update metadata with global lock
                with self._metadata_lock:
                    self._hits += 1
                    hits = self._hits
                
                # Log stats every 10 hits (not every hit to reduce noise)
                if hits % 10 == 0:
                    stats = self.get_stats()
                    logger.info(
                        f"📊 Cache: {stats['cache_size']} entries, "
                        f"{stats['hit_rate']:.1f}% hit rate "
                        f"({stats['hits']} hits / {stats['total_requests']} requests)"
                    )
                
                return self._cache[cache_key]
            
            # Update metadata with global lock
            with self._metadata_lock:
                self._misses += 1
            
            return None
    
    def put(self, text: str, embedding: List[float]):
        """
        Store embedding in cache (thread-safe per key)
        
        Args:
            text: Text that was embedded
            embedding: The embedding vector
        """
        cache_key = self._get_cache_key(text)
        key_lock = self._get_key_lock(cache_key)
        
        # Acquire lock for this specific key
        with key_lock:
            self._cache[cache_key] = embedding
            self._dirty = True
            
            # Update save counter with metadata lock
            with self._metadata_lock:
                self._save_counter += 1
                save_counter = self._save_counter
            
            # Periodic save to disk (outside of key lock to avoid blocking other keys)
            if save_counter >= self.save_interval:
                self._save_to_disk()
                with self._metadata_lock:
                    self._save_counter = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics (thread-safe)"""
        with self._metadata_lock:
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
        """Clear the cache (thread-safe)"""
        with self._metadata_lock:
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
