"""
Curriculum API Endpoints

Provides REST API endpoints for curriculum management, learning path retrieval,
adjustment recommendations, and version history.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.schemas import (
    CurriculumStateResponse,
    LearningPathResponse,
    AdjustmentRecommendation,
    CurriculumHistoryResponse
)
from curriculum.state_manager import CurriculumStateManager
from curriculum.learning_graph import load_learning_path
from curriculum.difficulty_adjuster import DifficultyAdjuster
from curriculum.concept_reshuffler import ConceptReshuffler
from agents.curriculum_agent import CurriculumAgent
from config.database import get_async_db
from sqlalchemy import text
import json

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])

state_manager = CurriculumStateManager()
difficulty_adjuster = DifficultyAdjuster()
concept_reshuffler = ConceptReshuffler()


# Request/Response Models
class AdjustmentRequest(BaseModel):
    student_id: str
    learning_path_id: str
    reason: str
    adjustment_type: str  # difficulty, pacing, reorder


class RollbackRequest(BaseModel):
    history_id: str


@router.get("/{student_id}/current", response_model=CurriculumStateResponse)
async def get_current_curriculum(student_id: str):
    """
    Fetch current curriculum state for a student.
    
    Returns learning path details, current module, progress, difficulty level,
    and recent adjustments.
    """
    try:
        # Get student's active learning path (schema only has learning_paths with studentId)
        async for db in get_async_db():
            query = text("""
                SELECT lp.id, lp.title, lp.difficulty, lp."currentModuleId", 
                       lp.progress, lp."updatedAt", lp."createdAt"
                FROM learning_paths lp
                WHERE lp."studentId" = :student_id AND lp.status = 'active'
                ORDER BY lp."updatedAt" DESC
                LIMIT 1
            """)
            
            result = await db.execute(query, {"student_id": student_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="No active learning path found")
            
            learning_path_id = row[0]
            
            # Get current curriculum state (includes completed modules from quiz_results)
            state = await state_manager.get_current_state(student_id, learning_path_id)
            
            # Get recent adjustments
            history = await state_manager.get_curriculum_history(learning_path_id, limit=3)
            
            return CurriculumStateResponse(
                student_id=student_id,
                learning_path_id=learning_path_id,
                title=row[1],
                difficulty=row[2],
                current_module_id=row[3],
                progress=row[4],
                completed_modules=state.get("completed_modules", []),
                last_updated=row[5].isoformat() if row[5] else None,
                last_accessed=row[6].isoformat() if row[6] else None,  # Use createdAt as fallback
                recent_adjustments=[
                    {
                        "change_type": h["change_type"],
                        "reason": h["reason"],
                        "created_at": h["created_at"]
                    }
                    for h in history
                ]
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching curriculum: {str(e)}")


@router.get("/{student_id}/path/{learning_path_id}", response_model=LearningPathResponse)
async def get_learning_path(student_id: str, learning_path_id: str):
    """
    Get complete learning path with all modules.
    
    Returns graph structure, module sequence, prerequisites, and difficulty distribution.
    """
    try:
        # Load learning path graph
        learning_graph = await load_learning_path(learning_path_id)
        
        # Validate graph
        if not learning_graph.validate_path_integrity():
            raise HTTPException(status_code=500, detail="Learning path has integrity issues")
        
        # Get student progress
        state = await state_manager.get_current_state(student_id, learning_path_id)
        completed_modules = state.get("completed_modules", [])
        
        # Build module list with availability status
        modules = []
        for module_id, module in learning_graph.modules.items():
            modules.append({
                "id": module_id,
                "title": module["title"],
                "description": module.get("description", ""),
                "difficulty": module["difficulty"],
                "moduleType": module["moduleType"],
                "estimatedMinutes": module["estimatedMinutes"],
                "orderIndex": module["orderIndex"],
                "prerequisites": module["prerequisites"],
                "isOptional": module.get("isOptional", False),
                "is_completed": module_id in completed_modules,
                "is_available": all(
                    p in completed_modules for p in module["prerequisites"]
                )
            })
        
        # Sort by order index
        modules.sort(key=lambda m: m["orderIndex"])
        
        # Calculate statistics
        difficulty_distribution = {
            "easy": sum(1 for m in modules if m["difficulty"] == "easy"),
            "medium": sum(1 for m in modules if m["difficulty"] == "medium"),
            "hard": sum(1 for m in modules if m["difficulty"] == "hard")
        }
        
        return LearningPathResponse(
            learning_path_id=learning_path_id,
            modules=modules,
            total_modules=len(modules),
            completed_count=len(completed_modules),
            difficulty_distribution=difficulty_distribution,
            avg_difficulty_score=learning_graph.calculate_path_difficulty(),
            is_valid=True
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading learning path: {str(e)}")


@router.post("/adjust", response_model=Dict[str, Any])
async def trigger_curriculum_adjustment(request: AdjustmentRequest):
    """
    Trigger manual curriculum adjustment.
    
    Executes curriculum agent logic and returns adjustment plan with estimated impact.
    """
    try:
        # Load learning path
        learning_graph = await load_learning_path(request.learning_path_id)
        
        # Get current state
        current_state = await state_manager.get_current_state(
            request.student_id,
            request.learning_path_id
        )
        
        # Generate adjustment plan based on type
        adjustments = []
        
        if request.adjustment_type == "difficulty":
            # Adjust difficulty
            target_diff = "easy" if current_state.get("difficulty") != "easy" else "medium"
            adjustments = difficulty_adjuster.generate_adjustment_plan(
                learning_graph,
                target_diff,
                {}
            )
        
        elif request.adjustment_type == "pacing":
            # Adjust pacing
            pacing = concept_reshuffler.calculate_pacing_adjustment([50, 60, 70])
            adjustments = [{
                "type": "adjust_pacing",
                "time_multiplier": pacing["time_multiplier"],
                "pacing_change": pacing["adjustment_percentage"],
                "reason": pacing["reasoning"]
            }]
        
        elif request.adjustment_type == "reorder":
            # Reorder modules
            current_order = [m["id"] for m in sorted(
                learning_graph.modules.values(),
                key=lambda x: x["orderIndex"]
            )]
            
            new_order = concept_reshuffler.reorder_modules(
                current_order,
                {
                    "learning_graph": learning_graph,
                    "struggling_modules": [],
                    "target_difficulty": current_state.get("difficulty", "medium")
                }
            )
            
            adjustments = [{
                "type": "reorder_modules",
                "new_order": new_order,
                "reason": request.reason
            }]
        
        # Estimate impact
        total_impact = {
            "cognitive_load_change": 0,
            "time_change_minutes": 0,
            "success_rate_change": 0
        }
        
        for adjustment in adjustments:
            impact = difficulty_adjuster.estimate_impact(adjustment)
            total_impact["cognitive_load_change"] += impact["expected_cognitive_load_change"]
            total_impact["time_change_minutes"] += impact["expected_time_change_minutes"]
            total_impact["success_rate_change"] += impact["expected_success_rate_change"]
        
        # Save adjustments
        success = await state_manager.save_curriculum_adjustment(
            request.learning_path_id,
            adjustments,
            request.reason
        )
        
        return {
            "success": success,
            "adjustments": adjustments,
            "estimated_impact": total_impact,
            "applied_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying adjustment: {str(e)}")


@router.get("/{learning_path_id}/history", response_model=List[CurriculumHistoryResponse])
async def get_curriculum_history(learning_path_id: str, limit: int = 10):
    """
    Retrieve curriculum adjustment history.
    
    Returns list of changes with timestamps, reasons, and state transitions.
    """
    try:
        history = await state_manager.get_curriculum_history(learning_path_id, limit)
        
        return [
            CurriculumHistoryResponse(
                id=h["id"],
                learning_path_id=learning_path_id,
                change_type=h["change_type"],
                previous_state=h["previous_state"],
                new_state=h["new_state"],
                reason=h["reason"],
                created_at=h["created_at"]
            )
            for h in history
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.post("/{learning_path_id}/rollback", response_model=Dict[str, Any])
async def rollback_curriculum(learning_path_id: str, request: RollbackRequest):
    """
    Rollback to previous curriculum version.
    
    Restores curriculum state from a specific history entry.
    """
    try:
        success = await state_manager.rollback_to_version(
            learning_path_id,
            request.history_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Rollback failed")
        
        return {
            "success": True,
            "learning_path_id": learning_path_id,
            "rolled_back_to": request.history_id,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during rollback: {str(e)}")


@router.get("/{student_id}/recommendations", response_model=List[AdjustmentRecommendation])
async def get_curriculum_recommendations(student_id: str):
    """
    Get AI-powered curriculum recommendations.
    
    Analyzes student metrics and generates personalized adjustment suggestions.
    """
    try:
        # Get student's active learning path (use learning_paths table only)
        async for db in get_async_db():
            query = text("""
                SELECT lp.id
                FROM learning_paths lp
                WHERE lp."studentId" = :student_id AND lp.status = 'active'
                ORDER BY lp."updatedAt" DESC
                LIMIT 1
            """)
            
            result = await db.execute(query, {"student_id": student_id})
            row = result.fetchone()
            
            if not row:
                return []
            
            learning_path_id = row[0]
            break
        
        # Load learning path
        learning_graph = await load_learning_path(learning_path_id)
        
        # Get recent performance metrics (simplified - would fetch from state in production)
        student_metrics = {
            "cognitive_load_score": 65,
            "quiz_accuracy": 72,
            "learning_velocity": 0.5,
            "weak_topics": [],
            "engagement_score": 75
        }
        
        # Generate recommendations
        difficulty_analysis = difficulty_adjuster.calculate_target_difficulty(student_metrics)
        
        recommendations = []
        
        # Difficulty recommendation
        if difficulty_analysis["target_difficulty"] != "medium":
            recommendations.append(AdjustmentRecommendation(
                type="difficulty_adjustment",
                priority="high" if difficulty_analysis["confidence"] > 0.8 else "medium",
                description=f"Adjust difficulty to {difficulty_analysis['target_difficulty']} level",
                reasoning=", ".join(difficulty_analysis["reasoning"]),
                estimated_impact={
                    "cognitive_load_change": -10 if difficulty_analysis["target_difficulty"] == "easy" else +10,
                    "success_rate_change": +15 if difficulty_analysis["target_difficulty"] == "easy" else -5
                },
                confidence=difficulty_analysis["confidence"]
            ))
        
        # Pacing recommendation
        pacing = concept_reshuffler.calculate_pacing_adjustment([student_metrics["cognitive_load_score"]])
        if pacing["time_multiplier"] != 1.0:
            recommendations.append(AdjustmentRecommendation(
                type="pacing_adjustment",
                priority="medium",
                description=f"Adjust learning pace by {pacing['adjustment_percentage']}",
                reasoning=pacing["reasoning"],
                estimated_impact={
                    "time_change_minutes": int((pacing["time_multiplier"] - 1.0) * 100),
                    "cognitive_load_change": -5 if pacing["time_multiplier"] > 1.0 else +5
                },
                confidence=0.75
            ))
        
        return recommendations
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")
