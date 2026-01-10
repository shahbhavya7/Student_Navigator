"""
Difficulty Adjustment Algorithm

Implements intelligent difficulty adjustment based on cognitive load,
performance metrics, and engagement patterns.
"""

from typing import Dict, Any, List
from curriculum.learning_graph import LearningPathGraph
import logging


class DifficultyAdjuster:
    """Calculates optimal difficulty adjustments based on student metrics"""
    
    # Adjustment thresholds
    COGNITIVE_LOAD_HIGH = 75
    COGNITIVE_LOAD_LOW = 30
    QUIZ_ACCURACY_LOW = 50
    QUIZ_ACCURACY_HIGH = 85
    ENGAGEMENT_THRESHOLD = 60
    
    # Difficulty scoring weights
    WEIGHT_COGNITIVE_LOAD = 0.40
    WEIGHT_QUIZ_ACCURACY = 0.30
    WEIGHT_LEARNING_VELOCITY = 0.20
    WEIGHT_ENGAGEMENT = 0.10
    
    def __init__(self):
        self.logger = logging.getLogger("DifficultyAdjuster")
    
    def calculate_target_difficulty(self, student_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine optimal difficulty level based on student metrics.
        
        Args:
            student_metrics: Dict containing cognitive_load_score, quiz_accuracy,
                           learning_velocity, engagement_score, plateau_detected
        
        Returns:
            Dict with target_difficulty, confidence, reasoning
        """
        cognitive_load = student_metrics.get("cognitive_load_score", 50)
        quiz_accuracy = student_metrics.get("quiz_accuracy", 0)
        learning_velocity = student_metrics.get("learning_velocity", 0)
        engagement_score = student_metrics.get("engagement_score", 0)
        plateau_detected = student_metrics.get("plateau_detected", False)
        improvement_trend = student_metrics.get("improvement_trend", "stable")
        
        # Calculate component scores (normalize to 0-100 where higher = can handle more difficulty)
        cognitive_score = 100 - cognitive_load  # Inverse: low load = can handle more
        accuracy_score = quiz_accuracy
        velocity_score = min((learning_velocity + 5) * 10, 100)  # Normalize velocity
        engagement_normalized = engagement_score
        
        # Weighted average
        readiness_score = (
            cognitive_score * self.WEIGHT_COGNITIVE_LOAD +
            accuracy_score * self.WEIGHT_QUIZ_ACCURACY +
            velocity_score * self.WEIGHT_LEARNING_VELOCITY +
            engagement_normalized * self.WEIGHT_ENGAGEMENT
        )
        
        # Determine target difficulty
        if plateau_detected or cognitive_load > self.COGNITIVE_LOAD_HIGH or quiz_accuracy < self.QUIZ_ACCURACY_LOW:
            target = "easy"
            reasoning = []
            if plateau_detected:
                reasoning.append("learning plateau detected")
            if cognitive_load > self.COGNITIVE_LOAD_HIGH:
                reasoning.append(f"high cognitive load ({cognitive_load})")
            if quiz_accuracy < self.QUIZ_ACCURACY_LOW:
                reasoning.append(f"low quiz accuracy ({quiz_accuracy}%)")
            confidence = 0.85
            
        elif (cognitive_load < self.COGNITIVE_LOAD_LOW and 
              quiz_accuracy > self.QUIZ_ACCURACY_HIGH and 
              engagement_score > self.ENGAGEMENT_THRESHOLD and
              improvement_trend == "improving"):
            target = "hard"
            reasoning = [
                f"low cognitive load ({cognitive_load})",
                f"high quiz accuracy ({quiz_accuracy}%)",
                f"strong engagement ({engagement_score})",
                "improving trend"
            ]
            confidence = 0.90
            
        else:
            target = "medium"
            reasoning = ["balanced performance metrics"]
            confidence = 0.75
        
        return {
            "target_difficulty": target,
            "confidence": round(confidence, 2),
            "readiness_score": round(readiness_score, 2),
            "reasoning": reasoning,
            "component_scores": {
                "cognitive_readiness": round(cognitive_score, 2),
                "accuracy_score": round(accuracy_score, 2),
                "velocity_score": round(velocity_score, 2),
                "engagement_score": round(engagement_normalized, 2)
            }
        }
    
    def should_adjust_difficulty(
        self, 
        current_difficulty: str, 
        target_difficulty: str, 
        confidence: float
    ) -> bool:
        """
        Determine if difficulty should be adjusted.
        
        Args:
            current_difficulty: Current difficulty level
            target_difficulty: Recommended difficulty level
            confidence: Confidence score for recommendation
        
        Returns:
            True if adjustment should be made
        """
        # Don't adjust if target matches current
        if current_difficulty == target_difficulty:
            return False
        
        # Require high confidence for difficulty increases
        if self._get_difficulty_value(target_difficulty) > self._get_difficulty_value(current_difficulty):
            return confidence >= 0.85
        
        # Lower threshold for difficulty decreases (safety first)
        return confidence >= 0.75
    
    def generate_adjustment_plan(
        self,
        current_path: LearningPathGraph,
        target_difficulty: str,
        student_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create comprehensive adjustment plan for curriculum modifications.
        
        Args:
            current_path: Current learning path graph
            target_difficulty: Target difficulty level
            student_metrics: Student performance metrics
        
        Returns:
            List of adjustment actions
        """
        adjustments = []
        current_difficulty = self._infer_path_difficulty(current_path)
        
        # Determine adjustment direction
        difficulty_change = self._get_difficulty_value(target_difficulty) - self._get_difficulty_value(current_difficulty)
        
        if difficulty_change < 0:
            # Reduce difficulty
            adjustments.extend(self._generate_difficulty_reduction_plan(current_path, student_metrics))
        elif difficulty_change > 0:
            # Increase difficulty
            adjustments.extend(self._generate_difficulty_increase_plan(current_path, student_metrics))
        
        return adjustments
    
    def _generate_difficulty_reduction_plan(
        self,
        current_path: LearningPathGraph,
        student_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate plan to reduce difficulty"""
        plan = []
        weak_topics = student_metrics.get("weak_topics", [])
        
        # 1. Downgrade module difficulties
        for module_id, module in current_path.modules.items():
            if module["difficulty"] == "hard":
                plan.append({
                    "type": "downgrade_difficulty",
                    "module_id": module_id,
                    "module_title": module["title"],
                    "from_difficulty": "hard",
                    "to_difficulty": "medium",
                    "reason": "Reducing cognitive load"
                })
            elif module["difficulty"] == "medium" and weak_topics:
                # Only downgrade medium if there are weak topics
                plan.append({
                    "type": "downgrade_difficulty",
                    "module_id": module_id,
                    "module_title": module["title"],
                    "from_difficulty": "medium",
                    "to_difficulty": "easy",
                    "reason": "Supporting struggling topics"
                })
        
        # 2. Insert prerequisite review modules
        if weak_topics:
            plan.append({
                "type": "insert_prerequisite_review",
                "weak_topics": weak_topics,
                "reason": "Reinforcing foundational concepts"
            })
        
        # 3. Increase time allocation
        plan.append({
            "type": "adjust_pacing",
            "pacing_change": "+25%",
            "reason": "Allowing more time for concept mastery"
        })
        
        # 4. Add practice modules
        if student_metrics.get("quiz_accuracy", 100) < 60:
            plan.append({
                "type": "insert_practice_module",
                "reason": "Additional practice needed for concept reinforcement"
            })
        
        return plan
    
    def _generate_difficulty_increase_plan(
        self,
        current_path: LearningPathGraph,
        student_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate plan to increase difficulty"""
        plan = []
        
        # 1. Upgrade module difficulties
        for module_id, module in current_path.modules.items():
            if module["difficulty"] == "easy":
                plan.append({
                    "type": "upgrade_difficulty",
                    "module_id": module_id,
                    "module_title": module["title"],
                    "from_difficulty": "easy",
                    "to_difficulty": "medium",
                    "reason": "Student ready for increased challenge"
                })
            elif module["difficulty"] == "medium" and student_metrics.get("quiz_accuracy", 0) > 90:
                plan.append({
                    "type": "upgrade_difficulty",
                    "module_id": module_id,
                    "module_title": module["title"],
                    "from_difficulty": "medium",
                    "to_difficulty": "hard",
                    "reason": "Exceptional performance - advancing complexity"
                })
        
        # 2. Skip redundant review modules
        for module_id, module in current_path.modules.items():
            if module["moduleType"] == "review" and module.get("isOptional"):
                plan.append({
                    "type": "skip_module",
                    "module_id": module_id,
                    "module_title": module["title"],
                    "reason": "Review not needed - strong foundational knowledge"
                })
        
        # 3. Accelerate pacing
        plan.append({
            "type": "adjust_pacing",
            "pacing_change": "-15%",
            "reason": "Student demonstrating strong comprehension - accelerating pace"
        })
        
        return plan
    
    def estimate_impact(self, adjustment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict the impact of a proposed adjustment.
        
        Args:
            adjustment: Adjustment action dict
        
        Returns:
            Impact estimation with expected outcomes
        """
        adjustment_type = adjustment["type"]
        
        impact = {
            "expected_cognitive_load_change": 0,
            "expected_time_change_minutes": 0,
            "expected_success_rate_change": 0,
            "risk_level": "low"
        }
        
        if adjustment_type == "downgrade_difficulty":
            impact["expected_cognitive_load_change"] = -10
            impact["expected_success_rate_change"] = +15
            impact["risk_level"] = "low"
            
        elif adjustment_type == "upgrade_difficulty":
            impact["expected_cognitive_load_change"] = +15
            impact["expected_success_rate_change"] = -5
            impact["risk_level"] = "medium"
            
        elif adjustment_type == "insert_prerequisite_review":
            impact["expected_cognitive_load_change"] = -5
            impact["expected_time_change_minutes"] = +30
            impact["expected_success_rate_change"] = +10
            impact["risk_level"] = "low"
            
        elif adjustment_type == "adjust_pacing":
            pacing_change = adjustment.get("pacing_change", "0%")
            if "+" in pacing_change:
                impact["expected_time_change_minutes"] = +45
                impact["expected_success_rate_change"] = +5
            elif "-" in pacing_change:
                impact["expected_time_change_minutes"] = -30
                impact["expected_cognitive_load_change"] = +5
            
        elif adjustment_type == "insert_practice_module":
            impact["expected_time_change_minutes"] = +20
            impact["expected_success_rate_change"] = +12
            impact["risk_level"] = "low"
            
        elif adjustment_type == "skip_module":
            impact["expected_time_change_minutes"] = -15
            impact["risk_level"] = "medium"
        
        return impact
    
    @staticmethod
    def _get_difficulty_value(difficulty: str) -> int:
        """Convert difficulty string to numeric value"""
        return {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
    
    @staticmethod
    def _infer_path_difficulty(learning_graph: LearningPathGraph) -> str:
        """Infer overall difficulty from learning path"""
        if not learning_graph.modules:
            return "medium"
        
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        for module in learning_graph.modules.values():
            difficulty_counts[module.get("difficulty", "medium")] += 1
        
        # Return the most common difficulty
        return max(difficulty_counts, key=difficulty_counts.get)
