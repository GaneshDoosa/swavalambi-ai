"""
tts_cache_service.py — Redis-based TTS audio caching service
"""

import redis
import json
import hashlib
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TTSCacheService:
    """Redis-based cache for TTS audio to reduce API calls and improve latency."""
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")
        
        try:
            pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=False,  # We store binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=20
            )
            self.redis_client = redis.Redis(connection_pool=pool)
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"TTS Cache connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.warning(f"TTS Cache disabled - Redis connection failed: {e}")
            self.enabled = False
            self.redis_client = None
    
    def _generate_cache_key(self, text: str, language: str, speaker: str, cache_type: str = "msg") -> str:
        """Generate cache key from text, language, and speaker."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"tts:{cache_type}:{language}:{speaker}:{text_hash}"
    
    def get_cached_audio(self, text: str, language: str, speaker: str) -> Optional[Dict[str, Any]]:
        """
        Get cached TTS audio if available.
        
        Returns:
            Dict with audio_base64, audio_format, etc. or None if not cached
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self._generate_cache_key(text, language, speaker)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Increment hit counter
                self.redis_client.incr("tts:metrics:hits")
                logger.info(f"[TTS-CACHE] HIT: {language}/{speaker}, {len(text)} chars")
                return json.loads(cached_data)
            else:
                # Increment miss counter
                self.redis_client.incr("tts:metrics:misses")
                logger.info(f"[TTS-CACHE] MISS: {language}/{speaker}, {len(text)} chars")
                return None
        except Exception as e:
            logger.error(f"[TTS-CACHE] Error reading cache: {e}")
            return None
    
    def cache_audio(self, text: str, language: str, speaker: str, audio_data: Dict[str, Any], ttl: int = 2592000):
        """
        Cache TTS audio result.
        
        Args:
            text: Original text
            language: Language code
            speaker: Speaker ID
            audio_data: Dict with audio_base64, audio_format, etc.
            ttl: Time to live in seconds (default 30 days)
        """
        if not self.enabled:
            return
        
        try:
            cache_key = self._generate_cache_key(text, language, speaker)
            
            # Store audio data as JSON
            cache_value = json.dumps({
                "audio_base64": audio_data.get("audio_base64"),
                "audio_format": audio_data.get("audio_format"),
                "text": text,
                "language": language,
                "speaker": speaker,
                "provider": audio_data.get("provider", "sarvam")
            })
            
            self.redis_client.setex(cache_key, ttl, cache_value)
            logger.info(f"[TTS-CACHE] STORED: {language}/{speaker}, {len(text)} chars, TTL={ttl}s")
        except Exception as e:
            logger.error(f"[TTS-CACHE] Error storing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            hits = int(self.redis_client.get("tts:metrics:hits") or 0)
            misses = int(self.redis_client.get("tts:metrics:misses") or 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return {
                "enabled": True,
                "hits": hits,
                "misses": misses,
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 1)
            }
        except Exception as e:
            logger.error(f"[TTS-CACHE] Error getting stats: {e}")
            return {"enabled": True, "error": str(e)}


# Singleton instance
_tts_cache_service = None

def get_tts_cache_service() -> TTSCacheService:
    """Get or create TTS cache service singleton."""
    global _tts_cache_service
    if _tts_cache_service is None:
        _tts_cache_service = TTSCacheService()
    return _tts_cache_service
