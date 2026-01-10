"""Content quality validator for generated educational content."""

import logging
import re
import json
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of content validation."""
    
    def __init__(self, passed: bool, issues: List[str] = None):
        self.passed = passed
        self.issues = issues or []
    
    def __bool__(self):
        return self.passed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'issues': self.issues
        }


class ContentValidator:
    """Validate quality of generated educational content."""
    
    # Words per minute reading speed estimate
    READING_SPEED_WPM = 175
    
    # Minimum content lengths
    MIN_LESSON_WORDS = 100
    MIN_QUIZ_QUESTIONS = 3
    MIN_EXERCISE_WORDS = 50
    
    def __init__(self):
        """Initialize content validator."""
        logger.info("ContentValidator initialized")
    
    def validate_content(
        self,
        content: str,
        content_type: str,
        expected_difficulty: str,
        estimated_minutes: int,
        prerequisites: List[str] = None
    ) -> ValidationResult:
        """
        Validate generated content quality.
        
        Args:
            content: Content to validate
            content_type: Type (lesson, quiz, exercise, recap)
            expected_difficulty: Expected difficulty level
            estimated_minutes: Expected duration
            prerequisites: Expected prerequisite topics
        
        Returns:
            ValidationResult with pass/fail and issues
        """
        issues = []
        
        if content_type == 'lesson':
            lesson_issues = self._validate_lesson(content, estimated_minutes, prerequisites)
            issues.extend(lesson_issues)
        
        elif content_type == 'quiz':
            quiz_issues = self._validate_quiz(content)
            issues.extend(quiz_issues)
        
        elif content_type == 'exercise':
            exercise_issues = self._validate_exercise(content)
            issues.extend(exercise_issues)
        
        # Common validations
        length_issues = self._validate_length(content, content_type, estimated_minutes)
        issues.extend(length_issues)
        
        # Difficulty consistency
        if expected_difficulty:
            difficulty_issues = self._validate_difficulty_consistency(content, expected_difficulty)
            issues.extend(difficulty_issues)
        
        passed = len(issues) == 0
        
        if passed:
            logger.info(f"Content validation PASSED for {content_type}")
        else:
            logger.warning(f"Content validation FAILED for {content_type}: {len(issues)} issues found")
        
        return ValidationResult(passed=passed, issues=issues)
    
    def _validate_lesson(
        self,
        content: str,
        estimated_minutes: int,
        prerequisites: List[str]
    ) -> List[str]:
        """Validate lesson structure."""
        issues = []
        
        # Check for required sections
        required_sections = ['introduction', 'main', 'summary']
        content_lower = content.lower()
        
        has_intro = any(marker in content_lower for marker in ['introduction', '## intro', 'learning objectives'])
        has_main = len(content) > 200  # Reasonable main content
        has_summary = any(marker in content_lower for marker in ['summary', 'key takeaways', 'conclusion'])
        
        if not has_intro:
            issues.append("Lesson missing introduction or learning objectives")
        
        if not has_main:
            issues.append("Lesson main content too short or missing")
        
        if not has_summary:
            issues.append("Lesson missing summary or key takeaways")
        
        # Check for examples
        example_markers = ['example', 'for instance', 'such as', 'consider']
        has_examples = any(marker in content_lower for marker in example_markers)
        
        if not has_examples:
            issues.append("Lesson should include concrete examples")
        
        # Check prerequisite coverage
        if prerequisites:
            for prereq in prerequisites:
                if prereq.lower() not in content_lower:
                    issues.append(f"Lesson doesn't reference prerequisite: {prereq}")
        
        return issues
    
    def _validate_quiz(self, content: str) -> List[str]:
        """Validate quiz structure."""
        issues = []
        
        try:
            # Parse quiz JSON
            quiz_data = json.loads(content)
            
            if not isinstance(quiz_data, list):
                issues.append("Quiz must be a JSON array of questions")
                return issues
            
            if len(quiz_data) < self.MIN_QUIZ_QUESTIONS:
                issues.append(f"Quiz must have at least {self.MIN_QUIZ_QUESTIONS} questions")
            
            for i, question in enumerate(quiz_data, 1):
                # Check required fields
                required_fields = ['question', 'options', 'correct_answer', 'explanation']
                missing_fields = [f for f in required_fields if f not in question]
                
                if missing_fields:
                    issues.append(f"Question {i} missing fields: {', '.join(missing_fields)}")
                    continue
                
                # Validate options
                if not isinstance(question.get('options'), dict):
                    issues.append(f"Question {i} options must be a dictionary")
                elif len(question['options']) != 4:
                    issues.append(f"Question {i} must have exactly 4 options")
                
                # Validate correct answer
                correct = question.get('correct_answer')
                if correct not in question.get('options', {}):
                    issues.append(f"Question {i} correct_answer '{correct}' not in options")
                
                # Check for explanation
                if not question.get('explanation') or len(question['explanation']) < 10:
                    issues.append(f"Question {i} needs a proper explanation")
        
        except json.JSONDecodeError:
            issues.append("Quiz content is not valid JSON")
        
        return issues
    
    def _validate_exercise(self, content: str) -> List[str]:
        """Validate exercise structure."""
        issues = []
        
        content_lower = content.lower()
        
        # Check for problem statement
        has_problem = any(marker in content_lower for marker in ['problem', 'exercise', 'task', 'challenge'])
        if not has_problem:
            issues.append("Exercise missing clear problem statement")
        
        # Check for hints
        has_hints = 'hint' in content_lower
        if not has_hints:
            issues.append("Exercise should include hints to support students")
        
        # Check for solution
        has_solution = any(marker in content_lower for marker in ['solution', 'answer', 'explanation'])
        if not has_solution:
            issues.append("Exercise missing solution or explanation")
        
        return issues
    
    def _validate_length(
        self,
        content: str,
        content_type: str,
        estimated_minutes: int
    ) -> List[str]:
        """Validate content length matches estimated time."""
        issues = []
        
        word_count = len(content.split())
        
        # Check minimum length
        if content_type == 'lesson' and word_count < self.MIN_LESSON_WORDS:
            issues.append(f"Lesson too short: {word_count} words (minimum {self.MIN_LESSON_WORDS})")
        
        elif content_type == 'exercise' and word_count < self.MIN_EXERCISE_WORDS:
            issues.append(f"Exercise too short: {word_count} words (minimum {self.MIN_EXERCISE_WORDS})")
        
        # Check if length roughly matches estimated time
        if content_type in ['lesson', 'exercise']:
            expected_words = estimated_minutes * self.READING_SPEED_WPM
            ratio = word_count / expected_words if expected_words > 0 else 0
            
            # Allow 50% variance
            if ratio < 0.5:
                issues.append(f"Content too short for estimated time: {word_count} words for {estimated_minutes} min")
            elif ratio > 1.5:
                issues.append(f"Content too long for estimated time: {word_count} words for {estimated_minutes} min")
        
        return issues
    
    def _validate_difficulty_consistency(
        self,
        content: str,
        expected_difficulty: str
    ) -> List[str]:
        """Validate content difficulty matches expectations."""
        issues = []
        
        readability_score = self.calculate_readability_score(content)
        
        # Map readability to expected difficulty
        if expected_difficulty == 'easy' and readability_score > 70:
            issues.append(f"Content may be too complex for 'easy' difficulty (readability: {readability_score})")
        
        elif expected_difficulty == 'hard' and readability_score < 40:
            issues.append(f"Content may be too simple for 'hard' difficulty (readability: {readability_score})")
        
        return issues
    
    def calculate_readability_score(self, content: str) -> float:
        """
        Calculate readability score (0-100, higher = easier).
        
        Simplified Flesch Reading Ease approximation.
        
        Args:
            content: Text content
        
        Returns:
            Readability score
        """
        # Remove markdown formatting
        clean_text = re.sub(r'[#*`\[\]]', '', content)
        
        # Count sentences (approximate)
        sentences = re.split(r'[.!?]+', clean_text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        if sentence_count == 0:
            return 50.0  # Default neutral score
        
        # Count words
        words = clean_text.split()
        word_count = len(words)
        
        if word_count == 0:
            return 50.0
        
        # Count syllables (very rough approximation)
        syllable_count = sum(self._count_syllables(word) for word in words)
        
        # Flesch Reading Ease formula (simplified)
        avg_sentence_length = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count
        
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        # Clamp to 0-100
        return max(0, min(100, score))
    
    def _count_syllables(self, word: str) -> int:
        """Rough syllable count for readability."""
        word = word.lower().strip()
        vowels = 'aeiouy'
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith('e'):
            syllable_count -= 1
        
        # Minimum one syllable
        return max(1, syllable_count)
    
    def check_prerequisite_coverage(
        self,
        content: str,
        prerequisites: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if content covers prerequisite topics.
        
        Args:
            content: Content to check
            prerequisites: Expected prerequisites
        
        Returns:
            Tuple of (all_covered, missing_prerequisites)
        """
        content_lower = content.lower()
        missing = []
        
        for prereq in prerequisites:
            if prereq.lower() not in content_lower:
                missing.append(prereq)
        
        return (len(missing) == 0, missing)
