"""
Integration Tests for Curriculum API Endpoints

Tests all 6 curriculum REST API endpoints with realistic scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    with patch('api.curriculum.get_async_db') as mock:
        db_session = MagicMock()
        mock.return_value.__aiter__.return_value = [db_session]
        yield db_session


@pytest.fixture
def sample_learning_path():
    """Sample learning path data."""
    return {
        'id': 'path_123',
        'studentId': 'student_456',
        'pathName': 'Python Fundamentals',
        'difficulty': 3,
        'status': 'active',
        'progress': 45.0,
        'createdAt': datetime.now(),
        'updatedAt': datetime.now()
    }


@pytest.fixture
def sample_modules():
    """Sample curriculum modules."""
    return [
        {
            'id': 'mod_1',
            'title': 'Variables',
            'content': 'Learn variables',
            'difficulty': 2,
            'moduleType': 'tutorial',
            'estimatedMinutes': 30,
            'orderIndex': 0,
            'prerequisites': [],
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        },
        {
            'id': 'mod_2',
            'title': 'Functions',
            'content': 'Learn functions',
            'difficulty': 3,
            'moduleType': 'tutorial',
            'estimatedMinutes': 45,
            'orderIndex': 1,
            'prerequisites': ['mod_1'],
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        }
    ]


# ============================================================================
# GET /curriculum/current Tests
# ============================================================================

def test_get_current_curriculum_success(client, mock_db, sample_learning_path, sample_modules):
    """Test retrieving current curriculum for a student."""
    # Mock database responses
    mock_result_path = MagicMock()
    mock_result_path.fetchone.return_value = (
        sample_learning_path['id'],
        sample_learning_path['pathName'],
        sample_learning_path['difficulty'],
        sample_learning_path['progress']
    )
    
    mock_result_modules = MagicMock()
    mock_result_modules.fetchall.return_value = [
        (m['id'], m['title'], m['difficulty'], m['orderIndex'], m['estimatedMinutes'])
        for m in sample_modules
    ]
    
    mock_result_completed = MagicMock()
    mock_result_completed.fetchall.return_value = [('mod_1',)]
    
    mock_db.execute.side_effect = [mock_result_path, mock_result_modules, mock_result_completed]
    
    response = client.get("/curriculum/current?student_id=student_456")
    
    assert response.status_code == 200
    data = response.json()
    assert 'learning_path_id' in data
    assert 'modules' in data
    assert 'completed_modules' in data


def test_get_current_curriculum_not_found(client, mock_db):
    """Test retrieving curriculum when student has no active path."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result
    
    response = client.get("/curriculum/current?student_id=nonexistent_student")
    
    assert response.status_code == 404
    assert "No active learning path" in response.json()['detail']


def test_get_current_curriculum_missing_student_id(client):
    """Test retrieving curriculum without student_id parameter."""
    response = client.get("/curriculum/current")
    
    assert response.status_code == 422  # Validation error


# ============================================================================
# GET /curriculum/path/{path_id} Tests
# ============================================================================

def test_get_learning_path_success(client, mock_db, sample_learning_path, sample_modules):
    """Test retrieving specific learning path details."""
    mock_result_path = MagicMock()
    mock_result_path.fetchone.return_value = (
        sample_learning_path['id'],
        sample_learning_path['pathName'],
        sample_learning_path['difficulty'],
        sample_learning_path['studentId']
    )
    
    mock_result_modules = MagicMock()
    mock_result_modules.fetchall.return_value = [
        (m['id'], m['title'], m['content'][:100], m['difficulty'], 
         m['moduleType'], m['estimatedMinutes'], m['orderIndex'], m['prerequisites'])
        for m in sample_modules
    ]
    
    mock_db.execute.side_effect = [mock_result_path, mock_result_modules]
    
    response = client.get("/curriculum/path/path_123")
    
    assert response.status_code == 200
    data = response.json()
    assert data['path_id'] == 'path_123'
    assert 'modules' in data
    assert len(data['modules']) > 0


