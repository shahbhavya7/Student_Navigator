"""Metadata enrichment for generated content."""

import logging
import re
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Automatically extract and enrich content metadata."""
    
    def __init__(self):
        """Initialize metadata enricher."""
        logger.info("MetadataEnricher initialized")
    
    def enrich_metadata(
        self,
        content: str,
        content_type: str,
        existing_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extract and enrich metadata from content.
        
        Args:
            content: Content to analyze
            content_type: Type of content
            existing_metadata: Existing metadata to enrich
        
        Returns:
            Enriched metadata dictionary
        """
        metadata = existing_metadata or {}
        
        # Extract key concepts
        metadata['key_concepts'] = self.extract_key_concepts(content)
        
        # Identify prerequisites mentioned
        metadata['mentioned_prerequisites'] = self.identify_prerequisites(content)
        
        # Calculate reading time
        metadata['calculated_reading_time'] = self.calculate_reading_time(content)
        
        # Auto-detect content type if needed
        if not metadata.get('detected_type'):
            metadata['detected_type'] = self.detect_content_type(content)
        
        # Generate tags
        metadata['tags'] = self.generate_tags(content, content_type)
        
        # Generate summary
        metadata['summary'] = self.generate_content_summary(content)
        
        # Extract learning objectives
        metadata['learning_objectives'] = self.extract_learning_objectives(content)
        
        # Calculate complexity metrics
        metadata['complexity_metrics'] = self.calculate_complexity_metrics(content)
        
        logger.info("Metadata enrichment completed")
        return metadata
    
    def extract_key_concepts(self, content: str, max_concepts: int = 10) -> List[str]:
        """
        Extract key concepts from content using keyword extraction.
        
        Args:
            content: Content text
            max_concepts: Maximum concepts to extract
        
        Returns:
            List of key concepts
        """
        # Remove markdown formatting
        clean_text = re.sub(r'[#*`\[\]()]', '', content)
        
        # Split into words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', clean_text.lower())
        
        # Common stop words to exclude
        stop_words = {
            'this', 'that', 'with', 'from', 'have', 'will', 'would', 'could',
            'should', 'about', 'which', 'their', 'there', 'these', 'those',
            'when', 'where', 'while', 'what', 'more', 'into', 'than', 'been'
        }
        
        # Filter and count
        filtered_words = [w for w in words if w not in stop_words and len(w) > 4]
        word_counts = Counter(filtered_words)
        
        # Get most common
        key_concepts = [word for word, count in word_counts.most_common(max_concepts)]
        
        return key_concepts
    
    def identify_prerequisites(self, content: str) -> List[str]:
        """
        Identify prerequisite topics mentioned in content.
        
        Args:
            content: Content text
        
        Returns:
            List of identified prerequisites
        """
        prerequisites = []
        
        # Look for explicit prerequisite mentions
        prereq_patterns = [
            r'prerequisite[s]?:?\s+([^.\n]+)',
            r'requires? understanding of\s+([^.\n]+)',
            r'building on\s+([^.\n]+)',
            r'assumes? familiarity with\s+([^.\n]+)',
            r'before starting.*should know\s+([^.\n]+)'
        ]
        
        content_lower = content.lower()
        
        for pattern in prereq_patterns:
            matches = re.findall(pattern, content_lower)
            prerequisites.extend(matches)
        
        # Clean up and deduplicate
        prerequisites = [p.strip() for p in prerequisites]
        prerequisites = list(set([p for p in prerequisites if len(p) > 3]))
        
        return prerequisites[:5]  # Limit to 5 most relevant
    
    def calculate_reading_time(self, content: str) -> int:
        """
        Calculate estimated reading time in minutes.
        
        Args:
            content: Content text
        
        Returns:
            Estimated minutes to read
        """
        # Average reading speed: 175 words per minute
        READING_SPEED_WPM = 175
        
        word_count = len(content.split())
        minutes = max(1, round(word_count / READING_SPEED_WPM))
        
        return minutes
    
    def detect_content_type(self, content: str) -> str:
        """
        Auto-detect content type from structure.
        
        Args:
            content: Content text
        
        Returns:
            Detected type (lesson, quiz, exercise, recap)
        """
        content_lower = content.lower()
        
        # Check for quiz indicators
        if 'correct_answer' in content_lower or '"options"' in content_lower:
            return 'quiz'
        
        # Check for exercise indicators
        if any(marker in content_lower for marker in ['problem statement', 'solution', 'exercise', 'practice']):
            return 'exercise'
        
        # Check for recap indicators
        if any(marker in content_lower for marker in ['review', 'recap', 'summary of']):
            return 'recap'
        
        # Default to lesson
        return 'lesson'
    
    def generate_tags(
        self,
        content: str,
        content_type: str,
        max_tags: int = 5
    ) -> List[str]:
        """
        Generate searchable tags for content.
        
        Args:
            content: Content text
            content_type: Content type
            max_tags: Maximum tags to generate
        
        Returns:
            List of tags
        """
        tags = [content_type]
        
        # Extract key concepts as tags
        key_concepts = self.extract_key_concepts(content, max_tags - 1)
        tags.extend(key_concepts[:max_tags - 1])
        
        # Add difficulty indicators
        content_lower = content.lower()
        if any(word in content_lower for word in ['advanced', 'complex', 'challenging']):
            if 'advanced' not in tags:
                tags.append('advanced')
        elif any(word in content_lower for word in ['basic', 'introduction', 'fundamentals']):
            if 'beginner' not in tags:
                tags.append('beginner')
        
        return tags[:max_tags]
    
    def generate_content_summary(self, content: str, max_sentences: int = 3) -> str:
        """
        Generate a brief summary of content.
        
        Args:
            content: Content text
            max_sentences: Maximum sentences in summary
        
        Returns:
            Content summary
        """
        # Extract first few sentences (simple approach)
        sentences = re.split(r'[.!?]+', content)
        
        # Filter out markdown headers and very short sentences
        valid_sentences = []
        for sentence in sentences:
            clean = sentence.strip()
            if len(clean) > 20 and not clean.startswith('#'):
                valid_sentences.append(clean)
            if len(valid_sentences) >= max_sentences:
                break
        
        summary = '. '.join(valid_sentences[:max_sentences])
        
        if not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    def extract_learning_objectives(self, content: str) -> List[str]:
        """
        Extract learning objectives from content.
        
        Args:
            content: Content text
        
        Returns:
            List of learning objectives
        """
        objectives = []
        
        # Look for explicit learning objectives section
        obj_patterns = [
            r'learning objectives?:?\s*\n+((?:[-*]\s*.+\n?)+)',
            r'you will learn:?\s*\n+((?:[-*]\s*.+\n?)+)',
            r'by the end.*you will:?\s*\n+((?:[-*]\s*.+\n?)+)'
        ]
        
        for pattern in obj_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                # Extract bullet points
                bullets = re.findall(r'[-*]\s*(.+)', matches[0])
                objectives.extend([b.strip() for b in bullets])
        
        # If no explicit objectives, infer from headings
        if not objectives:
            headings = re.findall(r'##\s+(.+)', content)
            objectives = [f"Understand {h.lower()}" for h in headings[:3]]
        
        return objectives[:5]  # Limit to 5 objectives
    
    def calculate_complexity_metrics(self, content: str) -> Dict[str, Any]:
        """
        Calculate various complexity metrics for content.
        
        Args:
            content: Content text
        
        Returns:
            Dictionary of complexity metrics
        """
        # Clean text
        clean_text = re.sub(r'[#*`\[\]()]', '', content)
        
        words = clean_text.split()
        word_count = len(words)
        
        if word_count == 0:
            return {
                'word_count': 0,
                'avg_word_length': 0,
                'unique_word_ratio': 0,
                'complexity_score': 0
            }
        
        # Average word length
        avg_word_length = sum(len(w) for w in words) / word_count
        
        # Unique word ratio (vocabulary diversity)
        unique_words = len(set(w.lower() for w in words))
        unique_ratio = unique_words / word_count
        
        # Sentence count
        sentences = re.split(r'[.!?]+', clean_text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Simple complexity score (0-100)
        # Based on word length, sentence length, vocabulary diversity
        complexity_score = min(100, (
            (avg_word_length - 4) * 10 +  # Word length factor
            (avg_sentence_length - 10) * 2 +  # Sentence length factor
            (1 - unique_ratio) * 50  # Vocabulary diversity (inverse)
        ))
        
        return {
            'word_count': word_count,
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(avg_sentence_length, 2),
            'unique_word_ratio': round(unique_ratio, 3),
            'complexity_score': round(max(0, complexity_score), 2)
        }
