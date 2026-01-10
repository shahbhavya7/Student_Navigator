"""
Curriculum State Manager

Handles persistence and version control for curriculum modifications,
managing both PostgreSQL storage and Redis caching.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from config.database import get_async_db
from config.redis_client import redis_client
import json
import logging


class CurriculumStateManager:
    """Manages curriculum state persistence and version history"""
    
    # Cache TTL: 1 hour
    CACHE_TTL = 3600
    
    def __init__(self):
        self.logger = logging.getLogger("CurriculumStateManager")
    
    async def get_current_state(
        self,
        student_id: str,
        learning_path_id: str
    ) -> Dict[str, Any]:
        """
        Fetch current curriculum state from Redis cache or PostgreSQL.
        
        Args:
            student_id: Student identifier
            learning_path_id: Learning path identifier
        
        Returns:
            Current curriculum state dict
        """
        # Try Redis cache first
        cache_key = f"curriculum:{student_id}:{learning_path_id}"
        
        try:
            cached_data = await redis_client.cache_client.hgetall(cache_key)
            
            if cached_data:
                # Parse cached data
                state = {}
                for key, value in cached_data.items():
                    key_str = key.decode() if isinstance(key, bytes) else key
                    value_str = value.decode() if isinstance(value, bytes) else value
                    
                    try:
                        state[key_str] = json.loads(value_str)
                    except:
                        state[key_str] = value_str
                
                self.logger.info(f"Retrieved curriculum state from cache for {student_id}")
                return state
        
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {str(e)}")
        
        # Cache miss - fetch from database
        return await self._fetch_from_database(student_id, learning_path_id)
    
    async def _fetch_from_database(
        self,
        student_id: str,
        learning_path_id: str
    ) -> Dict[str, Any]:
        """Fetch curriculum state from PostgreSQL"""
        try:
            async for db in get_async_db():
                # Schema only has learning_paths table with studentId FK
                query = text("""
                    SELECT 
                        lp.id as learning_path_id,
                        lp.title,
                        lp.difficulty,
                        lp."currentModuleId",
                        lp.progress,
                        lp."updatedAt"
                    FROM learning_paths lp
                    WHERE lp.id = :path_id AND lp."studentId" = :student_id
                """)
                
                result = await db.execute(query, {
                    "student_id": student_id,
                    "path_id": learning_path_id
                })
                row = result.fetchone()
                
                if not row:
                    return {
                        "learning_path_id": learning_path_id,
                        "difficulty": "medium",
                        "current_module_id": None,
                        "progress": 0,
                        "completed_modules": []
                    }
                
                # Get completed modules from quiz_results
                completed_query = text("""
                    SELECT DISTINCT "moduleId"
                    FROM quiz_results
                    WHERE "studentId" = :student_id AND score >= 60
                """)
                completed_result = await db.execute(completed_query, {"student_id": student_id})
                completed_modules = [r[0] for r in completed_result.fetchall()]
                
                state = {
                    "learning_path_id": row[0],
                    "title": row[1],
                    "difficulty": row[2],
                    "current_module_id": row[3],
                    "progress": row[4],
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "completed_modules": completed_modules
                }
                
                # Cache for future requests
                await self.cache_curriculum_state(student_id, learning_path_id, state)
                
                return state
        
        except Exception as e:
            self.logger.error(f"Database fetch failed: {str(e)}")
            raise
    
    async def save_curriculum_adjustment(
        self,
        learning_path_id: str,
        adjustments: List[Dict[str, Any]],
        reason: str
    ) -> bool:
        """
        Persist curriculum adjustments to database with version history.
        Uses single transaction for all operations.
        
        Args:
            learning_path_id: Learning path identifier
            adjustments: List of adjustment actions
            reason: Reason for adjustments
        
        Returns:
            True if successful
        """
        try:
            async for db in get_async_db():
                # Fetch current state for history
                query = text("""
                    SELECT difficulty, "currentModuleId", progress
                    FROM learning_paths
                    WHERE id = :path_id
                """)
                result = await db.execute(query, {"path_id": learning_path_id})
                current_row = result.fetchone()
                
                if not current_row:
                    self.logger.error(f"Learning path {learning_path_id} not found")
                    return False
                
                previous_state = {
                    "difficulty": current_row[0],
                    "current_module_id": current_row[1],
                    "progress": current_row[2]
                }
                
                # Apply adjustments to determine new state
                new_state = previous_state.copy()
                
                for adjustment in adjustments:
                    adj_type = adjustment.get("type")
                    
                    if adj_type in ["downgrade_difficulty", "upgrade_difficulty"]:
                        new_state["difficulty"] = adjustment.get("to_difficulty", previous_state["difficulty"])
                    
                    elif adj_type == "adjust_pacing":
                        # Pacing is tracked but doesn't change core state
                        pass
                
                # Update learning path (inline, same session)
                update_fields = []
                params = {"path_id": learning_path_id, "updated_at": datetime.now()}
                
                if "difficulty" in new_state and new_state["difficulty"] != previous_state["difficulty"]:
                    update_fields.append('difficulty = :difficulty')
                    params["difficulty"] = new_state["difficulty"]
                
                if "current_module_id" in new_state:
                    update_fields.append('"currentModuleId" = :current_module_id')
                    params["current_module_id"] = new_state["current_module_id"]
                
                if "progress" in new_state:
                    update_fields.append('progress = :progress')
                    params["progress"] = new_state["progress"]
                
                if update_fields:
                    update_fields.append('"updatedAt" = :updated_at')
                    
                    update_query = text(f"""
                        UPDATE learning_paths
                        SET {', '.join(update_fields)}
                        WHERE id = :path_id
                    """)
                    
                    await db.execute(update_query, params)
                
                # Create history entry (inline, same session)
                history_query = text("""
                    INSERT INTO path_history 
                    ("learningPathId", "changeType", "previousState", "newState", "reason", "timestamp")
                    VALUES (:path_id, :change_type, :previous, :new, :reason, :timestamp)
                """)
                
                await db.execute(history_query, {
                    "path_id": learning_path_id,
                    "change_type": "curriculum_adjustment",
                    "previous": json.dumps(previous_state),
                    "new": json.dumps(new_state),
                    "reason": reason,
                    "timestamp": datetime.now()
                })
                
                # Commit all changes in single transaction
                await db.commit()
                
                self.logger.info(f"Saved curriculum adjustments for {learning_path_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Failed to save adjustments: {str(e)}")
            return False
    
    async def create_history_entry(
        self,
        learning_path_id: str,
        change_type: str,
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any],
        reason: str
    ):
        """
        Log curriculum change to path_history table.
        
        Args:
            learning_path_id: Learning path identifier
            change_type: Type of change made
            previous_state: State before modification
            new_state: State after modification
            reason: Explanation for change
        """
        try:
            async for db in get_async_db():
                query = text("""
                    INSERT INTO path_history 
                    ("learningPathId", "changeType", "previousState", "newState", "reason", "timestamp")
                    VALUES (:path_id, :change_type, :previous, :new, :reason, :timestamp)
                """)
                
                await db.execute(query, {
                    "path_id": learning_path_id,
                    "change_type": change_type,
                    "previous": json.dumps(previous_state),
                    "new": json.dumps(new_state),
                    "reason": reason,
                    "timestamp": datetime.now()
                })
                
                self.logger.info(f"Created history entry for {learning_path_id}")
                break
        
        except Exception as e:
            self.logger.error(f"Failed to create history entry: {str(e)}")
            # Don't raise - history logging shouldn't block the main operation
    
    async def update_learning_path(
        self,
        learning_path_id: str,
        updates: Dict[str, Any]
    ):
        """
        Update learning_paths table with new state.
        
        Args:
            learning_path_id: Learning path identifier
            updates: Fields to update
        """
        try:
            async for db in get_async_db():
                # Build dynamic UPDATE query
                update_fields = []
                params = {"path_id": learning_path_id, "updated_at": datetime.now()}
                
                if "difficulty" in updates:
                    update_fields.append('difficulty = :difficulty')
                    params["difficulty"] = updates["difficulty"]
                
                if "current_module_id" in updates:
                    update_fields.append('"currentModuleId" = :current_module_id')
                    params["current_module_id"] = updates["current_module_id"]
                
                if "progress" in updates:
                    update_fields.append('progress = :progress')
                    params["progress"] = updates["progress"]
                
                update_fields.append('"updatedAt" = :updated_at')
                
                query = text(f"""
                    UPDATE learning_paths
                    SET {', '.join(update_fields)}
                    WHERE id = :path_id
                """)
                
                await db.execute(query, params)
                self.logger.info(f"Updated learning path {learning_path_id}")
                break
        
        except Exception as e:
            self.logger.error(f"Failed to update learning path: {str(e)}")
            raise
    
    async def cache_curriculum_state(
        self,
        student_id: str,
        learning_path_id: str,
        state: Dict[str, Any]
    ):
        """
        Store curriculum state in Redis cache.
        
        Args:
            student_id: Student identifier
            learning_path_id: Learning path identifier
            state: State dict to cache
        """
        try:
            cache_key = f"curriculum:{student_id}:{learning_path_id}"
            
            # Prepare data for Redis hash
            cache_data = {}
            for key, value in state.items():
                if isinstance(value, (dict, list)):
                    cache_data[key] = json.dumps(value)
                else:
                    cache_data[key] = str(value)
            
            await redis_client.cache_client.hset(cache_key, mapping=cache_data)
            await redis_client.cache_client.expire(cache_key, self.CACHE_TTL)
            
            self.logger.debug(f"Cached curriculum state for {student_id}")
        
        except Exception as e:
            self.logger.warning(f"Failed to cache state: {str(e)}")
            # Cache failure shouldn't block operations
    
    async def get_curriculum_history(
        self,
        learning_path_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch curriculum adjustment history.
        
        Args:
            learning_path_id: Learning path identifier
            limit: Maximum number of history entries to return
        
        Returns:
            List of history entries
        """
        try:
            async for db in get_async_db():
                query = text("""
                    SELECT 
                        id, "changeType", "previousState", "newState", 
                        reason, "timestamp"
                    FROM path_history
                    WHERE "learningPathId" = :path_id
                    ORDER BY "timestamp" DESC
                    LIMIT :limit
                """)
                
                result = await db.execute(query, {
                    "path_id": learning_path_id,
                    "limit": limit
                })
                rows = result.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        "id": row[0],
                        "change_type": row[1],
                        "previous_state": json.loads(row[2]) if row[2] else {},
                        "new_state": json.loads(row[3]) if row[3] else {},
                        "reason": row[4],
                        "created_at": row[5].isoformat() if row[5] else None
                    })
                
                return history
        
        except Exception as e:
            self.logger.error(f"Failed to fetch history: {str(e)}")
            return []
    
    async def rollback_to_version(
        self,
        learning_path_id: str,
        history_id: str
    ) -> bool:
        """
        Restore curriculum to a previous version.
        
        Args:
            learning_path_id: Learning path identifier
            history_id: History entry ID to restore
        
        Returns:
            True if successful
        """
        try:
            async for db in get_async_db():
                # Fetch the target history entry
                query = text("""
                    SELECT "previousState", "newState", reason
                    FROM path_history
                    WHERE id = :history_id AND "learningPathId" = :path_id
                """)
                
                result = await db.execute(query, {
                    "history_id": history_id,
                    "path_id": learning_path_id
                })
                row = result.fetchone()
                
                if not row:
                    self.logger.error(f"History entry {history_id} not found")
                    return False
                
                # Use previous state as the rollback target
                rollback_state = json.loads(row[0])
                
                # Update learning path
                await self.update_learning_path(learning_path_id, rollback_state)
                
                # Create new history entry for rollback
                await self.create_history_entry(
                    learning_path_id,
                    "rollback",
                    json.loads(row[1]),  # Current state becomes previous
                    rollback_state,      # Rollback target becomes new
                    f"Rollback to version {history_id}: {row[2]}"
                )
                
                await db.commit()
                
                self.logger.info(f"Rolled back {learning_path_id} to version {history_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False
    
    async def invalidate_cache(
        self,
        student_id: str,
        learning_path_id: str
    ):
        """
        Clear cached curriculum state.
        
        Args:
            student_id: Student identifier
            learning_path_id: Learning path identifier
        """
        try:
            cache_key = f"curriculum:{student_id}:{learning_path_id}"
            await redis_client.cache_client.delete(cache_key)
            self.logger.debug(f"Invalidated cache for {student_id}")
        except Exception as e:
            self.logger.warning(f"Cache invalidation failed: {str(e)}")
