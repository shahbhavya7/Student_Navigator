"""
Curriculum Management Module

Provides intelligent curriculum adaptation based on student performance,
cognitive load, and engagement patterns.
"""

from curriculum.learning_graph import LearningPathGraph, ConceptDependencyAnalyzer
from curriculum.difficulty_adjuster import DifficultyAdjuster
from curriculum.concept_reshuffler import ConceptReshuffler
from curriculum.state_manager import CurriculumStateManager

__all__ = [
    "LearningPathGraph",
    "ConceptDependencyAnalyzer",
    "DifficultyAdjuster",
    "ConceptReshuffler",
    "CurriculumStateManager"
]
