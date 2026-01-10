"""Difficulty adapter for cognitive load-aware content generation."""

import logging
from typing import Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class CognitiveLoadLevel(Enum):
    """Cognitive load level categories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DifficultyAdapter:
    """Adjust content generation based on cognitive load."""
    
    # Cognitive load thresholds
    HIGH_THRESHOLD = 70
    MEDIUM_THRESHOLD = 30
    
    def __init__(self):
        """Initialize difficulty adapter."""
        logger.info("DifficultyAdapter initialized")
    
    def adapt_generation_params(
        self,
        base_params: Dict[str, Any],
        cognitive_load_score: float
    ) -> Dict[str, Any]:
        """
        Adapt generation parameters based on cognitive load.
        
        Args:
            base_params: Base generation parameters
            cognitive_load_score: Current cognitive load score (0-100)
        
        Returns:
            Adapted parameters
        """
        load_level = self._classify_cognitive_load(cognitive_load_score)
        adapted_params = base_params.copy()
        
        if load_level == CognitiveLoadLevel.HIGH:
            # High cognitive load: simplify and provide more support
            adapted_params['content_length_multiplier'] = 0.7  # Reduce by 30%
            adapted_params['vocabulary_complexity'] = 'simple'
            adapted_params['examples_multiplier'] = 1.5  # 50% more examples
            adapted_params['estimated_minutes_multiplier'] = 1.5  # 50% more time
            adapted_params['scaffolding_level'] = 'high'
            adapted_params['chunk_size'] = 'small'
            
        elif load_level == CognitiveLoadLevel.MEDIUM:
            # Medium cognitive load: standard parameters
            adapted_params['content_length_multiplier'] = 1.0
            adapted_params['vocabulary_complexity'] = 'moderate'
            adapted_params['examples_multiplier'] = 1.0
            adapted_params['estimated_minutes_multiplier'] = 1.0
            adapted_params['scaffolding_level'] = 'moderate'
            adapted_params['chunk_size'] = 'medium'
            
        else:  # LOW
            # Low cognitive load: increase depth and complexity
            adapted_params['content_length_multiplier'] = 1.2  # 20% more content
            adapted_params['vocabulary_complexity'] = 'advanced'
            adapted_params['examples_multiplier'] = 0.8  # Fewer examples, more independent work
            adapted_params['estimated_minutes_multiplier'] = 0.9  # Slightly less time needed
            adapted_params['scaffolding_level'] = 'low'
            adapted_params['chunk_size'] = 'large'
        
        adapted_params['cognitive_load_level'] = load_level.value
        adapted_params['cognitive_load_score'] = cognitive_load_score
        
        logger.info(f"Adapted params for {load_level.value} cognitive load (score: {cognitive_load_score})")
        return adapted_params
    
    def calculate_optimal_difficulty(
        self,
        cognitive_load_score: float,
        current_difficulty: str,
        performance_score: float = 0.7
    ) -> str:
        """
        Calculate optimal content difficulty based on cognitive load and performance.
        
        Args:
            cognitive_load_score: Current cognitive load (0-100)
            current_difficulty: Current difficulty level
            performance_score: Recent performance score (0-1)
        
        Returns:
            Recommended difficulty level (easy, medium, hard)
        """
        load_level = self._classify_cognitive_load(cognitive_load_score)
        
        # High cognitive load: recommend easier content
        if load_level == CognitiveLoadLevel.HIGH:
            if current_difficulty == 'hard':
                return 'medium'
            elif current_difficulty == 'medium' and performance_score < 0.6:
                return 'easy'
            return current_difficulty
        
        # Low cognitive load and good performance: recommend harder content
        elif load_level == CognitiveLoadLevel.LOW and performance_score > 0.8:
            if current_difficulty == 'easy':
                return 'medium'
            elif current_difficulty == 'medium':
                return 'hard'
            return current_difficulty
        
        # Medium load or mixed performance: maintain current difficulty
        return current_difficulty
    
    def adjust_quiz_complexity(
        self,
        cognitive_load_score: float,
        base_questions: int = 5
    ) -> Dict[str, Any]:
        """
        Adjust quiz parameters based on cognitive load.
        
        Args:
            cognitive_load_score: Current cognitive load
            base_questions: Base number of questions
        
        Returns:
            Adjusted quiz parameters
        """
        load_level = self._classify_cognitive_load(cognitive_load_score)
        
        if load_level == CognitiveLoadLevel.HIGH:
            return {
                'num_questions': max(3, base_questions - 2),  # Fewer questions
                'time_limit_multiplier': 1.5,  # 50% more time
                'question_types': ['multiple_choice'],  # Simpler question types
                'hint_availability': 'always',
                'partial_credit': True
            }
        
        elif load_level == CognitiveLoadLevel.LOW:
            return {
                'num_questions': base_questions + 2,  # More questions
                'time_limit_multiplier': 0.8,  # Less time
                'question_types': ['multiple_choice', 'short_answer', 'problem_solving'],
                'hint_availability': 'limited',
                'partial_credit': False
            }
        
        else:  # MEDIUM
            return {
                'num_questions': base_questions,
                'time_limit_multiplier': 1.0,
                'question_types': ['multiple_choice', 'short_answer'],
                'hint_availability': 'on_request',
                'partial_credit': True
            }
    
    def get_pacing_recommendations(
        self,
        cognitive_load_score: float,
        session_duration_minutes: int
    ) -> Dict[str, Any]:
        """
        Get content pacing and break recommendations.
        
        Args:
            cognitive_load_score: Current cognitive load
            session_duration_minutes: Current session duration
        
        Returns:
            Pacing recommendations
        """
        load_level = self._classify_cognitive_load(cognitive_load_score)
        
        if load_level == CognitiveLoadLevel.HIGH:
            return {
                'chunk_duration_minutes': 10,  # Shorter chunks
                'break_frequency_minutes': 15,  # More frequent breaks
                'break_duration_minutes': 5,
                'max_session_duration': 45,
                'recommend_break_now': session_duration_minutes >= 15
            }
        
        elif load_level == CognitiveLoadLevel.LOW:
            return {
                'chunk_duration_minutes': 30,  # Longer chunks
                'break_frequency_minutes': 60,  # Less frequent breaks
                'break_duration_minutes': 5,
                'max_session_duration': 90,
                'recommend_break_now': session_duration_minutes >= 60
            }
        
        else:  # MEDIUM
            return {
                'chunk_duration_minutes': 20,
                'break_frequency_minutes': 30,
                'break_duration_minutes': 5,
                'max_session_duration': 60,
                'recommend_break_now': session_duration_minutes >= 30
            }
    
    def adjust_content_length(
        self,
        base_word_count: int,
        cognitive_load_score: float
    ) -> int:
        """
        Calculate adjusted content length based on cognitive load.
        
        Args:
            base_word_count: Base target word count
            cognitive_load_score: Current cognitive load
        
        Returns:
            Adjusted word count
        """
        load_level = self._classify_cognitive_load(cognitive_load_score)
        
        if load_level == CognitiveLoadLevel.HIGH:
            return int(base_word_count * 0.7)  # 30% reduction
        elif load_level == CognitiveLoadLevel.LOW:
            return int(base_word_count * 1.2)  # 20% increase
        else:
            return base_word_count
    
    def get_vocabulary_guidance(
        self,
        cognitive_load_score: float
    ) -> Dict[str, Any]:
        """
        Get vocabulary complexity guidance for content generation.
        
        Args:
            cognitive_load_score: Current cognitive load
        
        Returns:
            Vocabulary guidance
        """
        load_level = self._classify_cognitive_load(cognitive_load_score)
        
        if load_level == CognitiveLoadLevel.HIGH:
            return {
                'complexity_level': 'simple',
                'sentence_length': 'short',
                'technical_terms': 'minimal',
                'jargon_usage': 'avoid',
                'explanation_style': 'explicit and detailed'
            }
        
        elif load_level == CognitiveLoadLevel.LOW:
            return {
                'complexity_level': 'advanced',
                'sentence_length': 'varied',
                'technical_terms': 'encouraged',
                'jargon_usage': 'appropriate',
                'explanation_style': 'concise with implicit connections'
            }
        
        else:  # MEDIUM
            return {
                'complexity_level': 'moderate',
                'sentence_length': 'medium',
                'technical_terms': 'moderate',
                'jargon_usage': 'with_definitions',
                'explanation_style': 'balanced'
            }
    
    def _classify_cognitive_load(self, score: float) -> CognitiveLoadLevel:
        """Classify cognitive load score into level."""
        if score > self.HIGH_THRESHOLD:
            return CognitiveLoadLevel.HIGH
        elif score > self.MEDIUM_THRESHOLD:
            return CognitiveLoadLevel.MEDIUM
        else:
            return CognitiveLoadLevel.LOW
