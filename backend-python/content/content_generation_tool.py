"""LangChain tool for content generation in agent workflows."""

import logging
from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import Field
from content.generator import ContentGenerator
from content.difficulty_adapter import DifficultyAdapter

logger = logging.getLogger(__name__)


class ContentGenerationTool(BaseTool):
    """LangChain tool for generating educational content."""
    
    name: str = "generate_educational_content"
    description: str = """Generates personalized educational content (lessons, quizzes, exercises) based on topic, difficulty, and student cognitive profile. 
    
    Use this tool when:
    - Student needs customized learning materials
    - Difficulty needs to be adjusted with new content
    - Alternative explanations are needed
    - Review/recap materials are required
    
    Input should be a dictionary with:
    - topic (str): Content topic
    - content_type (str): lesson, quiz, exercise, or recap
    - difficulty (str): easy, medium, or hard
    - cognitive_load_score (float): Student's current cognitive load (0-100)
    - prerequisites (list, optional): List of prerequisite topics
    - estimated_minutes (int, optional): Target duration
    
    Returns dictionary with generated content and metadata."""
    
    content_generator: ContentGenerator = Field(default_factory=ContentGenerator)
    difficulty_adapter: DifficultyAdapter = Field(default_factory=DifficultyAdapter)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(
        self,
        topic: str,
        content_type: str,
        difficulty: str,
        cognitive_load_score: float,
        prerequisites: Optional[list] = None,
        estimated_minutes: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Synchronous execution (not supported for async content generation).
        Use async version instead.
        """
        raise NotImplementedError("Use async version (_arun) for content generation")
    
    async def _arun(
        self,
        topic: str,
        content_type: str,
        difficulty: str,
        cognitive_load_score: float,
        prerequisites: Optional[list] = None,
        estimated_minutes: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate educational content asynchronously.
        
        Args:
            topic: Content topic
            content_type: Type (lesson, quiz, exercise, recap)
            difficulty: Difficulty level
            cognitive_load_score: Current cognitive load
            prerequisites: Prerequisite topics
            estimated_minutes: Target duration
        
        Returns:
            Dictionary with content and metadata
        """
        try:
            logger.info(f"ContentGenerationTool called for topic: {topic}, type: {content_type}")
            
            # Build cognitive load profile
            cognitive_load_profile = {
                'current_score': cognitive_load_score,
                'fatigue_level': 'high' if cognitive_load_score > 70 else 'normal'
            }
            
            # Adapt difficulty based on cognitive load
            optimal_difficulty = self.difficulty_adapter.calculate_optimal_difficulty(
                cognitive_load_score=cognitive_load_score,
                current_difficulty=difficulty,
                performance_score=0.7  # Default, could be passed as parameter
            )
            
            if optimal_difficulty != difficulty:
                logger.info(f"Adjusted difficulty from {difficulty} to {optimal_difficulty}")
                difficulty = optimal_difficulty
            
            # Generate content based on type
            if content_type == 'lesson':
                content = await self.content_generator.generate_lesson(
                    topic=topic,
                    difficulty=difficulty,
                    prerequisites=prerequisites or [],
                    estimated_minutes=estimated_minutes or 15,
                    cognitive_load_profile=cognitive_load_profile
                )
            
            elif content_type == 'quiz':
                quiz_params = self.difficulty_adapter.adjust_quiz_complexity(
                    cognitive_load_score,
                    base_questions=5
                )
                content = await self.content_generator.generate_quiz(
                    topic=topic,
                    difficulty=difficulty,
                    num_questions=quiz_params['num_questions'],
                    cognitive_load_profile=cognitive_load_profile
                )
            
            elif content_type == 'exercise':
                content = await self.content_generator.generate_exercise(
                    topic=topic,
                    difficulty=difficulty,
                    exercise_type='problem-solving',
                    cognitive_load_profile=cognitive_load_profile
                )
            
            elif content_type == 'recap':
                content = await self.content_generator.generate_recap(
                    weak_topics=[topic],
                    recent_errors=[],
                    cognitive_load_profile=cognitive_load_profile
                )
            
            else:
                raise ValueError(f"Invalid content_type: {content_type}")
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(
                content=content,
                content_type=content_type,
                cognitive_load_score=cognitive_load_score
            )
            
            result = {
                'success': True,
                'content': content,
                'topic': topic,
                'content_type': content_type,
                'difficulty': difficulty,
                'adjusted_difficulty': optimal_difficulty != kwargs.get('original_difficulty', difficulty),
                'cognitive_load_score': cognitive_load_score,
                'confidence_score': confidence_score,
                'estimated_minutes': estimated_minutes or 15,
                'prerequisites': prerequisites or []
            }
            
            logger.info(f"Successfully generated {content_type} for {topic}")
            return result
        
        except Exception as e:
            logger.error(f"Error in ContentGenerationTool: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'topic': topic,
                'content_type': content_type
            }
    
    def _calculate_confidence(
        self,
        content: str,
        content_type: str,
        cognitive_load_score: float
    ) -> float:
        """
        Calculate confidence score for generated content.
        
        Returns score between 0 and 1.
        """
        confidence = 0.8  # Base confidence
        
        # Higher confidence for lower cognitive load (clearer state)
        if cognitive_load_score < 30:
            confidence += 0.1
        elif cognitive_load_score > 70:
            confidence -= 0.1
        
        # Higher confidence for longer content
        word_count = len(content.split())
        if content_type == 'lesson':
            if word_count > 200:
                confidence += 0.05
            elif word_count < 100:
                confidence -= 0.1
        
        # Ensure bounds
        return max(0.0, min(1.0, confidence))


def create_content_generation_tool() -> ContentGenerationTool:
    """Factory function to create content generation tool."""
    return ContentGenerationTool()
