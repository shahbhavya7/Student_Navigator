"""Comprehensive tests for content generation system."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from content.generator import ContentGenerator
from content.content_variations import ContentVariationGenerator, VariationStrategy
from content.content_cache import ContentCacheManager
from content.content_storage import ContentStorageService
from content.difficulty_adapter import DifficultyAdapter
from content.content_validator import ContentValidator
from content.metadata_enricher import MetadataEnricher


@pytest.fixture
def content_generator():
    """Fixture for content generator."""
    return ContentGenerator()


@pytest.fixture
def variation_generator():
    """Fixture for variation generator."""
    return ContentVariationGenerator()


@pytest.fixture
def cache_manager():
    """Fixture for cache manager."""
    return ContentCacheManager()


@pytest.fixture
def content_storage():
    """Fixture for content storage."""
    return ContentStorageService()


@pytest.fixture
def difficulty_adapter():
    """Fixture for difficulty adapter."""
    return DifficultyAdapter()


@pytest.fixture
def content_validator():
    """Fixture for content validator."""
    return ContentValidator()


@pytest.fixture
def metadata_enricher():
    """Fixture for metadata enricher."""
    return MetadataEnricher()


@pytest.fixture
def sample_cognitive_load_profile():
    """Sample cognitive load profile for testing."""
    return {
        'current_score': 50,
        'fatigue_level': 'normal'
    }


# ===== Content Generator Tests =====

@pytest.mark.asyncio
async def test_lesson_generation(content_generator):
    """Test lesson content generation."""
    mock_response = MagicMock()
    mock_response.content = "# Python Functions\n\n## Introduction\nFunctions are reusable blocks of code.\n\n## Main Content\nDefine functions with def keyword.\n\n## Summary\nFunctions make code modular."
    
    # Create a mock LLM with ainvoke method
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Replace the llm instance
    original_llm = content_generator.llm
    content_generator.llm = mock_llm
    
    try:
        lesson = await content_generator.generate_lesson(
            topic="Python Functions",
            difficulty="medium",
            prerequisites=["variables", "control flow"],
            estimated_minutes=20,
            cognitive_load_profile={'current_score': 50, 'fatigue_level': 'normal'}
        )
        
        assert isinstance(lesson, str)
        assert len(lesson) > 100
        assert "function" in lesson.lower()
    finally:
        content_generator.llm = original_llm
        
        assert isinstance(lesson, str)
        assert len(lesson) > 100
        assert "function" in lesson.lower()


@pytest.mark.asyncio
async def test_quiz_generation(content_generator):
    """Test quiz generation with valid JSON structure."""
    mock_quiz = [
        {
            "question": "What is a Python list?",
            "options": {"A": "Array", "B": "Dict", "C": "Set", "D": "Tuple"},
            "correct_answer": "A",
            "explanation": "Lists are ordered collections"
        },
        {
            "question": "How to create a list?",
            "options": {"A": "[]", "B": "{}", "C": "()", "D": "<>"},
            "correct_answer": "A",
            "explanation": "Use square brackets"
        },
        {
            "question": "What is list indexing?",
            "options": {"A": "Access", "B": "Delete", "C": "Create", "D": "Sort"},
            "correct_answer": "A",
            "explanation": "Indexing accesses elements"
        }
    ]
    
    mock_response = MagicMock()
    mock_response.content = json.dumps(mock_quiz)
    
    # Create mock LLM
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = content_generator.llm
    content_generator.llm = mock_llm
    
    try:
        quiz_json = await content_generator.generate_quiz(
            topic="Python Lists",
            difficulty="easy",
            num_questions=3,
            cognitive_load_profile={'current_score': 50}
        )
        
        quiz_data = json.loads(quiz_json)
        
        assert isinstance(quiz_data, list)
        assert len(quiz_data) >= 3
        
        # Validate structure
        for question in quiz_data:
            assert 'question' in question
            assert 'options' in question
            assert 'correct_answer' in question
            assert 'explanation' in question
            assert len(question['options']) == 4
    finally:
        content_generator.llm = original_llm


@pytest.mark.asyncio
async def test_exercise_generation(content_generator):
    """Test exercise generation."""
    mock_response = MagicMock()
    mock_response.content = "# Array Algorithm Exercise\n\n## Problem\nSort an array efficiently.\n\n## Hints\n1. Consider time complexity\n2. Use divide and conquer\n\n## Solution\nUse merge sort with O(n log n) complexity."
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = content_generator.llm
    content_generator.llm = mock_llm
    
    try:
        exercise = await content_generator.generate_exercise(
            topic="Array Algorithms",
            difficulty="hard",
            exercise_type="problem-solving",
            cognitive_load_profile={'current_score': 30}
        )
        
        assert isinstance(exercise, str)
        assert len(exercise) > 50
    finally:
        content_generator.llm = original_llm


@pytest.mark.asyncio
async def test_recap_generation(content_generator):
    """Test recap content generation."""
    mock_response = MagicMock()
    mock_response.content = "# Review: Loops and Conditionals\n\n## Summary\n- For loops iterate over sequences\n- While loops continue until condition false\n- If statements control flow\n\n## Common Mistakes\nOff-by-one errors in loop ranges\n\n## Practice\n1. Write a for loop\n2. Create nested conditionals"
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = content_generator.llm
    content_generator.llm = mock_llm
    
    try:
        recap = await content_generator.generate_recap(
            weak_topics=["loops", "conditionals"],
            recent_errors=["off-by-one errors"],
            cognitive_load_profile={'current_score': 75}
        )
        
        assert isinstance(recap, str)
        assert len(recap) > 50
    finally:
        content_generator.llm = original_llm


@pytest.mark.asyncio
async def test_fallback_on_llm_failure(content_generator):
    """Test that fallback content is used when LLM fails."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))
    
    original_llm = content_generator.llm
    content_generator.llm = mock_llm
    
    try:
        lesson = await content_generator.generate_lesson(
            topic="Fallback Test",
            difficulty="medium",
            prerequisites=[],
            estimated_minutes=15,
            cognitive_load_profile={'current_score': 50}
        )
        
        # Should still return content (fallback)
        assert isinstance(lesson, str)
        assert len(lesson) > 0
    finally:
        content_generator.llm = original_llm


