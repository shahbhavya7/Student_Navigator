import redis.asyncio as aioredis
from redis.asyncio import Redis
from typing import List, Dict, Optional
import json
import logging
import time

from config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with helper methods"""
    
    def __init__(self):
        self.data_client: Optional[Redis] = None
        self.pubsub_client: Optional[Redis] = None
        self.cache_client: Optional[Redis] = None
        
    async def connect(self):
        """Initialize Redis connections"""
        try:
            # Data client for reading behavioral events
            self.data_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            
            # Pub/Sub client
            self.pubsub_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Cache client for agent state
            self.cache_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            
            # Test connections
            await self.data_client.ping()
            await self.pubsub_client.ping()
            await self.cache_client.ping()
            
            logger.info("✅ Redis connections initialized")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connections"""
        if self.data_client:
            await self.data_client.close()
        if self.pubsub_client:
            await self.pubsub_client.close()
        if self.cache_client:
            await self.cache_client.close()
        logger.info("🔌 Redis connections closed")
    
    async def get_behavioral_events(self, session_id: str) -> List[Dict]:
        """Retrieve buffered events from Redis list"""
        try:
            key = f"behavior:{session_id}"
            # Get all events from list (lrange 0 -1)
            raw_events = await self.data_client.lrange(key, 0, -1)
            
            # Parse JSON events
            events = []
            for raw in raw_events:
                try:
                    event = json.loads(raw)
                    events.append(event)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse event: {raw}")
            
            logger.info(f"📥 Retrieved {len(events)} events for session {session_id}")
            return events
        except Exception as e:
            logger.error(f"Error retrieving behavioral events: {e}")
            return []
    
    async def publish_agent_event(self, channel: str, message: dict):
        """Publish to pub/sub channel"""
        try:
            await self.pubsub_client.publish(channel, json.dumps(message))
            logger.debug(f"📤 Published to {channel}: {message.get('type')}")
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")
    
    async def subscribe_to_channels(self, channels: List[str]):
        """Subscribe to multiple channels"""
        pubsub = self.pubsub_client.pubsub()
        await pubsub.subscribe(*channels)
        logger.info(f"📡 Subscribed to channels: {channels}")
        return pubsub
    
    async def set_agent_state(self, agent_id: str, state: dict, ttl: int = 3600):
        """Cache agent state with TTL"""
        try:
            key = f"agent_state:{agent_id}"
            await self.cache_client.setex(key, ttl, json.dumps(state))
            logger.debug(f"💾 Cached state for {agent_id}")
        except Exception as e:
            logger.error(f"Error caching agent state: {e}")
    
    async def get_agent_state(self, agent_id: str) -> Optional[Dict]:
        """Retrieve cached agent state"""
        try:
            key = f"agent_state:{agent_id}"
            state_json = await self.cache_client.get(key)
            if state_json:
                return json.loads(state_json)
            return None
        except Exception as e:
            logger.error(f"Error retrieving agent state: {e}")
            return None
    
    async def get_cognitive_load_history(self, student_id: str, days: int = 7) -> List[float]:
        """Get cognitive load history from time-series data"""
        try:
            key = f"clr:{student_id}"
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            # Get range from sorted set
            results = await self.data_client.zrangebyscore(
                key, start_time, end_time, withscores=False
            )
            
            # Parse scores
            scores = [float(score) for score in results if score]
            return scores
        except Exception as e:
            logger.error(f"Error retrieving cognitive load history: {e}")
            return []


# Global Redis client instance
redis_client = RedisClient()
