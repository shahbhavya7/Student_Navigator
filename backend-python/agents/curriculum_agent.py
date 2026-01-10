"""
Comprehensive Curriculum Agent

Orchestrates dynamic curriculum adaptation based on cognitive load,
performance metrics, and engagement patterns.
"""

from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from agents.state import AgentState
from curriculum.learning_graph import load_learning_path, LearningPathGraph
from curriculum.difficulty_adjuster import DifficultyAdjuster
from curriculum.concept_reshuffler import ConceptReshuffler
from curriculum.state_manager import CurriculumStateManager
from content.generator import ContentGenerator
from content.content_storage import ContentStorageService
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import logging


class CurriculumAgent(BaseAgent):
    """Agent for dynamic curriculum adaptation and optimization"""
    
    # Adjustment thresholds
    COGNITIVE_LOAD_ADJUSTMENT_THRESHOLD = 70
    PERFORMANCE_ADJUSTMENT_THRESHOLD = 60
    MAJOR_ADJUSTMENT_CONFIDENCE = 0.85
    
    def __init__(self, name: str = "curriculum_agent"):
        super().__init__(name)
        self.difficulty_adjuster = DifficultyAdjuster()
        self.concept_reshuffler = ConceptReshuffler()
        self.state_manager = CurriculumStateManager()
        self.content_generator = ContentGenerator()
        self.content_storage = ContentStorageService()
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)
        self.logger = logging.getLogger(name)
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute curriculum adaptation logic.
        
        Args:
            state: Current agent state with student metrics
        
        Returns:
            Dict with curriculum adjustments and rationale
        """
        try:
            # Extract data from state - handle both nested (dict) and flat formats
            student_id = state.get("student_id")
            
            # Handle learning_path_id or current_learning_path_id from orchestrator
            learning_path_id = state.get("learning_path_id") or state.get("current_learning_path_id")
            
            if not student_id or not learning_path_id:
                self.logger.warning(f"Missing student_id or learning_path_id in state. Keys: {list(state.keys())}")
                return self._get_default_output()
            
            # Gather student metrics - handle both nested dicts and flat top-level fields
            cognitive_load_data = state.get("cognitive_load", {})
            performance_data = state.get("performance_metrics", {})
            engagement_data = state.get("engagement_metrics", {})
            
            student_data = {
                "cognitive_load_score": (
                    cognitive_load_data.get("current_load") if isinstance(cognitive_load_data, dict)
                    else state.get("cognitive_load_score", 50)
                ),
                "mental_fatigue_level": (
                    cognitive_load_data.get("fatigue_level") if isinstance(cognitive_load_data, dict)
                    else state.get("mental_fatigue_level", "normal")
                ),
                "quiz_accuracy": (
                    performance_data.get("quiz_accuracy") if isinstance(performance_data, dict)
                    else state.get("quiz_accuracy", 0)
                ),
                "learning_velocity": (
                    performance_data.get("learning_velocity") if isinstance(performance_data, dict)
                    else state.get("learning_velocity", 0)
                ),
                "improvement_trend": (
                    performance_data.get("improvement_trend") if isinstance(performance_data, dict)
                    else state.get("improvement_trend", "stable")
                ),
                "weak_topics": (
                    performance_data.get("weak_topics") if isinstance(performance_data, dict)
                    else state.get("weak_topics", [])
                ),
                "plateau_detected": (
                    performance_data.get("plateau_detected") if isinstance(performance_data, dict)
                    else state.get("plateau_detected", False)
                ),
                "engagement_score": (
                    engagement_data.get("engagement_score") if isinstance(engagement_data, dict)
                    else state.get("engagement_score", 0)
                ),
                "dropout_risk": (
                    engagement_data.get("dropout_risk") if isinstance(engagement_data, dict)
                    else state.get("dropout_risk", 0)
                ),
                "completed_modules": state.get("completed_modules", []),
                "cognitive_load_history": state.get("cognitive_load_history", [])
            }
            
            # Load current curriculum state
            current_state = await self.state_manager.get_current_state(student_id, learning_path_id)
            current_module_id = current_state.get("current_module_id")
            current_difficulty = current_state.get("difficulty", "medium")
            
            # Load learning path graph
            learning_graph = await load_learning_path(learning_path_id)
            
            # Analyze adjustment needs
            adjustment_analysis = await self.analyze_adjustment_needs(student_data)
            
            if not adjustment_analysis["needs_adjustment"]:
                self.logger.info(f"No curriculum adjustment needed for {student_id}")
                return {
                    "curriculum_adjustments": [],
                    "difficulty_level": current_difficulty,
                    "current_module_id": current_module_id,
                    "adjustment_rationale": "Current curriculum is well-matched to student progress"
                }
            
            # Calculate target difficulty
            difficulty_analysis = self.difficulty_adjuster.calculate_target_difficulty(student_data)
            target_difficulty = difficulty_analysis["target_difficulty"]
            confidence = difficulty_analysis["confidence"]
            
            # Generate adjustment plan
            adjustments = await self.generate_adjustment_plan(
                student_data,
                learning_graph,
                current_difficulty,
                target_difficulty
            )
            
            # Generate LLM-powered rationale
            rationale = await self.generate_adjustment_rationale(
                adjustments,
                student_data,
                difficulty_analysis
            )
            
            # Apply adjustments if confidence is high enough
            if self.difficulty_adjuster.should_adjust_difficulty(
                current_difficulty,
                target_difficulty,
                confidence
            ):
                await self.apply_adjustments(learning_path_id, adjustments, rationale)
                
                # Invalidate cache to force refresh
                await self.state_manager.invalidate_cache(student_id, learning_path_id)
            
            # Publish curriculum update event
            await self.publish_event("curriculum_adjusted", {
                "student_id": student_id,
                "learning_path_id": learning_path_id,
                "adjustments": adjustments,
                "target_difficulty": target_difficulty,
                "confidence": confidence
            })
            
            return {
                "curriculum_adjustments": adjustments,
                "difficulty_level": target_difficulty,
                "current_module_id": current_module_id,
                "pacing_changes": self._extract_pacing_changes(adjustments),
                "adjustment_rationale": rationale,
                "adjustment_confidence": confidence
            }
        
        except Exception as e:
            self.logger.error(f"Error in curriculum agent: {str(e)}")
            return self._get_default_output()
    
    async def analyze_adjustment_needs(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if curriculum adjustments are needed.
        
        Args:
            student_data: Student metrics
        
        Returns:
            Analysis dict with needs_adjustment flag and reasons
        """
        needs_adjustment = False
        reasons = []
        urgency = "low"
        
        cognitive_load = student_data["cognitive_load_score"]
        quiz_accuracy = student_data["quiz_accuracy"]
        weak_topics = student_data["weak_topics"]
        plateau_detected = student_data["plateau_detected"]
        dropout_risk = student_data["dropout_risk"]
        
        # Check cognitive load
        if cognitive_load > self.COGNITIVE_LOAD_ADJUSTMENT_THRESHOLD:
            needs_adjustment = True
            urgency = "high"
            reasons.append(f"High cognitive load ({cognitive_load})")
        
        # Check performance
        if quiz_accuracy < self.PERFORMANCE_ADJUSTMENT_THRESHOLD:
            needs_adjustment = True
            urgency = "high" if urgency != "high" else urgency
            reasons.append(f"Low quiz accuracy ({quiz_accuracy}%)")
        
        # Check weak topics
        if len(weak_topics) >= 2:
            needs_adjustment = True
            reasons.append(f"{len(weak_topics)} weak topics identified")
        
        # Check plateau
        if plateau_detected:
            needs_adjustment = True
            reasons.append("Learning plateau detected")
        
        # Check dropout risk
        if dropout_risk > 0.6:
            needs_adjustment = True
            urgency = "critical"
            reasons.append(f"High dropout risk ({dropout_risk:.0%})")
        
        # Check for excellence (positive adjustment)
        if (cognitive_load < 30 and quiz_accuracy > 85 and 
            student_data["improvement_trend"] == "improving"):
            needs_adjustment = True
            urgency = "low"
            reasons.append("Opportunity to increase challenge level")
        
        return {
            "needs_adjustment": needs_adjustment,
            "urgency": urgency,
            "reasons": reasons
        }
    
    async def generate_adjustment_plan(
        self,
        student_data: Dict[str, Any],
        learning_graph: LearningPathGraph,
        current_difficulty: str,
        target_difficulty: str
    ) -> List[Dict[str, Any]]:
        """
        Create comprehensive adjustment plan.
        
        Args:
            student_data: Student metrics
            learning_graph: Learning path graph structure
            current_difficulty: Current difficulty level
            target_difficulty: Target difficulty level
        
        Returns:
            List of adjustment actions
        """
        adjustments = []
        
        # 1. Difficulty adjustments
        difficulty_adjustments = self.difficulty_adjuster.generate_adjustment_plan(
            learning_graph,
            target_difficulty,
            student_data
        )
        adjustments.extend(difficulty_adjustments)
        
        # 2. Concept reshuffling
        if student_data["weak_topics"] or student_data["cognitive_load_score"] > 70:
            reshuffling_plan = self.concept_reshuffler.generate_reshuffling_plan(
                learning_graph,
                student_data,
                student_data.get("current_module_id", "")
            )
            adjustments.extend(reshuffling_plan["actions"])
        
        # 3. Check if new content is needed
        missing_content = await self._generate_missing_content(
            adjustments,
            student_data,
            learning_graph.learning_path_id
        )
        if missing_content:
            adjustments.extend(missing_content)
        
        # 4. Add impact estimations
        for adjustment in adjustments:
            adjustment["estimated_impact"] = self.difficulty_adjuster.estimate_impact(adjustment)
        
        return adjustments
    
    async def apply_adjustments(
        self,
        learning_path_id: str,
        adjustments: List[Dict[str, Any]],
        rationale: str
    ) -> bool:
        """
        Execute curriculum adjustments in database.
        
        Args:
            learning_path_id: Learning path identifier
            adjustments: List of adjustment actions
            rationale: Explanation for adjustments
        
        Returns:
            True if successful
        """
        try:
            success = await self.state_manager.save_curriculum_adjustment(
                learning_path_id,
                adjustments,
                rationale
            )
            
            if success:
                self.logger.info(f"Applied {len(adjustments)} adjustments to {learning_path_id}")
            else:
                self.logger.error(f"Failed to apply adjustments to {learning_path_id}")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error applying adjustments: {str(e)}")
            return False
    
    async def generate_adjustment_rationale(
        self,
        adjustments: List[Dict[str, Any]],
        student_context: Dict[str, Any],
        difficulty_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate LLM-powered explanation for curriculum adjustments.
        
        Args:
            adjustments: List of planned adjustments
            student_context: Student metrics and state
            difficulty_analysis: Difficulty calculation results
        
        Returns:
            Personalized explanation text
        """
        try:
            system_message = SystemMessage(
                content="You are an adaptive learning specialist. Explain curriculum adjustments "
                        "to students in an encouraging, supportive tone. Focus on growth and learning success."
            )
            
            # Build context for LLM
            adjustment_summary = []
            for adj in adjustments[:5]:  # Limit to top 5 for clarity
                adj_type = adj.get("type", "unknown")
                if adj_type == "downgrade_difficulty":
                    adjustment_summary.append(
                        f"- Simplifying {adj.get('module_title', 'module')} to reduce cognitive load"
                    )
                elif adj_type == "upgrade_difficulty":
                    adjustment_summary.append(
                        f"- Advancing {adj.get('module_title', 'module')} to match your progress"
                    )
                elif adj_type == "insert_prerequisite_review":
                    adjustment_summary.append(
                        f"- Adding review modules for {', '.join(adj.get('weak_topics', []))}"
                    )
                elif adj_type == "adjust_pacing":
                    adjustment_summary.append(
                        f"- Adjusting study pace by {adj.get('pacing_change', '0%')}"
                    )
                elif adj_type == "content_generated":
                    action = adj.get('action', '')
                    if action == 'recap_inserted':
                        adjustment_summary.append(
                            f"- Created personalized review materials for {', '.join(adj.get('topics', []))}"
                        )
                    elif action == 'simplified_content':
                        adjustment_summary.append(
                            f"- Generated simplified version of current content"
                        )
                    elif action == 'advanced_content':
                        adjustment_summary.append(
                            f"- Created advanced version to challenge your skills"
                        )
            
            human_message = HumanMessage(
                content=f"""Generate a supportive explanation for these curriculum adjustments:

Student Context:
- Cognitive Load: {student_context['cognitive_load_score']}/100
- Quiz Accuracy: {student_context['quiz_accuracy']}%
- Learning Velocity: {student_context['learning_velocity']:.1f}
- Engagement: {student_context['engagement_score']}/100
- Weak Topics: {', '.join(student_context['weak_topics']) if student_context['weak_topics'] else 'None'}
- Improvement Trend: {student_context['improvement_trend']}

Recommended Adjustments:
{chr(10).join(adjustment_summary) if adjustment_summary else '- Maintaining current curriculum'}

Target Difficulty: {difficulty_analysis['target_difficulty']}
Reasoning: {', '.join(difficulty_analysis['reasoning'])}

Provide a brief (2-3 sentences) personalized explanation that:
1. Acknowledges the student's current progress
2. Explains why these adjustments will help
3. Encourages continued learning

Be warm, supportive, and focus on growth mindset."""
            )
            
            response = await self.llm.ainvoke([system_message, human_message])
            return response.content.strip()
        
        except Exception as e:
            self.logger.error(f"LLM rationale generation failed: {str(e)}")
            # Fallback to template-based rationale
            return self._generate_template_rationale(adjustments, student_context)
    
    def _generate_template_rationale(
        self,
        adjustments: List[Dict[str, Any]],
        student_context: Dict[str, Any]
    ) -> str:
        """Generate fallback rationale without LLM"""
        if not adjustments:
            return "Your current learning path is well-matched to your progress. Keep up the great work!"
        
        cognitive_load = student_context["cognitive_load_score"]
        quiz_accuracy = student_context["quiz_accuracy"]
        
        if cognitive_load > 70:
            return (
                f"We've noticed your cognitive load is elevated ({cognitive_load}/100). "
                "We're adjusting your curriculum to include more foundational review and "
                "reducing difficulty to help you master concepts at a comfortable pace."
            )
        elif quiz_accuracy < 60:
            return (
                f"Your recent quiz performance ({quiz_accuracy}%) suggests we should reinforce "
                "some key concepts. We've added review modules and adjusted difficulty to "
                "ensure you build a strong foundation before advancing."
            )
        elif quiz_accuracy > 85 and cognitive_load < 40:
            return (
                "You're doing exceptionally well! We're increasing the challenge level and "
                "introducing more advanced concepts to keep you engaged and accelerate your learning."
            )
        else:
            return (
                "We're fine-tuning your learning path based on your progress patterns. "
                "These adjustments will help optimize your learning experience and outcomes."
            )
    
    def _calculate_adjustment_confidence(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate confidence score for curriculum adjustments.
        
        Args:
            metrics: Student metrics
        
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence with clear signals
        cognitive_load = metrics.get("cognitive_load_score", 50)
        if cognitive_load > 80 or cognitive_load < 20:
            confidence += 0.2
        
        quiz_accuracy = metrics.get("quiz_accuracy", 0)
        if quiz_accuracy < 40 or quiz_accuracy > 90:
            confidence += 0.2
        
        if metrics.get("plateau_detected"):
            confidence += 0.15
        
        if len(metrics.get("weak_topics", [])) >= 3:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _generate_missing_content(
        self,
        adjustments: List[Dict[str, Any]],
        student_data: Dict[str, Any],
        learning_path_id: str
    ) -> List[Dict[str, Any]]:
        """
        Generate content for gaps in learning path or difficulty adjustments.
        
        Args:
            adjustments: Planned adjustments
            student_data: Student metrics
            learning_path_id: Learning path ID
        
        Returns:
            List of content generation adjustments
        """
        content_adjustments = []
        
        cognitive_load_profile = {
            'current_score': student_data.get('cognitive_load_score', 50),
            'fatigue_level': student_data.get('mental_fatigue_level', 'normal')
        }
        
        for adjustment in adjustments:
            adjustment_type = adjustment.get('type')
            
            # Downgrade difficulty: generate easier version
            if adjustment_type == 'downgrade_difficulty':
                module_id = adjustment.get('module_id')
                if module_id:
                    try:
                        # Get original module
                        original_module = await self.content_storage.get_content_by_id(module_id)
                        if original_module:
                            # Generate easier version
                            from content.content_variations import ContentVariationGenerator
                            variation_gen = ContentVariationGenerator()
                            easier_content = await variation_gen.generate_easier_version(
                                original_module['content'],
                                cognitive_load_profile
                            )
                            
                            # Store easier version
                            new_module_id = await self.content_storage.store_content_module(
                                learning_path_id=learning_path_id,
                                title=f"{original_module.get('title', 'Module')} (Simplified)",
                                content=easier_content,
                                module_type=original_module['module_type'],
                                difficulty='easy',
                                estimated_minutes=original_module['estimated_minutes'],
                                order_index=original_module['order_index'],
                                prerequisites=original_module.get('prerequisites', []),
                                metadata={'simplified_from': module_id}
                            )
                            
                            content_adjustments.append({
                                'type': 'content_generated',
                                'action': 'simplified_content',
                                'module_id': new_module_id,
                                'original_module_id': module_id,
                                'reason': 'Generated simplified version due to high cognitive load'
                            })
                    except Exception as e:
                        self.logger.error(f"Error generating easier content: {str(e)}")
            
            # Upgrade difficulty: generate harder version
            elif adjustment_type == 'upgrade_difficulty':
                module_id = adjustment.get('module_id')
                if module_id:
                    try:
                        original_module = await self.content_storage.get_content_by_id(module_id)
                        if original_module:
                            from content.content_variations import ContentVariationGenerator
                            variation_gen = ContentVariationGenerator()
                            harder_content = await variation_gen.generate_harder_version(
                                original_module['content'],
                                cognitive_load_profile
                            )
                            
                            new_module_id = await self.content_storage.store_content_module(
                                learning_path_id=learning_path_id,
                                title=f"{original_module.get('title', 'Module')} (Advanced)",
                                content=harder_content,
                                module_type=original_module['module_type'],
                                difficulty='hard',
                                estimated_minutes=original_module['estimated_minutes'],
                                order_index=original_module['order_index'],
                                prerequisites=original_module.get('prerequisites', []),
                                metadata={'advanced_from': module_id}
                            )
                            
                            content_adjustments.append({
                                'type': 'content_generated',
                                'action': 'advanced_content',
                                'module_id': new_module_id,
                                'original_module_id': module_id,
                                'reason': 'Generated advanced version for high-performing student'
                            })
                    except Exception as e:
                        self.logger.error(f"Error generating harder content: {str(e)}")
            
            # Insert prerequisite review: generate recap content
            elif adjustment_type == 'insert_prerequisite_review':
                weak_topics = student_data.get('weak_topics', [])
                if weak_topics:
                    try:
                        recap_content = await self.content_generator.generate_recap(
                            weak_topics=weak_topics,
                            recent_errors=[],
                            cognitive_load_profile=cognitive_load_profile
                        )
                        
                        recap_module_id = await self.content_storage.store_content_module(
                            learning_path_id=learning_path_id,
                            title=f"Review: {', '.join(weak_topics[:2])}",
                            content=recap_content,
                            module_type='recap',
                            difficulty='easy',
                            estimated_minutes=10,
                            order_index=adjustment.get('insert_at_index', 0),
                            prerequisites=[],
                            metadata={'generated_for': 'prerequisite_review', 'weak_topics': weak_topics}
                        )
                        
                        content_adjustments.append({
                            'type': 'content_generated',
                            'action': 'recap_inserted',
                            'module_id': recap_module_id,
                            'topics': weak_topics,
                            'reason': f"Generated personalized review materials for {', '.join(weak_topics)}"
                        })
                    except Exception as e:
                        self.logger.error(f"Error generating recap content: {str(e)}")
        
        return content_adjustments
    
    def _should_trigger_major_adjustment(
        self,
        cognitive_load: float,
        performance: Dict[str, Any]
    ) -> bool:
        """
        Determine if a major curriculum adjustment is warranted.
        
        Args:
            cognitive_load: Current cognitive load score
            performance: Performance metrics
        
        Returns:
            True if major adjustment needed
        """
        # Critical cognitive load
        if cognitive_load > 85:
            return True
        
        # Severe performance issues
        if performance.get("quiz_accuracy", 100) < 40:
            return True
        
        # Plateau with multiple weak topics
        if performance.get("plateau_detected") and len(performance.get("weak_topics", [])) >= 3:
            return True
        
        return False
    
    def _extract_pacing_changes(self, adjustments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract pacing-related changes from adjustments"""
        pacing_changes = {
            "time_multiplier": 1.0,
            "adjustment_percentage": "0%",
            "reasoning": "No pacing changes"
        }
        
        for adjustment in adjustments:
            if adjustment.get("type") == "adjust_pacing":
                pacing_changes = {
                    "time_multiplier": adjustment.get("time_multiplier", 1.0),
                    "adjustment_percentage": adjustment.get("pacing_change", "0%"),
                    "reasoning": adjustment.get("reason", "Pacing optimized")
                }
                break
        
        return pacing_changes
    
    def _get_default_output(self) -> Dict[str, Any]:
        """Return default output when execution fails"""
        return {
            "curriculum_adjustments": [],
            "difficulty_level": "medium",
            "current_module_id": None,
            "pacing_changes": {},
            "adjustment_rationale": "Unable to analyze curriculum at this time.",
            "adjustment_confidence": 0.0
        }