# ===== Content Variation Tests =====

@pytest.mark.asyncio
async def test_generate_easier_version(variation_generator):
    """Test generating easier version of content."""
    original_content = "# Advanced Algorithms\n\nComplex sorting with O(n log n) complexity."
    
    mock_response = MagicMock()
    mock_response.content = "# Basic Algorithms\n\nSimple sorting explained step by step with examples."
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = variation_generator.llm
    variation_generator.llm = mock_llm
    
    try:
        easier = await variation_generator.generate_easier_version(
            original_content,
            {'current_score': 80}
        )
        
        assert isinstance(easier, str)
        assert len(easier) > 0
    finally:
        variation_generator.llm = original_llm


@pytest.mark.asyncio
async def test_generate_harder_version(variation_generator):
    """Test generating harder version of content."""
    original_content = "# Basic Loops\n\nSimple for loop examples."
    
    mock_response = MagicMock()
    mock_response.content = "# Advanced Loop Patterns\n\nComplex nested loops with optimization techniques and time complexity analysis."
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = variation_generator.llm
    variation_generator.llm = mock_llm
    
    try:
        harder = await variation_generator.generate_harder_version(
            original_content,
            {'current_score': 20}
        )
        
        assert isinstance(harder, str)
        assert len(harder) > 0
    finally:
        variation_generator.llm = original_llm


@pytest.mark.asyncio
async def test_apply_variation_strategy(variation_generator):
    """Test applying different variation strategies."""
    content = "Original content about data structures."
    
    mock_response = MagicMock()
    mock_response.content = "Simplified content about basic data structures with easy examples."
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = variation_generator.llm
    variation_generator.llm = mock_llm
    
    try:
        result = await variation_generator.apply_variation_strategy(
            content,
            VariationStrategy.SIMPLIFY,
            {'current_score': 70}
        )
        
        assert isinstance(result, str)
    finally:
        variation_generator.llm = original_llm


