"""Redis caching layer for generated content."""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from config.redis_client import redis_client

logger = logging.getLogger(__name__)


class ContentCacheManager:
    """Manage Redis caching for generated educational content."""
    
    # Cache TTL in seconds (7 days)
    DEFAULT_TTL = 7 * 24 * 60 * 60
    
    # Cache key namespaces
    LESSON_PREFIX = "content:lesson"
    QUIZ_PREFIX = "content:quiz"
    EXERCISE_PREFIX = "content:exercise"
    RECAP_PREFIX = "content:recap"
    VARIATION_PREFIX = "content:variation"
    STATS_PREFIX = "content:stats"
    
    def __init__(self):
        """Initialize cache manager."""
        self.redis_wrapper = redis_client
        self.redis = None  # Will be set on first use
        logger.info("ContentCacheManager initialized")
    
    async def _ensure_connected(self):
        """Ensure Redis client is connected and available."""
        if self.redis is None:
            if not self.redis_wrapper.cache_client:
                await self.redis_wrapper.connect()
            self.redis = self.redis_wrapper.cache_client
    
    async def get_cached_content(
        self,
        topic: str,
        content_type: str,
        difficulty: str,
        cognitive_load_range: str
    ) -> Optional[str]:
        """
        Retrieve cached content if available.
        
        Args:
            topic: Content topic
            content_type: Type (lesson, quiz, exercise, recap)
            difficulty: Difficulty level
            cognitive_load_range: Bucketed cognitive load (low, medium, high)
        
        Returns:
            Cached content if found, None otherwise
        """
        try:
            await self._ensure_connected()
            
            cache_key = self._generate_cache_key(
                topic,
                content_type,
                difficulty,
                cognitive_load_range
            )
            
            content = await self.redis.get(cache_key)
            
            if content:
                await self._increment_cache_hits()
                logger.info(f"Cache HIT for key: {cache_key}")
                return content.decode('utf-8') if isinstance(content, bytes) else content
            else:
                await self._increment_cache_misses()
                logger.info(f"Cache MISS for key: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    async def cache_content(
        self,
        content: str,
        topic: str,
        content_type: str,
        difficulty: str,
        cognitive_load_range: str,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store generated content in cache.
        
        Args:
            content: Content to cache
            topic: Content topic
            content_type: Type (lesson, quiz, exercise, recap)
            difficulty: Difficulty level
            cognitive_load_range: Bucketed cognitive load
            metadata: Optional metadata to store alongside content
            ttl: Time-to-live in seconds (default: 7 days)
        
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            await self._ensure_connected()
            
            cache_key = self._generate_cache_key(
                topic,
                content_type,
                difficulty,
                cognitive_load_range
            )
            
            # Store content with metadata
            cache_data = {
                'content': content,
                'metadata': metadata or {},
                'cached_at': self._get_timestamp()
            }
            
            cache_value = json.dumps(cache_data)
            ttl_seconds = ttl or self.DEFAULT_TTL
            
            await self.redis.setex(
                cache_key,
                ttl_seconds,
                cache_value
            )
            
            logger.info(f"Cached content with key: {cache_key}, TTL: {ttl_seconds}s")
            return True
            
        except Exception as e:
            logger.error(f"Error caching content: {str(e)}")
            return False
    
    async def get_similar_content(
        self,
        topic: str,
        content_type: str,
        difficulty: str
    ) -> List[str]:
        """
        Find content with similar parameters (fuzzy matching).
        
        Args:
            topic: Content topic
            content_type: Content type
            difficulty: Difficulty level
        
        Returns:
            List of similar cached content
        """
        try:
            await self._ensure_connected()
            
            # Search for keys matching pattern (without cognitive load constraint)
            topic_hash = self._hash_topic(topic)
            prefix = self._get_prefix(content_type)
            pattern = f"{prefix}:{topic_hash}:{difficulty}:*"
            
            keys = await self.redis.keys(pattern)
            
            similar_content = []
            for key in keys:
                content_data = await self.redis.get(key)
                if content_data:
                    data = json.loads(content_data)
                    similar_content.append(data['content'])
            
            logger.info(f"Found {len(similar_content)} similar content items")
            return similar_content
            
        except Exception as e:
            logger.error(f"Error finding similar content: {str(e)}")
            return []
    
    async def invalidate_content(
        self,
        topic: str,
        content_type: Optional[str] = None
    ) -> int:
        """
        Invalidate cached content for a topic.
        
        Args:
            topic: Topic to invalidate
            content_type: Optional content type to limit invalidation
        
        Returns:
            Number of keys deleted
        """
        try:
            await self._ensure_connected()
            
            topic_hash = self._hash_topic(topic)
            
            if content_type:
                prefix = self._get_prefix(content_type)
                pattern = f"{prefix}:{topic_hash}:*"
            else:
                # Invalidate all content types for this topic
                pattern = f"content:*:{topic_hash}:*"
            
            keys = await self.redis.keys(pattern)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for topic: {topic}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            await self._ensure_connected()
            
            hits = await self.redis.get(f"{self.STATS_PREFIX}:hits") or 0
            misses = await self.redis.get(f"{self.STATS_PREFIX}:misses") or 0
            
            hits = int(hits)
            misses = int(misses)
            total = hits + misses
            
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            # Get approximate memory usage
            info = await self.redis.info('memory')
            memory_used = info.get('used_memory_human', 'Unknown')
            
            # Count cached items
            all_keys = await self.redis.keys("content:*")
            total_cached = len([k for k in all_keys if not k.startswith(f"{self.STATS_PREFIX}:")])
            
            return {
                'cache_hits': hits,
                'cache_misses': misses,
                'hit_rate_percent': round(hit_rate, 2),
                'total_cached_items': total_cached,
                'memory_used': memory_used
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                'error': str(e),
                'cache_hits': 0,
                'cache_misses': 0,
                'hit_rate_percent': 0
            }
    
    async def warm_cache(
        self,
        common_topics: List[str],
        content_generator
    ) -> int:
        """
        Pre-populate cache with common topics.
        
        Args:
            common_topics: List of frequently requested topics
            content_generator: ContentGenerator instance
        
        Returns:
            Number of items cached
        """
        cached_count = 0
        
        for topic in common_topics:
            for difficulty in ['easy', 'medium', 'hard']:
                for load_range in ['low', 'medium', 'high']:
                    # Generate and cache lesson
                    try:
                        content = await content_generator.generate_lesson(
                            topic=topic,
                            difficulty=difficulty,
                            prerequisites=[],
                            estimated_minutes=15,
                            cognitive_load_profile={'current_score': 50}
                        )
                        
                        if await self.cache_content(
                            content,
                            topic,
                            'lesson',
                            difficulty,
                            load_range
                        ):
                            cached_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error warming cache for {topic}: {str(e)}")
        
        logger.info(f"Cache warming completed: {cached_count} items cached")
        return cached_count
    
    def _generate_cache_key(
        self,
        topic: str,
        content_type: str,
        difficulty: str,
        cognitive_load_range: str
    ) -> str:
        """Generate Redis cache key."""
        topic_hash = self._hash_topic(topic)
        prefix = self._get_prefix(content_type)
        return f"{prefix}:{topic_hash}:{difficulty}:{cognitive_load_range}"
    
    def _hash_topic(self, topic: str) -> str:
        """Generate hash for topic to use in cache key."""
        return hashlib.md5(topic.lower().strip().encode()).hexdigest()[:12]
    
    def _get_prefix(self, content_type: str) -> str:
        """Get cache key prefix for content type."""
        prefixes = {
            'lesson': self.LESSON_PREFIX,
            'quiz': self.QUIZ_PREFIX,
            'exercise': self.EXERCISE_PREFIX,
            'recap': self.RECAP_PREFIX,
            'variation': self.VARIATION_PREFIX
        }
        return prefixes.get(content_type.lower(), self.LESSON_PREFIX)
    
    def _bucket_cognitive_load(self, score: float) -> str:
        """Bucket cognitive load score into range."""
        if score > 70:
            return 'high'
        elif score > 30:
            return 'medium'
        else:
            return 'low'
    
    async def _increment_cache_hits(self):
        """Increment cache hit counter."""
        try:
            await self._ensure_connected()
            await self.redis.incr(f"{self.STATS_PREFIX}:hits")
        except:
            pass
    
    async def _increment_cache_misses(self):
        """Increment cache miss counter."""
        try:
            await self._ensure_connected()
            await self.redis.incr(f"{self.STATS_PREFIX}:misses")
        except:
            pass
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
