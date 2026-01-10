"""
Concept Reshuffler Implementation

Handles reordering and substitution of modules based on learning patterns,
weak topics, and cognitive load signals.
"""

from typing import Dict, Any, List, Set
from curriculum.learning_graph import LearningPathGraph
import logging


class ConceptReshuffler:
    """Manages module reordering and substitution strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger("ConceptReshuffler")
    
    def identify_struggling_topics(
        self,
        weak_topics: List[str],
        learning_graph: LearningPathGraph
    ) -> List[str]:
        """
        Map weak topic names to module IDs in the learning path.
        
        Args:
            weak_topics: List of weak topic names from performance analysis
            learning_graph: Learning path graph structure
        
        Returns:
            List of module IDs corresponding to weak topics
        """
        struggling_module_ids = []
        
        for module_id, module in learning_graph.modules.items():
            module_title = module["title"].lower()
            module_desc = module.get("description", "").lower()
            
            # Check if any weak topic appears in module title or description
            for topic in weak_topics:
                topic_lower = topic.lower()
                if topic_lower in module_title or topic_lower in module_desc:
                    struggling_module_ids.append(module_id)
                    break
        
        self.logger.info(f"Identified {len(struggling_module_ids)} struggling modules from {len(weak_topics)} weak topics")
        return struggling_module_ids
    
    def generate_prerequisite_chain(
        self,
        module_id: str,
        learning_graph: LearningPathGraph
    ) -> List[str]:
        """
        Build a review sequence of prerequisite modules.
        
        Args:
            module_id: Target module ID
            learning_graph: Learning path graph structure
        
        Returns:
            Ordered list of prerequisite module IDs
        """
        if module_id not in learning_graph.modules:
            return []
        
        # Get all prerequisites using graph method
        prereq_modules = learning_graph.get_prerequisite_review_modules(module_id)
        
        # Return just the IDs in order
        return [m["id"] for m in prereq_modules]
    
    def reorder_modules(
        self,
        current_order: List[str],
        constraints: Dict[str, Any]
    ) -> List[str]:
        """
        Optimize module sequence based on constraints.
        
        Args:
            current_order: Current module sequence (list of module IDs)
            constraints: Dict with learning_graph, struggling_modules, target_difficulty
        
        Returns:
            Reordered list of module IDs
        """
        learning_graph: LearningPathGraph = constraints["learning_graph"]
        struggling_modules: Set[str] = set(constraints.get("struggling_modules", []))
        target_difficulty: str = constraints.get("target_difficulty", "medium")
        
        # Strategy: Move easier modules earlier, harder modules later
        # Preserve prerequisite relationships
        
        new_order = []
        remaining = set(current_order)
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        target_diff_value = difficulty_order.get(target_difficulty, 1)
        
        # Build dependency-aware ordering
        while remaining:
            # Find modules that can be added (prerequisites met)
            available = []
            for module_id in remaining:
                prereqs = learning_graph.prerequisites.get(module_id, [])
                if all(p in new_order or p not in current_order for p in prereqs):
                    available.append(module_id)
            
            if not available:
                # Deadlock - add remaining in original order
                new_order.extend(sorted(remaining, key=lambda x: current_order.index(x)))
                break
            
            # Sort available by priority
            def priority_key(mid):
                module = learning_graph.modules.get(mid, {})
                diff_value = difficulty_order.get(module.get("difficulty", "medium"), 1)
                
                # Prioritize easier modules when reducing difficulty
                if target_diff_value == 0:  # easy
                    return (diff_value, mid in struggling_modules)
                # Prioritize harder modules when increasing difficulty
                elif target_diff_value == 2:  # hard
                    return (-diff_value, mid not in struggling_modules)
                # Balanced approach for medium
                else:
                    return (diff_value, mid in struggling_modules)
            
            available.sort(key=priority_key)
            
            # Add the highest priority module
            next_module = available[0]
            new_order.append(next_module)
            remaining.remove(next_module)
        
        return new_order
    
    def find_module_substitutes(
        self,
        module_id: str,
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find alternative modules that can replace a difficult module.
        
        Args:
            module_id: ID of module to replace
            criteria: Dict with learning_graph, max_difficulty, module_type
        
        Returns:
            List of substitute module dicts
        """
        learning_graph: LearningPathGraph = criteria["learning_graph"]
        max_difficulty: str = criteria.get("max_difficulty", "medium")
        required_type: str = criteria.get("module_type")
        
        if module_id not in learning_graph.modules:
            return []
        
        target_module = learning_graph.modules[module_id]
        substitutes = []
        
        # Find modules with similar characteristics but easier
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        max_diff_value = difficulty_order.get(max_difficulty, 1)
        
        for mid, module in learning_graph.modules.items():
            if mid == module_id:
                continue
            
            # Check difficulty constraint
            if difficulty_order.get(module["difficulty"], 2) > max_diff_value:
                continue
            
            # Check module type if specified
            if required_type and module["moduleType"] != required_type:
                continue
            
            # Check if covers similar content (basic heuristic)
            if module["moduleType"] == target_module["moduleType"]:
                substitutes.append({
                    "module_id": mid,
                    "title": module["title"],
                    "difficulty": module["difficulty"],
                    "estimatedMinutes": module["estimatedMinutes"],
                    "similarity_score": self._calculate_similarity(target_module, module)
                })
        
        # Sort by similarity and difficulty (prefer easier)
        substitutes.sort(
            key=lambda x: (
                -x["similarity_score"],
                difficulty_order.get(x["difficulty"], 1)
            )
        )
        
        return substitutes[:3]  # Return top 3 substitutes
    
    def calculate_pacing_adjustment(
        self,
        cognitive_load_history: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate time allocation adjustments based on cognitive load patterns.
        
        Args:
            cognitive_load_history: List of recent cognitive load scores
        
        Returns:
            Pacing adjustment dict with time_multiplier and reasoning
        """
        if not cognitive_load_history:
            return {
                "time_multiplier": 1.0,
                "adjustment_percentage": "0%",
                "reasoning": "No cognitive load history available"
            }
        
        avg_load = sum(cognitive_load_history) / len(cognitive_load_history)
        
        # Analyze trend
        if len(cognitive_load_history) >= 3:
            recent_avg = sum(cognitive_load_history[-3:]) / 3
            older_avg = sum(cognitive_load_history[:-3]) / max(len(cognitive_load_history) - 3, 1)
            trend = "increasing" if recent_avg > older_avg + 5 else "stable" if abs(recent_avg - older_avg) <= 5 else "decreasing"
        else:
            trend = "stable"
        
        # Determine pacing adjustment
        if avg_load > 80:
            multiplier = 1.4
            adjustment = "+40%"
            reasoning = f"High average cognitive load ({avg_load:.1f}) - significantly increasing time allocation"
        elif avg_load > 70:
            multiplier = 1.25
            adjustment = "+25%"
            reasoning = f"Elevated cognitive load ({avg_load:.1f}) - increasing time allocation"
        elif avg_load < 30 and trend == "decreasing":
            multiplier = 0.85
            adjustment = "-15%"
            reasoning = f"Low cognitive load ({avg_load:.1f}) with declining trend - can accelerate pace"
        elif avg_load < 40:
            multiplier = 0.90
            adjustment = "-10%"
            reasoning = f"Low cognitive load ({avg_load:.1f}) - moderate pace increase"
        else:
            multiplier = 1.0
            adjustment = "0%"
            reasoning = f"Balanced cognitive load ({avg_load:.1f}) - maintaining current pace"
        
        return {
            "time_multiplier": round(multiplier, 2),
            "adjustment_percentage": adjustment,
            "reasoning": reasoning,
            "avg_cognitive_load": round(avg_load, 2),
            "trend": trend
        }
    
    def validate_reshuffled_path(
        self,
        new_order: List[str],
        learning_graph: LearningPathGraph
    ) -> bool:
        """
        Ensure prerequisite relationships are satisfied in new order.
        
        Args:
            new_order: Proposed new module sequence
            learning_graph: Learning path graph structure
        
        Returns:
            True if order is valid
        """
        seen_modules = set()
        
        for module_id in new_order:
            if module_id not in learning_graph.modules:
                self.logger.error(f"Module {module_id} not found in learning graph")
                return False
            
            # Check if all prerequisites have been seen
            prereqs = learning_graph.prerequisites.get(module_id, [])
            for prereq in prereqs:
                if prereq in learning_graph.modules and prereq not in seen_modules:
                    self.logger.error(
                        f"Module {module_id} appears before prerequisite {prereq}"
                    )
                    return False
            
            seen_modules.add(module_id)
        
        return True
    
    def generate_reshuffling_plan(
        self,
        learning_graph: LearningPathGraph,
        student_metrics: Dict[str, Any],
        current_module_id: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive reshuffling plan based on student needs.
        
        Args:
            learning_graph: Learning path graph structure
            student_metrics: Performance and engagement metrics
            current_module_id: Current student position
        
        Returns:
            Reshuffling plan with actions and rationale
        """
        plan = {
            "actions": [],
            "rationale": [],
            "estimated_impact": {}
        }
        
        weak_topics = student_metrics.get("weak_topics", [])
        cognitive_load = student_metrics.get("cognitive_load_score", 50)
        
        # 1. Identify struggling modules
        if weak_topics:
            struggling_ids = self.identify_struggling_topics(weak_topics, learning_graph)
            
            if struggling_ids:
                plan["actions"].append({
                    "type": "prerequisite_injection",
                    "struggling_modules": struggling_ids,
                    "weak_topics": weak_topics
                })
                plan["rationale"].append(
                    f"Inserting prerequisite review for {len(weak_topics)} weak topics"
                )
        
        # 2. Reorder based on difficulty
        if cognitive_load > 75:
            plan["actions"].append({
                "type": "move_difficult_concepts_later",
                "reason": "High cognitive load detected"
            })
            plan["rationale"].append(
                "Postponing advanced concepts to reduce immediate cognitive burden"
            )
        
        # 3. Pacing adjustment
        cognitive_history = student_metrics.get("cognitive_load_history", [cognitive_load])
        pacing = self.calculate_pacing_adjustment(cognitive_history)
        
        if pacing["time_multiplier"] != 1.0:
            plan["actions"].append({
                "type": "adjust_pacing",
                "time_multiplier": pacing["time_multiplier"],
                "adjustment": pacing["adjustment_percentage"]
            })
            plan["rationale"].append(pacing["reasoning"])
        
        # 4. Insert review modules
        if student_metrics.get("quiz_accuracy", 100) < 60:
            plan["actions"].append({
                "type": "insert_review_modules",
                "reason": "Low quiz accuracy requires reinforcement"
            })
            plan["rationale"].append(
                "Adding review modules to strengthen foundational understanding"
            )
        
        # 5. Alternative path suggestion
        if student_metrics.get("plateau_detected", False):
            alternatives = learning_graph.find_alternative_paths(
                current_module_id,
                student_metrics.get("completed_modules", [])
            )
            
            if alternatives:
                plan["actions"].append({
                    "type": "suggest_alternative_path",
                    "alternatives": alternatives[:2]
                })
                plan["rationale"].append(
                    "Learning plateau detected - suggesting alternative learning sequences"
                )
        
        return plan
    
    @staticmethod
    def _calculate_similarity(module1: Dict[str, Any], module2: Dict[str, Any]) -> float:
        """Calculate similarity score between two modules"""
        score = 0.0
        
        # Same module type
        if module1["moduleType"] == module2["moduleType"]:
            score += 0.5
        
        # Similar difficulty
        if module1["difficulty"] == module2["difficulty"]:
            score += 0.2
        
        # Similar estimated time
        time1 = module1.get("estimatedMinutes", 0)
        time2 = module2.get("estimatedMinutes", 0)
        if time1 and time2:
            time_diff = abs(time1 - time2)
            if time_diff < 10:
                score += 0.3
            elif time_diff < 20:
                score += 0.15
        
        return score
