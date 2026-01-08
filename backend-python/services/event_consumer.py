import asyncio
import logging
from typing import List, Dict
import time

from config.redis_client import redis_client
from agents.graph import execute_agent_workflow

logger = logging.getLogger(__name__)


class EventConsumer:
    """Service to periodically consume behavioral events from Redis"""
    
    def __init__(self, interval: int = 30):
        self.interval = interval
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the event consumer"""
        if self.running:
            logger.warning("Event consumer already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._consume_loop())
        logger.info(f"🔄 Event consumer started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the event consumer"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Event consumer stopped")
    
    async def _consume_loop(self):
        """Main consumption loop"""
        while self.running:
            try:
                await self._process_pending_sessions()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
                await asyncio.sleep(self.interval)
    
    async def _process_pending_sessions(self):
        """Process sessions marked for immediate flush"""
        try:
            # Get sessions marked for pending flush
            pending_sessions = await redis_client.data_client.smembers("sessions:pending_flush")
            
            if not pending_sessions:
                return
            
            logger.info(f"📋 Processing {len(pending_sessions)} pending sessions")
            
            for session_entry in pending_sessions:
                try:
                    # Parse session entry (format: "studentId:sessionId")
                    parts = session_entry.split(":")
                    if len(parts) != 2:
                        continue
                    
                    student_id, session_id = parts
                    
                    # Execute agent workflow
                    result = await execute_agent_workflow(student_id, session_id)
                    
                    # Remove from pending set
                    await redis_client.data_client.srem("sessions:pending_flush", session_entry)
                    
                    logger.info(f"✅ Processed session {session_id} for student {student_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing session {session_entry}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing pending sessions: {e}")


# Global event consumer instance
event_consumer = EventConsumer(interval=30)
