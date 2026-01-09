"""
Text Processing Utilities for Sentiment Analysis

Helper utilities for extracting and preprocessing text from various sources
for mood analysis.
"""

from typing import Dict, List, Optional
import json
import re


class TextProcessor:
    """Handles text extraction and preprocessing for sentiment analysis."""
    
    @staticmethod
    def extract_quiz_answer_text(quiz_result: Dict) -> str:
        """
        Extract text from quiz answer JSON structures.
        
        Args:
            quiz_result: Quiz result dictionary with answers field
            
        Returns:
            Concatenated text from all answers
        """
        answers = quiz_result.get('answers', [])
        
        if isinstance(answers, str):
            try:
                answers = json.loads(answers)
            except json.JSONDecodeError:
                return answers
        
        if not isinstance(answers, list):
            return str(answers)
        
        text_parts = []
        for answer in answers:
            if isinstance(answer, dict):
                # Extract text from various answer formats
                if 'text' in answer:
                    text_parts.append(str(answer['text']))
                elif 'answer' in answer:
                    text_parts.append(str(answer['answer']))
                elif 'response' in answer:
                    text_parts.append(str(answer['response']))
                elif 'value' in answer:
                    text_parts.append(str(answer['value']))
            elif isinstance(answer, str):
                text_parts.append(answer)
        
        return ' '.join(text_parts)
    
    @staticmethod
    def extract_search_query_text(navigation_event: Dict) -> str:
        """
        Extract search query text from navigation events.
        
        Args:
            navigation_event: Navigation event with metadata
            
        Returns:
            Search query text if present
        """
        metadata = navigation_event.get('metadata', {})
        
        # Check various possible locations for search query
        query = (metadata.get('searchQuery') or 
                metadata.get('query') or 
                metadata.get('search') or '')
        
        return str(query)
    
    @staticmethod
    def extract_typing_text(typing_event: Dict) -> str:
        """
        Extract typed text from typing pattern events.
        
        Args:
            typing_event: Typing pattern event with metadata
            
        Returns:
            Typed text if available
        """
        metadata = typing_event.get('metadata', {})
        
        text = (metadata.get('text') or 
               metadata.get('content') or 
               metadata.get('input') or '')
        
        return str(text)
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text for sentiment analysis.
        
        Args:
            text: Raw text string
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def is_code_snippet(text: str) -> bool:
        """
        Check if text appears to be a code snippet.
        
        Args:
            text: Text to check
            
        Returns:
            True if text looks like code
        """
        # Simple heuristics for code detection
        code_indicators = [
            'function', 'const', 'let', 'var', 'class',
            'def ', 'import ', 'from ', 'return ',
            '{', '}', '=>', '===', '!=='
        ]
        
        text_lower = text.lower()
        code_matches = sum(1 for indicator in code_indicators if indicator in text_lower)
        
        return code_matches >= 2
    
    @staticmethod
    def is_mathematical_notation(text: str) -> bool:
        """
        Check if text contains primarily mathematical notation.
        
        Args:
            text: Text to check
            
        Returns:
            True if text is mostly math notation
        """
        math_chars = sum(1 for char in text if char in '0123456789+-*/=()[]{}^')
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            return False
        
        return (math_chars / total_chars) > 0.5
    
    @staticmethod
    def extract_text_from_events(events: List[Dict]) -> List[str]:
        """
        Extract all text content from a list of behavioral events.
        
        Args:
            events: List of behavioral events
            
        Returns:
            List of extracted text strings
        """
        texts = []
        
        for event in events:
            event_type = event.get('type', '')
            
            if event_type == 'TYPING_PATTERN':
                text = TextProcessor.extract_typing_text(event)
                if text:
                    texts.append(text)
            
            elif event_type == 'NAVIGATION':
                text = TextProcessor.extract_search_query_text(event)
                if text:
                    texts.append(text)
            
            elif event_type == 'QUIZ_COMPLETE':
                metadata = event.get('metadata', {})
                if 'quizResult' in metadata:
                    text = TextProcessor.extract_quiz_answer_text(metadata['quizResult'])
                    if text:
                        texts.append(text)
        
        return texts
    
    @staticmethod
    def preprocess_for_sentiment(text: str) -> Optional[str]:
        """
        Preprocess text for sentiment analysis.
        Filters out code snippets and math notation.
        
        Args:
            text: Raw text
            
        Returns:
            Preprocessed text or None if not suitable for sentiment analysis
        """
        if not text or len(text.strip()) < 3:
            return None
        
        # Clean text
        cleaned = TextProcessor.clean_text(text)
        
        # Skip code snippets
        if TextProcessor.is_code_snippet(cleaned):
            return None
        
        # Skip pure mathematical notation
        if TextProcessor.is_mathematical_notation(cleaned):
            return None
        
        # Skip if too short after cleaning
        if len(cleaned) < 5:
            return None
        
        return cleaned
    
    @staticmethod
    def batch_preprocess(texts: List[str]) -> List[str]:
        """
        Preprocess multiple texts, filtering out unsuitable ones.
        
        Args:
            texts: List of raw text strings
            
        Returns:
            List of preprocessed texts (may be shorter than input)
        """
        processed = []
        
        for text in texts:
            preprocessed = TextProcessor.preprocess_for_sentiment(text)
            if preprocessed:
                processed.append(preprocessed)
        
        return processed
    
    @staticmethod
    def summarize_long_text(text: str, max_length: int = 500) -> str:
        """
        Truncate long text for efficient LLM processing.
        
        Args:
            text: Text to summarize
            max_length: Maximum character length
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        # Truncate and add ellipsis
        return text[:max_length - 3] + '...'