def test_calculate_content_diff(variation_generator):
    """Test content diff calculation."""
    original = "This is the original content with ten words total."
    modified = "This is modified content."
    
    diff = variation_generator.calculate_content_diff(original, modified)
    
    assert 'original_word_count' in diff
    assert 'modified_word_count' in diff
    assert 'length_change' in diff
    assert diff['original_word_count'] == 9
    assert diff['modified_word_count'] == 4


# ===== Difficulty Adapter Tests =====

def test_adapt_generation_params_high_load(difficulty_adapter):
    """Test parameter adaptation for high cognitive load."""
    base_params = {'topic': 'Test', 'difficulty': 'medium'}
    adapted = difficulty_adapter.adapt_generation_params(base_params, 85)
    
    assert adapted['content_length_multiplier'] == 0.7
    assert adapted['vocabulary_complexity'] == 'simple'
    assert adapted['scaffolding_level'] == 'high'


def test_adapt_generation_params_low_load(difficulty_adapter):
    """Test parameter adaptation for low cognitive load."""
    base_params = {'topic': 'Test', 'difficulty': 'medium'}
    adapted = difficulty_adapter.adapt_generation_params(base_params, 20)
    
    assert adapted['content_length_multiplier'] == 1.2
    assert adapted['vocabulary_complexity'] == 'advanced'
    assert adapted['scaffolding_level'] == 'low'


def test_calculate_optimal_difficulty(difficulty_adapter):
    """Test optimal difficulty calculation."""
    # High load should recommend easier
    easier = difficulty_adapter.calculate_optimal_difficulty(85, 'hard', 0.7)
    assert easier == 'medium'
    
    # Low load with good performance should recommend harder
    harder = difficulty_adapter.calculate_optimal_difficulty(20, 'easy', 0.85)
    assert harder == 'medium'


def test_adjust_quiz_complexity(difficulty_adapter):
    """Test quiz complexity adjustment."""
    # High cognitive load
    high_load_params = difficulty_adapter.adjust_quiz_complexity(85, base_questions=5)
    assert high_load_params['num_questions'] == 3
    assert high_load_params['time_limit_multiplier'] == 1.5
    
    # Low cognitive load
    low_load_params = difficulty_adapter.adjust_quiz_complexity(20, base_questions=5)
    assert low_load_params['num_questions'] == 7
    assert low_load_params['time_limit_multiplier'] == 0.8


def test_pacing_recommendations(difficulty_adapter):
    """Test pacing recommendations."""
    high_load_pacing = difficulty_adapter.get_pacing_recommendations(80, session_duration_minutes=20)
    assert high_load_pacing['chunk_duration_minutes'] == 10
    assert high_load_pacing['recommend_break_now'] == True
    
    low_load_pacing = difficulty_adapter.get_pacing_recommendations(25, session_duration_minutes=30)
    assert low_load_pacing['chunk_duration_minutes'] == 30
    assert low_load_pacing['recommend_break_now'] == False


# ===== Content Validator Tests =====

def test_validate_lesson(content_validator):
    """Test lesson validation."""
    lesson = """
# Introduction to Python

Learn Python basics.

## Main Content

Python is a programming language. For example, you can print "Hello".

## Summary
- Learn basics
- Practice coding
"""
    
    result = content_validator.validate_content(
        content=lesson,
        content_type='lesson',
        expected_difficulty='easy',
        estimated_minutes=15,
        prerequisites=[]
    )
    
    assert isinstance(result.passed, bool)
    assert isinstance(result.issues, list)


def test_validate_quiz(content_validator):
    """Test quiz validation."""
    quiz = json.dumps([
        {
            "question": "What is Python?",
            "options": {"A": "Language", "B": "Snake", "C": "Tool", "D": "None"},
            "correct_answer": "A",
            "explanation": "Python is a programming language."
        }
    ])
    
    result = content_validator.validate_content(
        content=quiz,
        content_type='quiz',
        expected_difficulty='easy',
        estimated_minutes=5,
        prerequisites=[]
    )
    
    # Should have at least 3 questions warning
    assert isinstance(result.passed, bool)


