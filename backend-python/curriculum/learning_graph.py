"""
Learning Path Graph Implementation

Builds a directed acyclic graph (DAG) representation of learning paths
with modules as nodes and prerequisites as edges.
"""

from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
from config.database import get_async_db
from sqlalchemy import text
import logging


class LearningPathGraph:
    """Graph representation of a learning path with prerequisite relationships"""
    
    def __init__(self, learning_path_id: str):
        self.learning_path_id = learning_path_id
        self.modules: Dict[str, Dict[str, Any]] = {}
        self.prerequisites: Dict[str, List[str]] = defaultdict(list)
        self.dependents: Dict[str, List[str]] = defaultdict(list)
        self.logger = logging.getLogger(f"LearningPathGraph:{learning_path_id}")
    
    async def load_learning_path(self):
        """
        Load learning path and modules from PostgreSQL.
        Builds the graph structure with prerequisite relationships.
        """
        try:
            async for db in get_async_db():
                # Fetch all modules for this learning path
                query = text("""
                    SELECT 
                        id, title, content, difficulty, 
                        "moduleType", "estimatedMinutes", "orderIndex",
                        prerequisites, "createdAt", "updatedAt"
                    FROM content_modules
                    WHERE "learningPathId" = :path_id
                    ORDER BY "orderIndex"
                """)
                
                result = await db.execute(query, {"path_id": self.learning_path_id})
                rows = result.fetchall()
                
                # Build module dict and prerequisite graph
                for row in rows:
                    module_id = row[0]
                    self.modules[module_id] = {
                        "id": module_id,
                        "title": row[1],
                        "description": row[2][:200] if row[2] else "",  # Use content as description (truncated)
                        "difficulty": row[3],
                        "moduleType": row[4],
                        "estimatedMinutes": row[5],
                        "orderIndex": row[6],
                        "prerequisites": row[7] or [],
                        "isOptional": False  # Schema doesn't have isOptional, default to False
                    }
                    
                    # Build prerequisite relationships
                    prereqs = row[7] or []
                    self.prerequisites[module_id] = prereqs
                    for prereq in prereqs:
                        self.dependents[prereq].append(module_id)
                
                self.logger.info(f"Loaded {len(self.modules)} modules with prerequisite graph")
                break
                
        except Exception as e:
            self.logger.error(f"Error loading learning path: {str(e)}")
            raise
    
    def get_available_modules(self, completed_modules: List[str]) -> List[Dict[str, Any]]:
        """
        Get modules that can be started based on completed prerequisites.
        
        Args:
            completed_modules: List of completed module IDs
            
        Returns:
            List of available module dictionaries
        """
        completed_set = set(completed_modules)
        available = []
        
        for module_id, module in self.modules.items():
            # Skip if already completed
            if module_id in completed_set:
                continue
            
            # Check if all prerequisites are met
            prereqs = self.prerequisites[module_id]
            if all(prereq in completed_set for prereq in prereqs):
                available.append(module)
        
        # Sort by order index
        available.sort(key=lambda m: m["orderIndex"])
        return available
    
    def find_easier_alternatives(self, module_id: str, max_difficulty: str) -> List[Dict[str, Any]]:
        """
        Find alternative modules with lower difficulty that cover similar concepts.
        
        Args:
            module_id: ID of the difficult module
            max_difficulty: Maximum allowed difficulty level
            
        Returns:
            List of alternative modules
        """
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        max_level = difficulty_order.get(max_difficulty, 1)
        
        if module_id not in self.modules:
            return []
        
        target_module = self.modules[module_id]
        target_type = target_module["moduleType"]
        
        # Find modules with same type but lower difficulty
        alternatives = []
        for mid, module in self.modules.items():
            if mid == module_id:
                continue
            
            if (module["moduleType"] == target_type and 
                difficulty_order.get(module["difficulty"], 999) <= max_level):
                alternatives.append(module)
        
        # Sort by difficulty (easiest first)
        alternatives.sort(key=lambda m: difficulty_order.get(m["difficulty"], 999))
        return alternatives
    
    def get_prerequisite_review_modules(self, module_id: str) -> List[Dict[str, Any]]:
        """
        Get all prerequisite modules that should be reviewed before attempting a module.
        
        Args:
            module_id: ID of the target module
            
        Returns:
            List of prerequisite modules in order
        """
        if module_id not in self.prerequisites:
            return []
        
        # BFS to get all transitive prerequisites
        prereq_chain = []
        visited = set()
        queue = deque(self.prerequisites[module_id])
        
        while queue:
            prereq_id = queue.popleft()
            if prereq_id in visited or prereq_id not in self.modules:
                continue
            
            visited.add(prereq_id)
            prereq_chain.append(self.modules[prereq_id])
            
            # Add prerequisites of this prerequisite
            for sub_prereq in self.prerequisites[prereq_id]:
                if sub_prereq not in visited:
                    queue.append(sub_prereq)
        
        # Sort by order index (foundation first)
        prereq_chain.sort(key=lambda m: m["orderIndex"])
        return prereq_chain
    
    def calculate_path_difficulty(self) -> float:
        """
        Calculate aggregate difficulty score for the entire path.
        
        Returns:
            Difficulty score (0-100)
        """
        if not self.modules:
            return 0.0
        
        difficulty_weights = {"easy": 25, "medium": 50, "hard": 75}
        total_score = sum(
            difficulty_weights.get(module["difficulty"], 50) 
            for module in self.modules.values()
        )
        
        return round(total_score / len(self.modules), 2)
    
    def validate_path_integrity(self) -> bool:
        """
        Validate that the learning path is a valid DAG with no circular dependencies.
        
        Returns:
            True if path is valid
        """
        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(module_id: str) -> bool:
            visited.add(module_id)
            rec_stack.add(module_id)
            
            for dependent in self.dependents[module_id]:
                if dependent not in visited:
                    if has_cycle(dependent):
                        return True
                elif dependent in rec_stack:
                    return True
            
            rec_stack.remove(module_id)
            return False
        
        # Check each module
        for module_id in self.modules:
            if module_id not in visited:
                if has_cycle(module_id):
                    self.logger.error(f"Circular dependency detected involving module {module_id}")
                    return False
        
        # Check for orphaned nodes (modules with prerequisites not in path)
        for module_id, prereqs in self.prerequisites.items():
            for prereq in prereqs:
                if prereq not in self.modules:
                    self.logger.warning(f"Module {module_id} has missing prerequisite {prereq}")
                    return False
        
        return True
    
    def get_next_modules(self, completed_modules: List[str], count: int = 3) -> List[Dict[str, Any]]:
        """
        Get the next recommended modules to study.
        
        Args:
            completed_modules: List of completed module IDs
            count: Number of modules to recommend
            
        Returns:
            List of recommended modules
        """
        available = self.get_available_modules(completed_modules)
        return available[:count]
    
    def find_alternative_paths(self, current_module_id: str, completed_modules: List[str]) -> List[List[str]]:
        """
        Find alternative learning sequences from current position.
        
        Args:
            current_module_id: Current module ID
            completed_modules: Completed module IDs
            
        Returns:
            List of alternative module sequences
        """
        completed_set = set(completed_modules)
        paths = []
        
        # Get all modules that can be studied next
        available = self.get_available_modules(list(completed_set))
        
        for module in available:
            if module["id"] == current_module_id:
                continue
            
            # Build a path from this alternative
            path = [module["id"]]
            temp_completed = completed_set.copy()
            temp_completed.add(module["id"])
            
            # Get next 2-3 modules in this path
            for _ in range(3):
                next_modules = self.get_available_modules(list(temp_completed))
                if not next_modules:
                    break
                path.append(next_modules[0]["id"])
                temp_completed.add(next_modules[0]["id"])
            
            paths.append(path)
        
        return paths[:3]  # Return top 3 alternative paths


