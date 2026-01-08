import asyncio
import logging
import json

from config.redis_client import redis_client
from agents.graph import execute_agent_workflow

logger = logging.getLogger(__name__)


class PubSubListener:
    """Redis pub/sub listener for real-time events"""
    
    def __init__(self):
        self.running = False
        self.task = None
        self.pubsub = None
    
    async def start(self):
        """Start listening to Redis pub/sub channels"""
        if self.running:
            logger.warning("PubSub listener already running")
            return
        
        self.running = True
        
        # Subscribe to channels
        channels = [
            "behavior:events",
            "sessions:ended",
            "quiz:completed",
            "cognitive:threshold"
        ]
        
        self.pubsub = await redis_client.subscribe_to_channels(channels)
        
        # Start listening task
        self.task = asyncio.create_task(self._listen_loop())
        logger.info(f"📡 PubSub listener started for channels: {channels}")
    
    async def stop(self):
        """Stop the pub/sub listener"""
        self.running = False
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ PubSub listener stopped")
    
    async def _listen_loop(self):
        """Main listening loop"""
        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break
                
                if message["type"] == "message":
                    await self._handle_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
    
    async def _handle_message(self, message: dict):
        """Handle incoming pub/sub message"""
        try:
            channel = message["channel"]
            data = json.loads(message["data"])
            
            logger.debug(f"📨 Received message on {channel}: {data.get('type')}")
            
            if channel == "sessions:ended":
                await self._handle_session_ended(data)
            elif channel == "quiz:completed":
                await self._handle_quiz_completed(data)
            elif channel == "cognitive:threshold":
                await self._handle_cognitive_threshold_breach(data)
            elif channel == "behavior:events":
                await self._handle_behavior_event(data)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_session_ended(self, message: dict):
        """Trigger agent workflow when session ends"""
        try:
            student_id = message.get("student_id")
            session_id = message.get("session_id")
            
            if not student_id or not session_id:
                return
            
            logger.info(f"🎬 Session ended for student {student_id}, triggering workflow")
            
            # Execute agent workflow
            await execute_agent_workflow(student_id, session_id)
            
        except Exception as e:
            logger.error(f"Error handling session ended: {e}")
    
    async def _handle_quiz_completed(self, message: dict):
        """Trigger performance analysis after quiz"""
        try:
            student_id = message.get("student_id")
            session_id = message.get("session_id")
            quiz_id = message.get("quiz_id")
            score = message.get("score", 0)
            
            logger.info(
                f"📝 Quiz {quiz_id} completed by student {student_id} "
                f"with score {score}"
            )
            
            # If score is low, trigger immediate analysis
            if score < 60:
                await execute_agent_workflow(student_id, session_id)
            
        except Exception as e:
            logger.error(f"Error handling quiz completed: {e}")
    
    async def _handle_cognitive_threshold_breach(self, message: dict):
        """Immediate intervention on high cognitive load"""
        try:
            student_id = message.get("student_id")
            session_id = message.get("session_id")
            cognitive_load = message.get("cognitive_load", 0)
            
            logger.warning(
                f"🚨 Cognitive threshold breach for student {student_id}: "
                f"load={cognitive_load}"
            )
            
            # Trigger immediate workflow with intervention
            await execute_agent_workflow(student_id, session_id)
            
        except Exception as e:
            logger.error(f"Error handling cognitive threshold breach: {e}")
    
    async def _handle_behavior_event(self, message: dict):
        """Handle real-time behavioral events"""
        try:
            event_type = message.get("eventType")
            priority = message.get("priority", "normal")
            
            # Only process critical events in real-time
            if priority == "CRITICAL":
                student_id = message.get("studentId")
                session_id = message.get("sessionId")
                
                logger.warning(
                    f"⚠️ Critical behavior event for student {student_id}: {event_type}"
                )
                
                # Could trigger immediate mini-workflow here
                
        except Exception as e:
            logger.error(f"Error handling behavior event: {e}")


# Global pub/sub listener instance
pubsub_listener = PubSubListener()
