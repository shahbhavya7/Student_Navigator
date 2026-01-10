"""PostgreSQL storage service for generated content."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_async_db

try:
    from prisma import Prisma
    PRISMA_AVAILABLE = True
except ImportError:
    PRISMA_AVAILABLE = False
    Prisma = None

logger = logging.getLogger(__name__)


class ContentStorageService:
    """Service for persisting generated content to PostgreSQL."""
    
    def __init__(self):
        """Initialize content storage service."""
        if not PRISMA_AVAILABLE:
            logger.warning("Prisma not available, ContentStorageService will operate in mock mode")
            self.prisma = None
        else:
            self.prisma = Prisma()
        logger.info("ContentStorageService initialized")
    
    async def connect(self):
        """Connect to database."""
        if self.prisma and not self.prisma.is_connected():
            await self.prisma.connect()
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.prisma and self.prisma.is_connected():
            await self.prisma.disconnect()
    
    async def store_content_module(
        self,
        learning_path_id: str,
        title: str,
        content: str,
        module_type: str,
        difficulty: str,
        estimated_minutes: int,
        order_index: int,
        prerequisites: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a content module in the database.
        
        Args:
            learning_path_id: ID of associated learning path
            title: Module title
            content: Module content (JSON or Markdown)
            module_type: Type (lesson, quiz, exercise, recap)
            difficulty: Difficulty level
            estimated_minutes: Estimated completion time
            order_index: Position in learning path
            prerequisites: List of prerequisite topics
            metadata: Additional metadata
        
        Returns:
            Created content module ID
        """
        try:
            await self.connect()
            
            # Prepare metadata with generation info
            full_metadata = metadata or {}
            full_metadata.update({
                'generated': True,
                'generated_at': datetime.utcnow().isoformat(),
                'prerequisites': prerequisites
            })
            
            content_module = await self.prisma.contentmodule.create(
                data={
                    'learningPathId': learning_path_id,
                    'title': title,
                    'content': content,
                    'moduleType': module_type,
                    'difficulty': difficulty,
                    'estimatedMinutes': estimated_minutes,
                    'orderIndex': order_index,
                    'prerequisites': prerequisites,
                    'metadata': full_metadata
                }
            )
            
            logger.info(f"Stored content module: {content_module.id} for path {learning_path_id}")
            return content_module.id
            
        except Exception as e:
            logger.error(f"Error storing content module: {str(e)}")
            raise
    
    async def get_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a content module by ID.
        
        Args:
            content_id: Content module ID
        
        Returns:
            Content module data or None if not found
        """
        try:
            await self.connect()
            
            content_module = await self.prisma.contentmodule.find_unique(
                where={'id': content_id}
            )
            
            if content_module:
                return {
                    'id': content_module.id,
                    'learning_path_id': content_module.learningPathId,
                    'title': content_module.title,
                    'content': content_module.content,
                    'module_type': content_module.moduleType,
                    'difficulty': content_module.difficulty,
                    'estimated_minutes': content_module.estimatedMinutes,
                    'order_index': content_module.orderIndex,
                    'prerequisites': content_module.prerequisites,
                    'metadata': content_module.metadata,
                    'created_at': content_module.createdAt.isoformat() if content_module.createdAt else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving content {content_id}: {str(e)}")
            return None
    
    async def search_content(
        self,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        module_type: Optional[str] = None,
        learning_path_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for content modules with filters.
        
        Args:
            topic: Topic to search for (in title)
            difficulty: Difficulty level filter
            module_type: Module type filter
            learning_path_id: Learning path ID filter
            limit: Maximum results to return
        
        Returns:
            List of matching content modules
        """
        try:
            await self.connect()
            
            # Build where clause
            where_conditions = {}
            
            if topic:
                where_conditions['title'] = {'contains': topic, 'mode': 'insensitive'}
            
            if difficulty:
                where_conditions['difficulty'] = difficulty
            
            if module_type:
                where_conditions['moduleType'] = module_type
            
            if learning_path_id:
                where_conditions['learningPathId'] = learning_path_id
            
            content_modules = await self.prisma.contentmodule.find_many(
                where=where_conditions,
                take=limit,
                order={'createdAt': 'desc'}
            )
            
            results = []
            for module in content_modules:
                results.append({
                    'id': module.id,
                    'learning_path_id': module.learningPathId,
                    'title': module.title,
                    'content': module.content,
                    'module_type': module.moduleType,
                    'difficulty': module.difficulty,
                    'estimated_minutes': module.estimatedMinutes,
                    'order_index': module.orderIndex,
                    'prerequisites': module.prerequisites,
                    'created_at': module.createdAt.isoformat() if module.createdAt else None
                })
            
            logger.info(f"Found {len(results)} content modules matching search criteria")
            return results
            
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            return []
    
    async def update_content_metadata(
        self,
        content_id: str,
        difficulty: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update content module metadata based on feedback.
        
        Args:
            content_id: Content module ID
            difficulty: New difficulty level
            estimated_minutes: Updated time estimate
            metadata_updates: Additional metadata to update
        
        Returns:
            True if updated successfully
        """
        try:
            await self.connect()
            
            # Build update data
            update_data = {}
            
            if difficulty:
                update_data['difficulty'] = difficulty
            
            if estimated_minutes:
                update_data['estimatedMinutes'] = estimated_minutes
            
            # Merge metadata updates
            if metadata_updates:
                existing = await self.get_content_by_id(content_id)
                if existing:
                    current_metadata = existing.get('metadata', {})
                    current_metadata.update(metadata_updates)
                    update_data['metadata'] = current_metadata
            
            if update_data:
                await self.prisma.contentmodule.update(
                    where={'id': content_id},
                    data=update_data
                )
                
                logger.info(f"Updated metadata for content module: {content_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating content metadata: {str(e)}")
            return False
    
    async def link_content_to_learning_path(
        self,
        content_id: str,
        learning_path_id: str,
        order_index: int
    ) -> bool:
        """
        Associate generated content with a student's learning path.
        
        Args:
            content_id: Content module ID
            learning_path_id: Learning path ID
            order_index: Position in learning path
        
        Returns:
            True if linked successfully
        """
        try:
            await self.connect()
            
            await self.prisma.contentmodule.update(
                where={'id': content_id},
                data={
                    'learningPathId': learning_path_id,
                    'orderIndex': order_index
                }
            )
            
            logger.info(f"Linked content {content_id} to learning path {learning_path_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error linking content to learning path: {str(e)}")
            return False
    
    async def get_content_usage_stats(
        self,
        content_id: str
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a content module.
        
        Args:
            content_id: Content module ID
        
        Returns:
            Dictionary with usage statistics
        """
        try:
            await self.connect()
            
            # Get content module with progress data
            content_module = await self.prisma.contentmodule.find_unique(
                where={'id': content_id},
                include={
                    'studentProgress': True
                }
            )
            
            if not content_module:
                return {}
            
            total_students = len(content_module.studentProgress) if content_module.studentProgress else 0
            completed_students = sum(
                1 for progress in (content_module.studentProgress or [])
                if progress.completed
            )
            
            completion_rate = (completed_students / total_students * 100) if total_students > 0 else 0
            
            # Calculate average time spent
            times = [
                progress.timeSpent for progress in (content_module.studentProgress or [])
                if progress.timeSpent
            ]
            avg_time = sum(times) / len(times) if times else 0
            
            return {
                'content_id': content_id,
                'total_students': total_students,
                'completed_students': completed_students,
                'completion_rate_percent': round(completion_rate, 2),
                'average_time_minutes': round(avg_time, 2),
                'estimated_vs_actual_ratio': round(avg_time / content_module.estimatedMinutes, 2) if avg_time and content_module.estimatedMinutes else None
            }
            
        except Exception as e:
            logger.error(f"Error getting content usage stats: {str(e)}")
            return {'error': str(e)}
    
    async def get_content_by_learning_path(
        self,
        learning_path_id: str,
        order_by: str = 'orderIndex'
    ) -> List[Dict[str, Any]]:
        """
        Get all content modules for a learning path.
        
        Args:
            learning_path_id: Learning path ID
            order_by: Field to order by
        
        Returns:
            List of content modules
        """
        return await self.search_content(
            learning_path_id=learning_path_id,
            limit=100
        )