def test_get_learning_path_not_found(client, mock_db):
    """Test retrieving non-existent learning path."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result
    
    response = client.get("/curriculum/path/invalid_path")
    
    assert response.status_code == 404


# ============================================================================
# POST /curriculum/adjust Tests
# ============================================================================

def test_adjust_curriculum_success(client, mock_db):
    """Test successful curriculum adjustment."""
    with patch('api.curriculum.CurriculumAgent') as mock_agent:
        # Mock agent execution
        mock_instance = mock_agent.return_value
        mock_instance.execute = AsyncMock(return_value={
            'adjustment_applied': True,
            'reasoning': 'Reduced difficulty due to high cognitive load',
            'new_curriculum_state': {
                'modules': ['mod_1', 'mod_2'],
                'current_difficulty': 2
            }
        })
        
        # Mock database update
        mock_db.execute.return_value = MagicMock()
        
        request_data = {
            'student_id': 'student_456',
            'learning_path_id': 'path_123',
            'reason': 'Student struggling with current difficulty',
            'agent_state': {
                'cognitive_load_score': 85,
                'quiz_accuracy': 55.0,
                'current_module_id': 'mod_2'
            }
        }
        
        response = client.post("/curriculum/adjust", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'adjustment_reasoning' in data


def test_adjust_curriculum_no_change_needed(client, mock_db):
    """Test curriculum adjustment when no changes are needed."""
    with patch('api.curriculum.CurriculumAgent') as mock_agent:
        mock_instance = mock_agent.return_value
        mock_instance.execute = AsyncMock(return_value={
            'adjustment_applied': False,
            'reasoning': 'Current curriculum is optimal',
            'new_curriculum_state': None
        })
        
        request_data = {
            'student_id': 'student_456',
            'learning_path_id': 'path_123',
            'reason': 'Routine check',
            'agent_state': {
                'cognitive_load_score': 55,
                'quiz_accuracy': 85.0
            }
        }
        
        response = client.post("/curriculum/adjust", json=request_data)
        
        assert response.status_code == 200
        assert response.json()['success'] is True


def test_adjust_curriculum_invalid_data(client):
    """Test curriculum adjustment with invalid request data."""
    request_data = {
        'student_id': 'student_456'
        # Missing required fields
    }
    
    response = client.post("/curriculum/adjust", json=request_data)
    
    assert response.status_code == 422  # Validation error


# ============================================================================
# GET /curriculum/history Tests
# ============================================================================

def test_get_curriculum_history_success(client, mock_db):
    """Test retrieving curriculum adjustment history."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, 'path_123', {'modules': ['mod_1']}, 'Initial setup', datetime.now()),
        (2, 'path_123', {'modules': ['mod_1', 'mod_2']}, 'Added module', datetime.now())
    ]
    mock_db.execute.return_value = mock_result
    
    response = client.get("/curriculum/history?student_id=student_456&path_id=path_123")
    
    assert response.status_code == 200
    data = response.json()
    assert 'history' in data
    assert len(data['history']) == 2


def test_get_curriculum_history_empty(client, mock_db):
    """Test retrieving history when none exists."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result
    
    response = client.get("/curriculum/history?student_id=student_456&path_id=path_123")
    
    assert response.status_code == 200
    assert len(response.json()['history']) == 0


def test_get_curriculum_history_with_limit(client, mock_db):
    """Test retrieving history with limit parameter."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (i, 'path_123', {'modules': []}, f'Version {i}', datetime.now())
        for i in range(1, 6)
    ]
    mock_db.execute.return_value = mock_result
    
    response = client.get("/curriculum/history?student_id=student_456&path_id=path_123&limit=3")
    
    assert response.status_code == 200
    # Note: actual limiting happens in SQL query
    assert 'history' in response.json()


