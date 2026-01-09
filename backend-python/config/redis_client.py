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
    
    async def get_cognitive_load_history(self, student_id: str, days: int = 7, 
                                         time_range: str = None, include_metadata: bool = False) -> List:
        """
        Get cognitive load history from time-series data with enhanced options.
        
        Args:
            student_id: Student identifier
            days: Number of days of history (used if time_range not specified)
            time_range: Specific time range (last_hour, last_day, last_week, last_month)
            include_metadata: Whether to include full metadata or just scores
            
        Returns:
            List of cognitive load data (scores or full metadata)
        """
        try:
            key = f"clr:{student_id}"
            
            # Calculate time range
            if time_range:
                range_map = {
                    'last_hour': 1 * 60 * 60 * 1000,
                    'last_day': 24 * 60 * 60 * 1000,
                    'last_week': 7 * 24 * 60 * 60 * 1000,
                    'last_month': 30 * 24 * 60 * 60 * 1000
                }
                time_delta = range_map.get(time_range, 7 * 24 * 60 * 60 * 1000)
            else:
                time_delta = days * 24 * 60 * 60 * 1000
            
            end_time = int(time.time() * 1000)
            start_time = end_time - time_delta
            
            # Get range from sorted set
            results = await self.data_client.zrangebyscore(
                key, start_time, end_time, withscores=True
            )
            
            if include_metadata:
                # Return full metadata
                history = []
                for value, timestamp in results:
                    try:
                        import json
                        data = json.loads(value) if isinstance(value, str) else value
                        history.append({
                            'timestamp': int(timestamp),
                            'score': data.get('score', 0) if isinstance(data, dict) else float(data),
                            'metadata': data if isinstance(data, dict) else {}
                        })
                    except:
                        continue
                return history
            else:
                # Return just scores
                scores = [float(score) for score, _ in results if score]
                return scores
                
        except Exception as e:
            logger.error(f"Error retrieving cognitive load history: {e}")
            return []
    
    def store_clr_timeseries(self, student_id: str, timestamp: int, score: float, metadata: dict = None):
        """
        Store cognitive load in Redis time-series (sorted set).
        
        Args:
            student_id: Student identifier
            timestamp: Unix timestamp in milliseconds
            score: Cognitive load score
            metadata: Optional metadata dictionary
        """
        try:
            key = f"clr:{student_id}"
            
            # If metadata provided, store as JSON
            if metadata:
                import json
                value = json.dumps({
                    'score': score,
                    **metadata
                })
            else:
                value = str(score)
            
            # Store in sorted set
            self.data_client.zadd(key, {value: timestamp})
            
            # Set TTL of 30 days
            self.data_client.expire(key, 30 * 24 * 60 * 60)
            
            # Store metadata in separate hash if provided
            if metadata:
                meta_key = f"clr_meta:{student_id}:{timestamp}"
                self.data_client.hset(meta_key, mapping=metadata)
                self.data_client.expire(meta_key, 30 * 24 * 60 * 60)
                
        except Exception as e:
            logger.error(f"Error storing CLR timeseries: {e}")


# Global Redis client instance
redis_client = RedisClient()
