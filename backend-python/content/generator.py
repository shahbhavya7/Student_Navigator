"""Core content generator using LangChain and Google Gemini."""

import logging
import json
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from content.prompt_templates import (
    get_prompt_template,
    LESSON_PROMPT,
    QUIZ_PROMPT,
    EXERCISE_PROMPT,
    RECAP_PROMPT
)
from config.settings import settings

logger = logging.getLogger(__name__)


# Fallback templates for when LLM generation fails
FALLBACK_LESSON = """# {topic}

## Introduction
This lesson covers the fundamentals of {topic}. You'll learn the key concepts and practical applications.

## Main Content
{topic} is an important concept that requires understanding of prerequisite topics: {prerequisites}.

### Key Concepts
- Fundamental principles
- Practical applications
- Common patterns

## Practice Questions
1. What are the main principles of {topic}?
2. How would you apply {topic} in a real-world scenario?

## Summary
- Understand core concepts
- Apply knowledge practically
- Connect to related topics

## Next Steps
Continue practicing and explore advanced topics related to {topic}.
"""

FALLBACK_QUIZ = [
    {
        "question": "What is the main concept of {topic}?",
        "options": {
            "A": "First option",
            "B": "Second option",
            "C": "Third option",
            "D": "Fourth option"
        },
        "correct_answer": "A",
        "explanation": "This is the fundamental definition of {topic}."
    }
]

FALLBACK_EXERCISE = """# Practice Exercise: {topic}

## Problem Statement
Apply your understanding of {topic} to solve the following problem.

## Hints
1. Review the key concepts
2. Break the problem into smaller steps
3. Consider how the prerequisites apply

## Solution
Step-by-step solution will guide you through the problem.

## Extension Challenges
Try solving a more complex variation of this problem.
"""