def test_calculate_readability_score(content_validator):
    """Test readability score calculation."""
    simple_text = "This is simple. It is easy. Very easy."
    score = content_validator.calculate_readability_score(simple_text)
    
    assert 0 <= score <= 100
    assert score > 50  # Simple text should have higher readability


def test_check_prerequisite_coverage(content_validator):
    """Test prerequisite coverage checking."""
    content = "Before learning loops, you need variables and conditions."
    prerequisites = ["variables", "conditions"]
    
    all_covered, missing = content_validator.check_prerequisite_coverage(content, prerequisites)
    
    assert all_covered == True
    assert len(missing) == 0


# ===== Metadata Enricher Tests =====

def test_extract_key_concepts(metadata_enricher):
    """Test key concept extraction."""
    content = """Functions are reusable blocks of code. They take parameters and return values. 
    Functions make code modular and maintainable."""
    
    concepts = metadata_enricher.extract_key_concepts(content, max_concepts=5)
    
    assert isinstance(concepts, list)
    assert len(concepts) <= 5
    assert any('function' in c.lower() for c in concepts)


def test_calculate_reading_time(metadata_enricher):
    """Test reading time calculation."""
    short_text = " ".join(["word"] * 100)  # 100 words
    reading_time = metadata_enricher.calculate_reading_time(short_text)
    
    assert reading_time == 1  # Should be 1 minute


def test_detect_content_type(metadata_enricher):
    """Test content type detection."""
    lesson_content = "# Introduction\n\nLet's learn about functions."
    assert metadata_enricher.detect_content_type(lesson_content) == 'lesson'
    
    quiz_content = '{"question": "Test", "correct_answer": "A"}'
    assert metadata_enricher.detect_content_type(quiz_content) == 'quiz'


def test_generate_tags(metadata_enricher):
    """Test tag generation."""
    content = "Advanced algorithms and data structures for expert programmers."
    tags = metadata_enricher.generate_tags(content, 'lesson', max_tags=5)
    
    assert isinstance(tags, list)
    assert len(tags) <= 5
    assert 'lesson' in tags


def test_enrich_metadata(metadata_enricher):
    """Test full metadata enrichment."""
    content = "# Functions\n\nFunctions are blocks of reusable code."
    
    metadata = metadata_enricher.enrich_metadata(content, 'lesson')
    
    assert 'key_concepts' in metadata
    assert 'calculated_reading_time' in metadata
    assert 'tags' in metadata
    assert 'complexity_metrics' in metadata


# ===== Integration Tests =====

@pytest.mark.asyncio
async def test_end_to_end_generation_flow(content_generator, content_validator, metadata_enricher):
    """Test complete content generation flow."""
    mock_response = MagicMock()
    mock_response.content = "# Testing in Python\n\n## Introduction\nLearn testing fundamentals and best practices.\n\n## Main Content\nUnit tests validate code behavior. Use pytest framework for testing.\n\n## Examples\nWrite simple test functions with assertions.\n\n## Summary\n- Testing ensures code quality\n- pytest is powerful\n- Write tests early"
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    original_llm = content_generator.llm
    content_generator.llm = mock_llm
    
    try:
        # Generate content
        lesson = await content_generator.generate_lesson(
            topic="Testing",
            difficulty="medium",
            prerequisites=[],
            estimated_minutes=15,
            cognitive_load_profile={'current_score': 50}
        )
        
        # Validate
        validation = content_validator.validate_content(
            content=lesson,
            content_type='lesson',
            expected_difficulty='medium',
            estimated_minutes=15,
            prerequisites=[]
        )
        
        # Enrich metadata
        metadata = metadata_enricher.enrich_metadata(lesson, 'lesson')
        
        assert isinstance(lesson, str)
        assert isinstance(validation.passed, bool)
        assert isinstance(metadata, dict)
    finally:
        content_generator.llm = original_llm
