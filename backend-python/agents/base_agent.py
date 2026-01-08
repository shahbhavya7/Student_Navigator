from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.base import BaseLanguageModel
import logging
import time

from agents.state import AgentState
from config.redis_client import redis_client
from config.settings import settings


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str, llm: Optional[BaseLanguageModel] = None):
        self.name = name
        self.llm = llm or ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7,
            google_api_key=settings.GOOGLE_API_KEY
        )
        self.logger = logging.getLogger(name)
        self.execution_count = 0
        self.error_count = 0
    
    @abstractmethod
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute agent logic and return output
        
        Args:
            state: Current agent state
            
        Returns:
            Dict with agent output to merge into state
        """
        pass
    
    async def publish_event(self, event_type: str, data: Dict):
        """Publish agent event to Redis pub/sub"""
        try:
            await redis_client.publish_agent_event(
                channel=f"agent:{self.name}",
                message={
                    "type": event_type,
                    "agent": self.name,
                    "data": data,
                    "timestamp": int(time.time())
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
    
    def log_execution(self, state: AgentState, output: Dict):
        """Log agent execution for monitoring"""
        self.execution_count += 1
        self.logger.info(
            f"Executed for student {state['student_id']} "
            f"(session {state['session_id']}): {output}"
        )
    
    def log_error(self, error: Exception, state: AgentState):
        """Log agent error"""
        self.error_count += 1
        self.logger.error(
            f"Error for student {state['student_id']} "
            f"(session {state['session_id']}): {error}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.execution_count - self.error_count) / self.execution_count * 100
                if self.execution_count > 0 else 0
            )
        }