class ConceptDependencyAnalyzer:
    """Analyzes prerequisite relationships and identifies critical path modules"""
    
    def __init__(self, learning_graph: LearningPathGraph):
        self.graph = learning_graph
        self.logger = logging.getLogger("ConceptDependencyAnalyzer")
    
    def analyze_prerequisite_relationships(self) -> Dict[str, Any]:
        """
        Analyze the complexity of prerequisite relationships.
        
        Returns:
            Analysis dict with critical path, bottlenecks, complexity scores
        """
        analysis = {
            "total_modules": len(self.graph.modules),
            "avg_prerequisites": 0,
            "max_prerequisite_depth": 0,
            "bottleneck_modules": [],
            "critical_path": []
        }
        
        if not self.graph.modules:
            return analysis
        
        # Calculate average prerequisites
        total_prereqs = sum(len(prereqs) for prereqs in self.graph.prerequisites.values())
        analysis["avg_prerequisites"] = round(total_prereqs / len(self.graph.modules), 2)
        
        # Find maximum prerequisite depth
        max_depth = 0
        for module_id in self.graph.modules:
            depth = self._calculate_prerequisite_depth(module_id)
            max_depth = max(max_depth, depth)
        analysis["max_prerequisite_depth"] = max_depth
        
        # Identify bottleneck modules (modules that block many dependents)
        bottlenecks = []
        for module_id, dependents in self.graph.dependents.items():
            if len(dependents) >= 3:
                bottlenecks.append({
                    "module_id": module_id,
                    "title": self.graph.modules[module_id]["title"],
                    "dependent_count": len(dependents)
                })
        analysis["bottleneck_modules"] = sorted(bottlenecks, key=lambda x: x["dependent_count"], reverse=True)
        
        # Calculate critical path (longest dependency chain)
        analysis["critical_path"] = self._find_critical_path()
        
        return analysis
    
    def _calculate_prerequisite_depth(self, module_id: str, visited: Optional[Set[str]] = None) -> int:
        """Calculate the maximum depth of prerequisites for a module"""
        if visited is None:
            visited = set()
        
        if module_id in visited or module_id not in self.graph.modules:
            return 0
        
        visited.add(module_id)
        prereqs = self.graph.prerequisites[module_id]
        
        if not prereqs:
            return 0
        
        max_depth = 0
        for prereq in prereqs:
            depth = self._calculate_prerequisite_depth(prereq, visited.copy())
            max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    def _find_critical_path(self) -> List[str]:
        """Find the longest dependency chain in the graph"""
        longest_path = []
        
        for module_id in self.graph.modules:
            path = self._get_longest_path_from_module(module_id)
            if len(path) > len(longest_path):
                longest_path = path
        
        return longest_path
    
    def _get_longest_path_from_module(self, module_id: str) -> List[str]:
        """Get longest path starting from a specific module"""
        prereqs = self.graph.prerequisites[module_id]
        
        if not prereqs:
            return [module_id]
        
        longest = []
        for prereq in prereqs:
            path = self._get_longest_path_from_module(prereq)
            if len(path) > len(longest):
                longest = path
        
        return longest + [module_id]
    
    def calculate_module_difficulty_scores(self) -> Dict[str, float]:
        """
        Calculate difficulty scores based on prerequisite complexity.
        
        Returns:
            Dict mapping module_id to difficulty score (0-100)
        """
        difficulty_map = {"easy": 25, "medium": 50, "hard": 75}
        scores = {}
        
        for module_id, module in self.graph.modules.items():
            base_difficulty = difficulty_map.get(module["difficulty"], 50)
            prereq_depth = self._calculate_prerequisite_depth(module_id)
            prereq_count = len(self.graph.prerequisites[module_id])
            
            # Adjust score based on prerequisites
            complexity_factor = (prereq_depth * 5) + (prereq_count * 3)
            final_score = min(base_difficulty + complexity_factor, 100)
            
            scores[module_id] = round(final_score, 2)
        
        return scores
    
    def identify_bottleneck_concepts(self) -> List[Dict[str, Any]]:
        """
        Identify modules that block multiple downstream modules.
        
        Returns:
            List of bottleneck modules with impact analysis
        """
        bottlenecks = []
        
        for module_id, dependents in self.graph.dependents.items():
            if len(dependents) >= 2:
                # Calculate transitive impact
                total_blocked = self._count_transitive_dependents(module_id)
                
                bottlenecks.append({
                    "module_id": module_id,
                    "title": self.graph.modules[module_id]["title"],
                    "difficulty": self.graph.modules[module_id]["difficulty"],
                    "direct_dependents": len(dependents),
                    "total_blocked_modules": total_blocked,
                    "impact_score": total_blocked * 10
                })
        
        return sorted(bottlenecks, key=lambda x: x["impact_score"], reverse=True)
    
    def _count_transitive_dependents(self, module_id: str, visited: Optional[Set[str]] = None) -> int:
        """Count all modules that transitively depend on this module"""
        if visited is None:
            visited = set()
        
        if module_id in visited:
            return 0
        
        visited.add(module_id)
        count = len(self.graph.dependents[module_id])
        
        for dependent in self.graph.dependents[module_id]:
            count += self._count_transitive_dependents(dependent, visited)
        
        return count
    
    def generate_alternative_sequences(self, start_module_id: str, target_count: int = 5) -> List[List[str]]:
        """
        Generate alternative learning sequences starting from a specific module.
        
        Args:
            start_module_id: Starting module ID
            target_count: Number of modules in each sequence
            
        Returns:
            List of alternative module sequences
        """
        sequences = []
        completed = set()
        
        # Generate multiple sequences
        for _ in range(3):
            sequence = [start_module_id]
            temp_completed = completed.copy()
            temp_completed.add(start_module_id)
            
            while len(sequence) < target_count:
                available = self.graph.get_available_modules(list(temp_completed))
                if not available:
                    break
                
                # Pick next module (prioritize different choices for variety)
                next_module = available[len(sequences) % len(available)]
                sequence.append(next_module["id"])
                temp_completed.add(next_module["id"])
            
            sequences.append(sequence)
        
        return sequences


async def load_learning_path(learning_path_id: str) -> LearningPathGraph:
    """
    Factory function to load and initialize a learning path graph.
    
    Args:
        learning_path_id: Learning path identifier
        
    Returns:
        Initialized LearningPathGraph instance
    """
    graph = LearningPathGraph(learning_path_id)
    await graph.load_learning_path()
    return graph