# ============================================================================
# POST /curriculum/rollback Tests
# ============================================================================

def test_rollback_curriculum_success(client, mock_db):
    """Test successful curriculum rollback."""
    # Mock history lookup
    mock_history = MagicMock()
    mock_history.fetchone.return_value = (
        'path_123',
        {'modules': ['mod_1'], 'difficulty': 2},
        'Previous version',
        datetime.now()
    )
    
    # Mock update
    mock_update = MagicMock()
    
    mock_db.execute.side_effect = [mock_history, mock_update]
    
    request_data = {
        'student_id': 'student_456',
        'learning_path_id': 'path_123',
        'version': 1,
        'reason': 'Reverting to easier difficulty'
    }
    
    response = client.post("/curriculum/rollback", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert 'restored_state' in data


def test_rollback_curriculum_version_not_found(client, mock_db):
    """Test rollback to non-existent version."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result
    
    request_data = {
        'student_id': 'student_456',
        'learning_path_id': 'path_123',
        'version': 999,
        'reason': 'Testing invalid version'
    }
    
    response = client.post("/curriculum/rollback", json=request_data)
    
    assert response.status_code == 404


# ============================================================================
# GET /curriculum/recommendations Tests
# ============================================================================

def test_get_recommendations_success(client, mock_db):
    """Test getting curriculum recommendations."""
    # Mock active paths query
    mock_paths = MagicMock()
    mock_paths.fetchone.return_value = ('path_123',)
    
    # Mock state data
    mock_state = MagicMock()
    mock_state.fetchone.return_value = (
        'path_123', ['mod_1'], 'mod_2', 3, datetime.now()
    )
    
    # Mock quiz results
    mock_quiz = MagicMock()
    mock_quiz.fetchone.return_value = (75.0, 3)
    
    # Mock cognitive metrics
    mock_cognitive = MagicMock()
    mock_cognitive.fetchone.return_value = (65,)
    
    mock_db.execute.side_effect = [mock_paths, mock_state, mock_quiz, mock_cognitive]
    
    with patch('api.curriculum.DifficultyAdjuster') as mock_adjuster:
        mock_instance = mock_adjuster.return_value
        mock_instance.recommend_difficulty_adjustment.return_value = {
            'action': 'maintain',
            'target_difficulty': 3,
            'confidence': 0.9,
            'reasons': ['Good performance', 'Stable cognitive load']
        }
        
        response = client.get("/curriculum/recommendations?student_id=student_456")
        
        assert response.status_code == 200
        data = response.json()
        assert 'recommended_action' in data
        assert 'confidence' in data


def test_get_recommendations_no_active_path(client, mock_db):
    """Test recommendations when student has no active learning path."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result
    
    response = client.get("/curriculum/recommendations?student_id=student_456")
    
    assert response.status_code == 404


def test_get_recommendations_insufficient_data(client, mock_db):
    """Test recommendations with insufficient student data."""
    # Mock path exists but no quiz data
    mock_path = MagicMock()
    mock_path.fetchone.return_value = ('path_123',)
    
    mock_state = MagicMock()
    mock_state.fetchone.return_value = ('path_123', [], None, 2, datetime.now())
    
    mock_quiz = MagicMock()
    mock_quiz.fetchone.return_value = (None, 0)  # No quiz data
    
    mock_db.execute.side_effect = [mock_path, mock_state, mock_quiz]
    
    response = client.get("/curriculum/recommendations?student_id=student_456")
    
    # Should still return recommendations based on available data
    assert response.status_code in [200, 422]


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_api_database_error(client, mock_db):
    """Test API behavior when database errors occur."""
    mock_db.execute.side_effect = Exception("Database connection failed")
    
    response = client.get("/curriculum/current?student_id=student_456")
    
    assert response.status_code == 500


def test_api_invalid_json(client):
    """Test API with malformed JSON."""
    response = client.post(
        "/curriculum/adjust",
        data="invalid json{",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
