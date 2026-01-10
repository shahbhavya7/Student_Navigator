"""
Unit Tests for Curriculum Agent

Tests learning graph operations, difficulty adjustment, concept reshuffling,
state management, and curriculum adjustment orchestration.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from agents.curriculum_agent import CurriculumAgent
from curriculum.learning_graph import LearningPathGraph
from curriculum.difficulty_adjuster import DifficultyAdjuster
from curriculum.concept_reshuffler import ConceptReshuffler
from curriculum.state_manager import CurriculumStateManager


@pytest.fixture
def curriculum_agent():
    """Create Curriculum Agent instance for testing."""
    return CurriculumAgent(agent_id="test_curriculum_agent")


@pytest.fixture
def sample_modules():
    """Sample learning modules for testing."""
    return [
        {
            'id': 'mod_1',
            'title': 'Introduction to Python',
            'content': 'Basic Python concepts',
            'difficulty': 1,
            'moduleType': 'tutorial',
            'estimatedMinutes': 30,
            'orderIndex': 0,
            'prerequisites': [],
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        },
        {
            'id': 'mod_2',
            'title': 'Variables and Data Types',
            'content': 'Learn about variables',
            'difficulty': 2,
            'moduleType': 'tutorial',
            'estimatedMinutes': 45,
            'orderIndex': 1,
            'prerequisites': ['mod_1'],
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        },
        {
            'id': 'mod_3',
            'title': 'Control Flow',
            'content': 'If statements and loops',
            'difficulty': 3,
            'moduleType': 'tutorial',
            'estimatedMinutes': 60,
            'orderIndex': 2,
            'prerequisites': ['mod_2'],
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        },
        {
            'id': 'mod_4',
            'title': 'Functions',
            'content': 'Creating and using functions',
            'difficulty': 4,
            'moduleType': 'tutorial',
            'estimatedMinutes': 50,
            'orderIndex': 3,
            'prerequisites': ['mod_3'],
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        }
    ]


@pytest.fixture
def sample_state():
    """Sample agent state for testing."""
    return {
        'student_id': 'student_123',
        'learning_path_id': 'path_456',
        'current_module_id': 'mod_2',
        'completed_modules': ['mod_1'],
        'cognitive_load_score': 75,
        'quiz_accuracy': 65.0,
        'struggle_indicators': ['high_time_on_task', 'low_quiz_scores'],
        'engagement_level': 'moderate',
        'learning_velocity': 1.8,
        'improvement_trend': 'declining'
    }


# ============================================================================
# Learning Graph Tests
# ============================================================================

@pytest.mark.asyncio
async def test_learning_graph_load_path(sample_modules):
    """Test loading learning path into graph structure."""
    graph = LearningPathGraph()
    
    with patch.object(graph, 'db_session') as mock_db:
        mock_db.execute.return_value.fetchall.return_value = [
            (m['id'], m['title'], m['content'], m['difficulty'], 
             m['moduleType'], m['estimatedMinutes'], m['orderIndex'], 
             m['prerequisites']) 
            for m in sample_modules
        ]
        
        await graph.load_learning_path('path_456')
        
        assert len(graph.modules) == 4
        assert graph.modules['mod_1']['prerequisites'] == []
        assert graph.modules['mod_2']['prerequisites'] == ['mod_1']


@pytest.mark.asyncio
async def test_learning_graph_get_available_modules(sample_modules):
    """Test getting modules available based on completed prerequisites."""
    graph = LearningPathGraph()
    graph.modules = {m['id']: m for m in sample_modules}
    
    # Only mod_1 completed
    available = graph.get_available_modules(['mod_1'])
    assert 'mod_2' in available
    assert 'mod_3' not in available
    
    # mod_1 and mod_2 completed
    available = graph.get_available_modules(['mod_1', 'mod_2'])
    assert 'mod_3' in available
    assert 'mod_4' not in available


@pytest.mark.asyncio
async def test_learning_graph_find_easier_alternatives(sample_modules):
    """Test finding easier alternative modules."""
    graph = LearningPathGraph()
    graph.modules = {m['id']: m for m in sample_modules}
    
    alternatives = graph.find_easier_alternatives('mod_4', max_difficulty=3)
    assert len(alternatives) > 0
    assert all(m['difficulty'] <= 3 for m in alternatives)


@pytest.mark.asyncio
async def test_learning_graph_prerequisite_review(sample_modules):
    """Test getting prerequisite modules for review."""
    graph = LearningPathGraph()
    graph.modules = {m['id']: m for m in sample_modules}
    
    review_modules = graph.get_prerequisite_review_modules('mod_3')
    assert 'mod_1' in review_modules or 'mod_2' in review_modules


# ============================================================================
# Difficulty Adjuster Tests
# ============================================================================

def test_difficulty_adjuster_analyze_performance():
    """Test analyzing performance metrics."""
    adjuster = DifficultyAdjuster()
    
    # Low performance scenario
    performance_score = adjuster.analyze_performance_metrics(
        quiz_accuracy=50.0,
        completion_rate=60.0,
        time_efficiency=0.5
    )
    assert performance_score < 60
    
    # High performance scenario
    performance_score = adjuster.analyze_performance_metrics(
        quiz_accuracy=90.0,
        completion_rate=95.0,
        time_efficiency=1.2
    )
    assert performance_score > 80


def test_difficulty_adjuster_cognitive_load_factor():
    """Test cognitive load impact on difficulty adjustment."""
    adjuster = DifficultyAdjuster()
    
    # High cognitive load should reduce recommended difficulty
    adjustment = adjuster.calculate_cognitive_load_factor(85)
    assert adjustment < 0
    
    # Low cognitive load allows increased difficulty
    adjustment = adjuster.calculate_cognitive_load_factor(40)
    assert adjustment > 0


def test_difficulty_adjuster_recommend_difficulty():
    """Test overall difficulty recommendation."""
    adjuster = DifficultyAdjuster()
    
    factors = {
        'quiz_accuracy': 65.0,
        'cognitive_load': 75,
        'engagement_level': 'moderate',
        'learning_velocity': 1.5,
        'recent_struggles': True
    }
    
    recommendation = adjuster.recommend_difficulty_adjustment(
        current_difficulty=3,
        **factors
    )
    
    assert 'action' in recommendation
    assert 'target_difficulty' in recommendation
    assert 'confidence' in recommendation
    assert recommendation['action'] in ['decrease', 'maintain', 'increase']


# ============================================================================
# Concept Reshuffler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_concept_reshuffler_reorder_modules(sample_modules):
    """Test reordering modules based on student needs."""
    reshuffler = ConceptReshuffler()
    
    student_context = {
        'completed_modules': ['mod_1'],
        'current_module': 'mod_2',
        'struggle_topics': ['control flow'],
        'strong_topics': ['variables'],
        'cognitive_load': 70
    }
    
    reordered = await reshuffler.reorder_learning_path(
        sample_modules,
        student_context
    )
    
    assert len(reordered) == len(sample_modules)
    assert all('orderIndex' in m for m in reordered)
    # Verify prerequisites are still respected
    for module in reordered:
        for prereq_id in module['prerequisites']:
            prereq = next(m for m in reordered if m['id'] == prereq_id)
            assert prereq['orderIndex'] < module['orderIndex']


@pytest.mark.asyncio
async def test_concept_reshuffler_inject_review_modules(sample_modules):
    """Test injecting review modules for struggling topics."""
    reshuffler = ConceptReshuffler()
    
    current_path = sample_modules[:2]
    struggling_module = sample_modules[2]
    
    enhanced_path = await reshuffler.inject_review_modules(
        current_path,
        struggling_module,
        review_depth=1
    )
    
    # Should have original modules plus potential review injections
    assert len(enhanced_path) >= len(current_path)


@pytest.mark.asyncio
async def test_concept_reshuffler_optimize_cognitive_load(sample_modules):
    """Test optimizing module sequence for cognitive load."""
    reshuffler = ConceptReshuffler()
    
    optimized = await reshuffler.optimize_for_cognitive_load(
        sample_modules,
        target_load=60
    )
    
    # Should alternate difficulty levels or group appropriately
    assert len(optimized) == len(sample_modules)
    # Check that high-difficulty modules are spaced out
    high_diff_indices = [i for i, m in enumerate(optimized) if m['difficulty'] >= 4]
    if len(high_diff_indices) > 1:
        # Should have spacing between high difficulty modules
        assert max(high_diff_indices) - min(high_diff_indices) > len(high_diff_indices)


# ============================================================================
# State Manager Tests
# ============================================================================

@pytest.mark.asyncio
async def test_state_manager_get_current_state():
    """Test retrieving current curriculum state."""
    state_manager = CurriculumStateManager()
    
    with patch.object(state_manager, 'db') as mock_db, \
         patch.object(state_manager, 'redis') as mock_redis:
        
        # Mock Redis cache miss
        mock_redis.get.return_value = None
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            'path_456', ['mod_1', 'mod_2'], 'mod_3', 2, datetime.now()
        )
        mock_db.execute.return_value = mock_result
        
        state = await state_manager.get_current_state('student_123', 'path_456')
        
        assert state is not None
        assert state['learning_path_id'] == 'path_456'
        assert 'completed_modules' in state


@pytest.mark.asyncio
async def test_state_manager_save_adjustment():
    """Test saving curriculum adjustment with version history."""
    state_manager = CurriculumStateManager()
    
    with patch.object(state_manager, 'db') as mock_db, \
         patch.object(state_manager, 'redis') as mock_redis:
        
        adjustment_data = {
            'student_id': 'student_123',
            'learning_path_id': 'path_456',
            'new_module_order': ['mod_1', 'mod_2', 'mod_3'],
            'adjustment_reason': 'High cognitive load',
            'difficulty_change': -1
        }
        
        await state_manager.save_curriculum_adjustment(adjustment_data)
        
        # Verify database update was called
        assert mock_db.execute.called
        # Verify Redis cache was invalidated
        assert mock_redis.delete.called


@pytest.mark.asyncio
async def test_state_manager_rollback():
    """Test rolling back to previous curriculum version."""
    state_manager = CurriculumStateManager()
    
    with patch.object(state_manager, 'db') as mock_db:
        
        # Mock history entry
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            'path_456', {'modules': ['mod_1', 'mod_2']}, 'Test rollback', datetime.now()
        )
        mock_db.execute.return_value = mock_result
        
        success = await state_manager.rollback_to_version('student_123', 'path_456', 1)
        
        assert success is not None


# ============================================================================
# Curriculum Agent Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_curriculum_agent_analyze_needs(curriculum_agent, sample_state):
    """Test analyzing curriculum adjustment needs."""
    analysis = await curriculum_agent.analyze_adjustment_needs(sample_state)
    
    assert 'needs_adjustment' in analysis
    assert 'primary_issues' in analysis
    assert 'recommended_actions' in analysis
    
    # With high cognitive load and declining performance, should recommend adjustment
    if sample_state['cognitive_load_score'] > 70 and sample_state['quiz_accuracy'] < 70:
        assert analysis['needs_adjustment'] is True


@pytest.mark.asyncio
async def test_curriculum_agent_generate_plan(curriculum_agent, sample_state):
    """Test generating curriculum adjustment plan."""
    with patch.object(curriculum_agent, 'learning_graph') as mock_graph, \
         patch.object(curriculum_agent, 'difficulty_adjuster') as mock_adjuster:
        
        mock_graph.modules = {
            'mod_1': {'id': 'mod_1', 'difficulty': 2},
            'mod_2': {'id': 'mod_2', 'difficulty': 3}
        }
        
        mock_adjuster.recommend_difficulty_adjustment.return_value = {
            'action': 'decrease',
            'target_difficulty': 2,
            'confidence': 0.8
        }
        
        plan = await curriculum_agent.generate_adjustment_plan(sample_state)
        
        assert 'difficulty_adjustment' in plan
        assert 'module_reordering' in plan
        assert 'review_injections' in plan


@pytest.mark.asyncio
async def test_curriculum_agent_execute(curriculum_agent, sample_state):
    """Test end-to-end curriculum agent execution."""
    with patch.object(curriculum_agent, 'state_manager') as mock_state, \
         patch.object(curriculum_agent, 'learning_graph') as mock_graph, \
         patch.object(curriculum_agent, 'llm') as mock_llm:
        
        # Mock state retrieval
        mock_state.get_current_state.return_value = sample_state
        
        # Mock graph operations
        mock_graph.load_learning_path = AsyncMock()
        mock_graph.modules = {
            'mod_1': {'id': 'mod_1', 'difficulty': 2, 'prerequisites': []},
            'mod_2': {'id': 'mod_2', 'difficulty': 3, 'prerequisites': ['mod_1']}
        }
        
        # Mock LLM rationale
        mock_llm.invoke.return_value.content = "Adjusted curriculum due to high cognitive load"
        
        result = await curriculum_agent.execute(sample_state)
        
        assert 'adjustment_applied' in result
        assert 'reasoning' in result
        assert 'new_curriculum_state' in result


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_curriculum_agent_missing_data(curriculum_agent):
    """Test handling of incomplete state data."""
    incomplete_state = {
        'student_id': 'student_123'
        # Missing other required fields
    }
    
    result = await curriculum_agent.execute(incomplete_state)
    
    # Should handle gracefully or return error indication
    assert result is not None


@pytest.mark.asyncio
async def test_learning_graph_circular_dependencies():
    """Test detection of circular prerequisite dependencies."""
    graph = LearningPathGraph()
    
    # Create circular dependency
    graph.modules = {
        'mod_1': {'id': 'mod_1', 'prerequisites': ['mod_2']},
        'mod_2': {'id': 'mod_2', 'prerequisites': ['mod_1']}
    }
    
    is_valid = graph.validate_path_integrity()
    assert is_valid is False


def test_difficulty_adjuster_extreme_values():
    """Test difficulty adjuster with extreme input values."""
    adjuster = DifficultyAdjuster()
    
    # Test with 0 accuracy
    result = adjuster.recommend_difficulty_adjustment(
        current_difficulty=5,
        quiz_accuracy=0.0,
        cognitive_load=95,
        engagement_level='low',
        learning_velocity=0.1,
        recent_struggles=True
    )
    
    assert result['action'] == 'decrease'
    assert result['target_difficulty'] < 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