class ContentGenerator:
    """Generate educational content using LangChain and Google Gemini."""
    
    def __init__(self):
        """Initialize content generator with LLM."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=2048
        )
        logger.info("ContentGenerator initialized with Gemini 2.0 Flash")
    
    async def generate_lesson(
        self,
        topic: str,
        difficulty: str,
        prerequisites: List[str],
        estimated_minutes: int,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate a lesson using LLM.
        
        Args:
            topic: Lesson topic
            difficulty: Difficulty level (easy, medium, hard)
            prerequisites: List of prerequisite topics
            estimated_minutes: Target duration in minutes
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Generated lesson content as markdown
        """
        try:
            # Extract cognitive load context
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_load_context(
                cognitive_load_score, 
                cognitive_load_profile
            )
            
            # Format prerequisites
            prereq_str = ", ".join(prerequisites) if prerequisites else "None"
            
            # Generate using LLM
            messages = LESSON_PROMPT.format_messages(
                topic=topic,
                difficulty=difficulty,
                estimated_minutes=estimated_minutes,
                prerequisites=prereq_str,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Validate generated content
            if len(content.strip()) < 100:
                logger.warning(f"Generated lesson too short for {topic}, using fallback")
                return self._get_fallback_lesson(topic, prerequisites)
            
            logger.info(f"Successfully generated lesson for topic: {topic}")
            return content
            
        except Exception as e:
            logger.error(f"Error generating lesson for {topic}: {str(e)}")
            return self._get_fallback_lesson(topic, prerequisites)
    
    async def generate_quiz(
        self,
        topic: str,
        difficulty: str,
        num_questions: int,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate a quiz using LLM.
        
        Args:
            topic: Quiz topic
            difficulty: Difficulty level
            num_questions: Number of questions to generate
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Generated quiz as JSON string
        """
        try:
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_load_context(
                cognitive_load_score,
                cognitive_load_profile
            )
            
            messages = QUIZ_PROMPT.format_messages(
                topic=topic,
                difficulty=difficulty,
                num_questions=num_questions,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Extract JSON from response (may be wrapped in markdown code blocks)
            quiz_data = self._extract_json_from_response(content)
            
            # Validate quiz structure
            if not self._validate_quiz_structure(quiz_data):
                logger.warning(f"Invalid quiz structure for {topic}, using fallback")
                return json.dumps(self._get_fallback_quiz(topic))
            
            logger.info(f"Successfully generated quiz for topic: {topic}")
            return json.dumps(quiz_data)
            
        except Exception as e:
            logger.error(f"Error generating quiz for {topic}: {str(e)}")
            return json.dumps(self._get_fallback_quiz(topic))
    
    async def generate_exercise(
        self,
        topic: str,
        difficulty: str,
        exercise_type: str,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate a practice exercise using LLM.
        
        Args:
            topic: Exercise topic
            difficulty: Difficulty level
            exercise_type: Type (problem-solving, application, analysis)
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Generated exercise as markdown
        """
        try:
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_load_context(
                cognitive_load_score,
                cognitive_load_profile
            )
            
            messages = EXERCISE_PROMPT.format_messages(
                topic=topic,
                difficulty=difficulty,
                exercise_type=exercise_type,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            if len(content.strip()) < 100:
                logger.warning(f"Generated exercise too short for {topic}, using fallback")
                return self._get_fallback_exercise(topic)
            
            logger.info(f"Successfully generated exercise for topic: {topic}")
            return content
            
        except Exception as e:
            logger.error(f"Error generating exercise for {topic}: {str(e)}")
            return self._get_fallback_exercise(topic)
    
    async def generate_recap(
        self,
        weak_topics: List[str],
        recent_errors: List[str],
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate review/recap content for struggling students.
        
        Args:
            weak_topics: Topics student is struggling with
            recent_errors: Recent mistakes or misconceptions
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Generated recap content as markdown
        """
        try:
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_load_context(
                cognitive_load_score,
                cognitive_load_profile
            )
            
            weak_topics_str = ", ".join(weak_topics) if weak_topics else "Core concepts"
            recent_errors_str = "; ".join(recent_errors) if recent_errors else "General review needed"
            
            messages = RECAP_PROMPT.format_messages(
                weak_topics=weak_topics_str,
                recent_errors=recent_errors_str,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            logger.info(f"Successfully generated recap for topics: {weak_topics_str}")
            return content
            
        except Exception as e:
            logger.error(f"Error generating recap: {str(e)}")
            return f"# Review: {', '.join(weak_topics)}\n\nReview the key concepts and practice problems."
    
    def _build_cognitive_load_context(
        self,
        cognitive_load_score: float,
        profile: Dict[str, Any]
    ) -> str:
        """Build context string describing cognitive load state."""
        if cognitive_load_score > 70:
            load_level = "HIGH"
            description = "Student is experiencing high cognitive load. Simplify content, add scaffolding, and reduce information density."
        elif cognitive_load_score > 30:
            load_level = "MEDIUM"
            description = "Student has moderate cognitive load. Use standard teaching approach with balanced complexity."
        else:
            load_level = "LOW"
            description = "Student has low cognitive load. Can handle more complex material and advanced concepts."
        
        fatigue = profile.get('fatigue_level', 'normal')
        return f"{load_level} cognitive load (score: {cognitive_load_score}). Fatigue level: {fatigue}. {description}"
    
    def _extract_json_from_response(self, content: str) -> List[Dict[str, Any]]:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        return json.loads(content)
    
    def _validate_quiz_structure(self, quiz_data: List[Dict[str, Any]]) -> bool:
        """Validate quiz has correct structure."""
        if not isinstance(quiz_data, list) or len(quiz_data) == 0:
            return False
        
        for question in quiz_data:
            if not all(key in question for key in ['question', 'options', 'correct_answer', 'explanation']):
                return False
            if not isinstance(question['options'], dict) or len(question['options']) != 4:
                return False
        
        return True
    
    def _get_fallback_lesson(self, topic: str, prerequisites: List[str]) -> str:
        """Return fallback lesson template."""
        prereq_str = ", ".join(prerequisites) if prerequisites else "foundational knowledge"
        return FALLBACK_LESSON.format(topic=topic, prerequisites=prereq_str)
    
    def _get_fallback_quiz(self, topic: str) -> List[Dict[str, Any]]:
        """Return fallback quiz template."""
        return [q for q in FALLBACK_QUIZ]
    
    def _get_fallback_exercise(self, topic: str) -> str:
        """Return fallback exercise template."""
        return FALLBACK_EXERCISE.format(topic=topic)
