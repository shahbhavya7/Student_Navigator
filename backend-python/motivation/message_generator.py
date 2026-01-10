"""
Personalized Message Generator

Uses LangChain with Google Gemini to generate personalized,
context-aware intervention messages.
"""

from typing import Dict, Any
import logging
import hashlib
import json

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from motivation.intervention_types import InterventionType
from config.redis_client import redis_client
from config.settings import settings


class PersonalizedMessageGenerator:
    """Generates personalized intervention messages using LLM"""
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        self.logger = logging.getLogger("PersonalizedMessageGenerator")
        self._init_prompt_templates()
    
    def _init_prompt_templates(self):
        """Initialize intervention-specific prompt templates"""
        
        # Base system message for all interventions
        base_system_message = """You are an empathetic learning coach providing supportive interventions to students. 
Your goal is to help students succeed by offering timely, personalized guidance.

Guidelines:
- Be brief (1-2 sentences maximum)
- Be encouraging and positive
- Be specific to the student's situation
- Use a warm, supportive tone
- Focus on actionable advice
- Avoid being preachy or condescending"""
        
        # Break suggestion template
        self.break_prompt = ChatPromptTemplate.from_messages([
            ("system", base_system_message),
            ("human", """Student Context:
- Cognitive Load: {cognitive_load}/100
- Session Duration: {session_duration} minutes
- Fatigue Level: {fatigue_level}
- Time of Day: {time_of_day}

The student has been working intensively and their cognitive load is high.
Generate a brief, encouraging message suggesting they take a break.""")
        ])
        
        # Topic switch template
        self.topic_switch_prompt = ChatPromptTemplate.from_messages([
            ("system", base_system_message),
            ("human", """Student Context:
- Current Topic: {current_topic}
- Quiz Accuracy: {quiz_accuracy}%
- Avoided Topics: {avoided_topics}
- Error Patterns: {error_patterns}

The student is struggling with the current topic or avoiding it.
Generate a brief message suggesting switching to an easier topic or reviewing prerequisites.""")
        ])
        
        # Recap prompt template
        self.recap_prompt = ChatPromptTemplate.from_messages([
            ("system", base_system_message),
            ("human", """Student Context:
- Quiz Accuracy: {quiz_accuracy}%
- Weak Topics: {weak_topics}
- Recent Performance: {performance_trend}

The student's performance indicates they need to review certain topics.
Generate a brief message encouraging review of weak topics before proceeding.""")
        ])
        
        # Encouragement template
        self.encouragement_prompt = ChatPromptTemplate.from_messages([
            ("system", base_system_message),
            ("human", """Student Context:
- Mood Score: {mood_score}
- Sentiment: {sentiment}
- Recent Performance: {quiz_accuracy}%
- Dropout Risk: {dropout_risk}
- Progress: {progress}%

The student is feeling discouraged or at risk of dropping out.
Generate a brief, uplifting message that acknowledges their effort and encourages them to continue.""")
        ])
        
        # Difficulty adjustment template
        self.difficulty_adjustment_prompt = ChatPromptTemplate.from_messages([
            ("system", base_system_message),
            ("human", """Student Context:
- Current Difficulty: {current_difficulty}
- Quiz Accuracy: {quiz_accuracy}%
- Plateau Detected: {plateau_detected}
- Learning Velocity: {learning_velocity}

We're adjusting the difficulty level to better match the student's current capabilities.
Generate a brief message explaining the adjustment in a positive way.""")
        ])
    
    async def generate_message(
        self, 
        intervention_type: str,
        context: Dict[str, Any],
        student_profile: Dict[str, Any]
    ) -> str:
        """
        Generate personalized intervention message.
        
        Args:
            intervention_type: Type of intervention
            context: Context data for message generation
            student_profile: Student profile information
            
        Returns:
            Personalized message string
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(intervention_type, context, student_profile)
            cached_message = await self._get_cached_message(cache_key)
            if cached_message:
                self.logger.debug(f"Using cached message for {intervention_type}")
                return cached_message
            
            # Get appropriate prompt template
            prompt = self._get_prompt_template(intervention_type)
            
            # Build context string
            prompt_values = self._build_prompt_values(context, student_profile)
            
            # Generate message using LLM
            message = await self._invoke_llm(prompt, prompt_values, intervention_type)
            
            # Cache the message
            await self._cache_message(cache_key, message)
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error generating message: {e}", exc_info=True)
            # Return fallback template message
            return self._get_fallback_message(intervention_type)
    
    def _get_prompt_template(self, intervention_type: str) -> ChatPromptTemplate:
        """Get prompt template for intervention type"""
        type_map = {
            InterventionType.BREAK_SUGGESTION: self.break_prompt,
            InterventionType.TOPIC_SWITCH: self.topic_switch_prompt,
            InterventionType.RECAP_PROMPT: self.recap_prompt,
            InterventionType.ENCOURAGEMENT: self.encouragement_prompt,
            InterventionType.DIFFICULTY_ADJUSTMENT: self.difficulty_adjustment_prompt,
        }
        return type_map.get(intervention_type, self.encouragement_prompt)
    
    def _build_prompt_values(
        self, 
        context: Dict[str, Any], 
        student_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build values dict for prompt template"""
        return {
            # Cognitive metrics
            "cognitive_load": context.get("cognitive_load", 50),
            "fatigue_level": context.get("fatigue_level", "moderate"),
            
            # Performance metrics
            "quiz_accuracy": context.get("quiz_accuracy", 70),
            "performance_trend": context.get("performance_trend", "stable"),
            "learning_velocity": context.get("learning_velocity", 1.0),
            
            # Engagement & mood
            "mood_score": context.get("mood_score", 0),
            "sentiment": context.get("sentiment_trend", "neutral"),
            "dropout_risk": context.get("dropout_risk", 0),
            
            # Learning context
            "current_topic": context.get("current_topic", "current lesson"),
            "weak_topics": ", ".join(context.get("weak_topics", [])) or "various topics",
            "avoided_topics": ", ".join(context.get("avoided_topics", [])) or "none",
            "error_patterns": context.get("error_patterns", "none detected"),
            
            # Session context
            "session_duration": context.get("session_duration", 0),
            "time_of_day": context.get("time_of_day", "day"),
            
            # Difficulty
            "current_difficulty": context.get("current_difficulty", "medium"),
            "plateau_detected": context.get("plateau_detected", False),
            
            # Progress
            "progress": student_profile.get("progress", 0),
        }
    
    async def _invoke_llm(
        self, 
        prompt: ChatPromptTemplate,
        values: Dict[str, Any],
        intervention_type: str
    ) -> str:
        """Invoke LLM to generate message"""
        try:
            messages = prompt.format_messages(**values)
            response = await self.llm.ainvoke(messages)
            
            # Extract text content
            if hasattr(response, 'content'):
                message = response.content.strip()
            else:
                message = str(response).strip()
            
            # Remove quotes if LLM wrapped the message
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
            
            self.logger.info(f"Generated message for {intervention_type}: {message[:50]}...")
            return message
            
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}", exc_info=True)
            raise
    
    def _get_cache_key(
        self,
        intervention_type: str,
        context: Dict[str, Any],
        student_profile: Dict[str, Any]
    ) -> str:
        """Generate cache key for message"""
        # Create a deterministic hash of the context
        context_str = json.dumps({
            "type": intervention_type,
            "cognitive_load": context.get("cognitive_load", 0) // 10 * 10,  # Round to nearest 10
            "quiz_accuracy": context.get("quiz_accuracy", 0) // 10 * 10,
            "mood_score": round(context.get("mood_score", 0), 1),
            "student_id": student_profile.get("student_id", "unknown")
        }, sort_keys=True)
        
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:12]
        return f"intervention_msg:{intervention_type}:{context_hash}"
    
    async def _get_cached_message(self, cache_key: str) -> str:
        """Retrieve cached message from Redis"""
        try:
            cached = redis_client.client.get(cache_key)
            if cached:
                return cached.decode('utf-8') if isinstance(cached, bytes) else cached
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def _cache_message(self, cache_key: str, message: str):
        """Cache message in Redis"""
        try:
            redis_client.client.setex(
                cache_key,
                settings.INTERVENTION_MESSAGE_CACHE_TTL_SECONDS,
                message
            )
        except Exception as e:
            self.logger.warning(f"Cache storage failed: {e}")
    
    def _get_fallback_message(self, intervention_type: str) -> str:
        """Get fallback template message if LLM fails"""
        fallback_messages = {
            InterventionType.BREAK_SUGGESTION: 
                "You've been working hard! Consider taking a 5-minute break to recharge.",
            
            InterventionType.TOPIC_SWITCH: 
                "This topic seems challenging. Let's try a different approach or review the basics first.",
            
            InterventionType.RECAP_PROMPT: 
                "Let's review some key concepts before moving forward. Mastering the fundamentals will help you succeed.",
            
            InterventionType.ENCOURAGEMENT: 
                "You're making progress! Learning takes time and effort. Keep going, you're doing great!",
            
            InterventionType.DIFFICULTY_ADJUSTMENT: 
                "We're adjusting the pace to better match your learning style. This will help you build confidence.",
        }
        return fallback_messages.get(intervention_type, "Keep up the great work!")
