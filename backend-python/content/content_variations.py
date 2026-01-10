"""Content variation system for generating alternative explanations."""

import logging
from enum import Enum
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from content.prompt_templates import (
    EASIER_VERSION_PROMPT,
    HARDER_VERSION_PROMPT,
    ALTERNATIVE_EXPLANATION_PROMPT
)

logger = logging.getLogger(__name__)


class VariationStrategy(Enum):
    """Strategies for varying content."""
    SIMPLIFY = "simplify"
    COMPLEXIFY = "complexify"
    REPHRASE = "rephrase"
    ADD_EXAMPLES = "add_examples"
    CHANGE_APPROACH = "change_approach"


class ContentVariationGenerator:
    """Generate variations of educational content."""
    
    def __init__(self):
        """Initialize variation generator with LLM."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.8,  # Higher temperature for more variation
            max_tokens=2048
        )
        logger.info("ContentVariationGenerator initialized")
    
    async def generate_easier_version(
        self,
        original_content: str,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate a simpler version of content.
        
        Args:
            original_content: Original content to simplify
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Simplified content
        """
        try:
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_context(
                cognitive_load_score,
                cognitive_load_profile
            )
            
            messages = EASIER_VERSION_PROMPT.format_messages(
                original_content=original_content,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            logger.info("Successfully generated easier version of content")
            return content
            
        except Exception as e:
            logger.error(f"Error generating easier version: {str(e)}")
            return self._apply_simple_simplification(original_content)
    
    async def generate_harder_version(
        self,
        original_content: str,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate a more challenging version of content.
        
        Args:
            original_content: Original content to enhance
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Enhanced content with increased difficulty
        """
        try:
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_context(
                cognitive_load_score,
                cognitive_load_profile
            )
            
            messages = HARDER_VERSION_PROMPT.format_messages(
                original_content=original_content,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            logger.info("Successfully generated harder version of content")
            return content
            
        except Exception as e:
            logger.error(f"Error generating harder version: {str(e)}")
            return original_content + "\n\n## Advanced Challenge\nApply these concepts to more complex scenarios."
    
    async def generate_alternative_explanation(
        self,
        original_content: str,
        strategy: VariationStrategy,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Generate alternative explanation using different approach.
        
        Args:
            original_content: Original content
            strategy: Variation strategy to apply
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Alternative explanation
        """
        try:
            cognitive_load_score = cognitive_load_profile.get('current_score', 50)
            cognitive_load_context = self._build_cognitive_context(
                cognitive_load_score,
                cognitive_load_profile
            )
            
            messages = ALTERNATIVE_EXPLANATION_PROMPT.format_messages(
                original_content=original_content,
                variation_strategy=strategy.value,
                cognitive_load_context=cognitive_load_context
            )
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            logger.info(f"Successfully generated alternative explanation using {strategy.value}")
            return content
            
        except Exception as e:
            logger.error(f"Error generating alternative explanation: {str(e)}")
            return original_content
    
    async def apply_variation_strategy(
        self,
        base_content: str,
        strategy: VariationStrategy,
        cognitive_load_profile: Dict[str, Any]
    ) -> str:
        """
        Apply a specific variation strategy to content.
        
        Args:
            base_content: Base content to modify
            strategy: Variation strategy
            cognitive_load_profile: Student's cognitive load data
        
        Returns:
            Modified content
        """
        if strategy == VariationStrategy.SIMPLIFY:
            return await self.generate_easier_version(base_content, cognitive_load_profile)
        elif strategy == VariationStrategy.COMPLEXIFY:
            return await self.generate_harder_version(base_content, cognitive_load_profile)
        else:
            return await self.generate_alternative_explanation(
                base_content,
                strategy,
                cognitive_load_profile
            )
    
    def calculate_content_diff(
        self,
        original_content: str,
        modified_content: str
    ) -> Dict[str, Any]:
        """
        Track differences between content versions.
        
        Args:
            original_content: Original content
            modified_content: Modified content
        
        Returns:
            Dictionary with diff statistics
        """
        original_words = original_content.split()
        modified_words = modified_content.split()
        
        length_change = len(modified_words) - len(original_words)
        length_change_pct = (length_change / len(original_words) * 100) if original_words else 0
        
        return {
            'original_word_count': len(original_words),
            'modified_word_count': len(modified_words),
            'length_change': length_change,
            'length_change_percent': round(length_change_pct, 2),
            'original_char_count': len(original_content),
            'modified_char_count': len(modified_content)
        }
    
    def _build_cognitive_context(
        self,
        cognitive_load_score: float,
        profile: Dict[str, Any]
    ) -> str:
        """Build context string for cognitive load."""
        if cognitive_load_score > 70:
            return f"HIGH cognitive load (score: {cognitive_load_score}). Student needs maximum support and simplification."
        elif cognitive_load_score > 30:
            return f"MEDIUM cognitive load (score: {cognitive_load_score}). Standard teaching approach appropriate."
        else:
            return f"LOW cognitive load (score: {cognitive_load_score}). Student can handle advanced material."
    
    def _apply_simple_simplification(self, content: str) -> str:
        """Apply basic simplification as fallback."""
        # Simple fallback: add a note about reviewing fundamentals
        return content + "\n\n## Review\nLet's break this down step by step. Take your time to understand each concept before moving forward."
