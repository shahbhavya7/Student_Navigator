"""
Machine Learning Module for Cognitive Load Analysis

This module provides ML-based pattern recognition and sentiment analysis
for the Cognitive Load Radar (CLR) system.
"""

from .cognitive_patterns import (
    CognitivePatternDetector,
    PatternFeatureExtractor,
    MentalStrainClassifier,
    HistoricalBaselineTracker
)

__all__ = [
    'CognitivePatternDetector',
    'PatternFeatureExtractor',
    'MentalStrainClassifier',
    'HistoricalBaselineTracker'
]
