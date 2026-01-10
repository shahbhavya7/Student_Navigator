"""FastAPI router for content generation endpoints."""

import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    GenerateContentRequest,
    GeneratedContentResponse,
    ContentVariationRequest,
    ContentVariationResponse,
    BatchGenerateRequest,
    BatchGenerateResponse,
    ContentModuleResponse,
    ContentSearchRequest,
    ContentCacheStatsResponse
)
from content.generator import ContentGenerator
from content.content_variations import ContentVariationGenerator, VariationStrategy
from content.content_cache import ContentCacheManager
from content.content_storage import ContentStorageService
from content.difficulty_adapter import DifficultyAdapter
from content.content_validator import ContentValidator
from content.metadata_enricher import MetadataEnricher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])

# Initialize services
content_generator = ContentGenerator()
variation_generator = ContentVariationGenerator()
cache_manager = ContentCacheManager()
content_storage = ContentStorageService()
difficulty_adapter = DifficultyAdapter()
content_validator = ContentValidator()
metadata_enricher = MetadataEnricher()


@router.post("/generate", response_model=GeneratedContentResponse)
async def generate_content(request: GenerateContentRequest):
    """
    Generate new educational content on-demand.
    
    This endpoint:
    1. Checks cache for existing content
    2. Generates new content if not cached
    3. Validates content quality
    4. Stores in Redis cache and PostgreSQL
    5. Returns generated content
    """
    try:
        start_time = time.time()
        
        # Adapt generation parameters based on cognitive load
        cognitive_load_score = request.cognitive_load_profile.get('current_score', 50)
        
        # Calculate optimal difficulty based on cognitive load
        adapted_difficulty = difficulty_adapter.calculate_optimal_difficulty(
            cognitive_load_score=cognitive_load_score,
            current_difficulty=request.difficulty,
            performance_score=0.7  # Default, could come from request
        )
        
        generation_params = difficulty_adapter.adapt_generation_params(
            {
                'topic': request.topic,
                'difficulty': adapted_difficulty,
                'estimated_minutes': request.estimated_minutes or 15
            },
            cognitive_load_score
        )
        
        # Determine cognitive load range for caching
        if cognitive_load_score > 70:
            load_range = 'high'
        elif cognitive_load_score > 30:
            load_range = 'medium'
        else:
            load_range = 'low'
        
        # Check cache first (use adapted difficulty for cache key)
        cached_content = await cache_manager.get_cached_content(
            topic=request.topic,
            content_type=request.content_type,
            difficulty=adapted_difficulty,
            cognitive_load_range=load_range
        )
        
        if cached_content:
            logger.info(f"Serving cached content for {request.topic} (adapted difficulty: {adapted_difficulty})")
            
            # Parse cached content to get stored data
            try:
                import json
                cache_data = json.loads(cached_content)
                actual_content = cache_data.get('content', cached_content)
                cached_metadata = cache_data.get('metadata', {})
                cached_content_id = cache_data.get('content_id', 'cached')
                cached_estimated_minutes = cache_data.get('estimated_minutes', request.estimated_minutes or 15)
            except:
                actual_content = cached_content
                cached_metadata = {}
                cached_content_id = 'cached'
                cached_estimated_minutes = request.estimated_minutes or 15
            
            return GeneratedContentResponse(
                content_id=cached_content_id,
                topic=request.topic,
                content_type=request.content_type,
                difficulty=adapted_difficulty,
                content=actual_content,
                metadata=cached_metadata,
                estimated_minutes=cached_estimated_minutes,
                prerequisites=request.prerequisites,
                generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                cached=True
            )
        
        # Generate new content (use adapted difficulty)
        if request.content_type == 'lesson':
            content = await content_generator.generate_lesson(
                topic=request.topic,
                difficulty=adapted_difficulty,
                prerequisites=request.prerequisites,
                estimated_minutes=int(generation_params.get('estimated_minutes', 15) * 
                                    generation_params.get('estimated_minutes_multiplier', 1.0)),
                cognitive_load_profile=request.cognitive_load_profile
            )
        
        elif request.content_type == 'quiz':
            quiz_params = difficulty_adapter.adjust_quiz_complexity(
                cognitive_load_score,
                base_questions=5
            )
            content = await content_generator.generate_quiz(
                topic=request.topic,
                difficulty=adapted_difficulty,
                num_questions=quiz_params['num_questions'],
                cognitive_load_profile=request.cognitive_load_profile
            )
        
        elif request.content_type == 'exercise':
            content = await content_generator.generate_exercise(
                topic=request.topic,
                difficulty=adapted_difficulty,
                exercise_type='problem-solving',
                cognitive_load_profile=request.cognitive_load_profile
            )
        
        elif request.content_type == 'recap':
            content = await content_generator.generate_recap(
                weak_topics=[request.topic],
                recent_errors=[],
                cognitive_load_profile=request.cognitive_load_profile
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid content_type: {request.content_type}")
        
        # Validate content (use adapted difficulty)
        validation_result = content_validator.validate_content(
            content=content,
            content_type=request.content_type,
            expected_difficulty=adapted_difficulty,
            estimated_minutes=request.estimated_minutes or 15,
            prerequisites=request.prerequisites
        )
        
        if not validation_result.passed:
            logger.warning(f"Content validation had issues: {validation_result.issues}")
            # Continue anyway but log issues
        
        # Enrich metadata
        enriched_metadata = metadata_enricher.enrich_metadata(
            content=content,
            content_type=request.content_type,
            existing_metadata={
                'generation_params': generation_params,
                'adapted_difficulty': adapted_difficulty,
                'original_difficulty': request.difficulty
            }
        )
        
        # Store in PostgreSQL first to get content_id
        content_id = await content_storage.store_content_module(
            learning_path_id=request.learning_path_id,
            title=f"{request.topic} - {request.content_type.title()}",
            content=content,
            module_type=request.content_type,
            difficulty=adapted_difficulty,
            estimated_minutes=request.estimated_minutes or enriched_metadata.get('calculated_reading_time', 15),
            order_index=0,  # Will be updated by curriculum agent
            prerequisites=request.prerequisites,
            metadata=enriched_metadata
        )
        
        # Cache content with content_id and metadata
        await cache_manager.cache_content(
            content=content,
            topic=request.topic,
            content_type=request.content_type,
            difficulty=adapted_difficulty,
            cognitive_load_range=load_range,
            metadata={
                **enriched_metadata,
                'content_id': content_id,
                'estimated_minutes': request.estimated_minutes or enriched_metadata.get('calculated_reading_time', 15)
            }
        )
        
        generation_time = time.time() - start_time
        logger.info(f"Generated and stored content {content_id} in {generation_time:.2f}s")
        
        return GeneratedContentResponse(
            content_id=content_id,
            topic=request.topic,
            content_type=request.content_type,
            difficulty=adapted_difficulty,
            content=content,
            metadata=enriched_metadata,
            estimated_minutes=request.estimated_minutes or enriched_metadata.get('calculated_reading_time', 15),
            prerequisites=request.prerequisites,
            generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            cached=False
        )
    
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.get("/{content_id}", response_model=ContentModuleResponse)
async def get_content(content_id: str):
    """Retrieve a specific content module by ID."""
    try:
        content_data = await content_storage.get_content_by_id(content_id)
        
        if not content_data:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return ContentModuleResponse(
            id=content_data['id'],
            title=content_data.get('title', 'Untitled'),
            content=content_data['content'],
            module_type=content_data['module_type'],
            difficulty=content_data['difficulty'],
            estimated_minutes=content_data['estimated_minutes'],
            prerequisites=content_data.get('prerequisites', []),
            created_at=content_data.get('created_at'),
            metadata=content_data.get('metadata', {})
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{content_id}/variations", response_model=ContentVariationResponse)
async def generate_variation(
    content_id: str,
    request: ContentVariationRequest
):
    """Generate a variation of existing content (easier/harder/alternative)."""
    try:
        # Get original content
        original_content = await content_storage.get_content_by_id(content_id)
        
        if not original_content:
            raise HTTPException(status_code=404, detail="Original content not found")
        
        # Generate variation
        if request.variation_type == 'easier':
            varied_content = await variation_generator.generate_easier_version(
                original_content['content'],
                request.cognitive_load_profile
            )
            new_difficulty = 'easy'
        
        elif request.variation_type == 'harder':
            varied_content = await variation_generator.generate_harder_version(
                original_content['content'],
                request.cognitive_load_profile
            )
            new_difficulty = 'hard'
        
        elif request.variation_type == 'alternative':
            varied_content = await variation_generator.generate_alternative_explanation(
                original_content['content'],
                VariationStrategy.CHANGE_APPROACH,
                request.cognitive_load_profile
            )
            new_difficulty = original_content['difficulty']
        
        else:
            raise HTTPException(status_code=400, detail="Invalid variation_type")
        
        # Store varied content
        variation_id = await content_storage.store_content_module(
            learning_path_id=original_content['learning_path_id'],
            title=f"{original_content.get('title', 'Content')} ({request.variation_type})",
            content=varied_content,
            module_type=original_content['module_type'],
            difficulty=new_difficulty,
            estimated_minutes=original_content['estimated_minutes'],
            order_index=original_content['order_index'],
            prerequisites=original_content.get('prerequisites', []),
            metadata={
                'variation_of': content_id,
                'variation_type': request.variation_type
            }
        )
        
        return ContentVariationResponse(
            original_content_id=content_id,
            variation_content_id=variation_id,
            variation_type=request.variation_type,
            content=varied_content,
            difficulty_change=f"{original_content['difficulty']} -> {new_difficulty}" if new_difficulty != original_content['difficulty'] else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating variation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[ContentModuleResponse])
async def search_content(
    topic: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    learning_path_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    """Search for existing content modules."""
    try:
        results = await content_storage.search_content(
            topic=topic,
            difficulty=difficulty,
            module_type=content_type,
            learning_path_id=learning_path_id,
            limit=limit
        )
        
        return [
            ContentModuleResponse(
                id=item['id'],
                title=item.get('title', 'Untitled'),
                content=item['content'],
                module_type=item['module_type'],
                difficulty=item['difficulty'],
                estimated_minutes=item['estimated_minutes'],
                prerequisites=item.get('prerequisites', []),
                created_at=item.get('created_at'),
                metadata=item.get('metadata', {})
            )
            for item in results
        ]
    
    except Exception as e:
        logger.error(f"Error searching content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-generate", response_model=BatchGenerateResponse)
async def batch_generate_content(request: BatchGenerateRequest):
    """Generate multiple content modules for a learning path."""
    try:
        start_time = time.time()
        
        if len(request.topics) != len(request.difficulty_progression):
            raise HTTPException(
                status_code=400,
                detail="topics and difficulty_progression must have same length"
            )
        
        generated_ids = []
        failed_topics = []
        
        for i, topic in enumerate(request.topics):
            try:
                # Generate content for this topic
                gen_request = GenerateContentRequest(
                    topic=topic,
                    content_type='lesson',
                    difficulty=request.difficulty_progression[i],
                    student_id=request.student_id,
                    learning_path_id=request.learning_path_id,
                    cognitive_load_profile=request.cognitive_load_profile,
                    prerequisites=[],
                    estimated_minutes=20
                )
                
                response = await generate_content(gen_request)
                generated_ids.append(response.content_id)
                
            except Exception as e:
                logger.error(f"Failed to generate content for {topic}: {str(e)}")
                failed_topics.append(topic)
        
        generation_time = time.time() - start_time
        
        return BatchGenerateResponse(
            generated_content_ids=generated_ids,
            total_generated=len(generated_ids),
            failed_topics=failed_topics,
            generation_time_seconds=round(generation_time, 2)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=ContentCacheStatsResponse)
async def get_cache_stats():
    """Get cache performance metrics."""
    try:
        stats = await cache_manager.get_cache_stats()
        
        return ContentCacheStatsResponse(
            cache_hits=stats.get('cache_hits', 0),
            cache_misses=stats.get('cache_misses', 0),
            hit_rate_percent=stats.get('hit_rate_percent', 0.0),
            total_cached_items=stats.get('total_cached_items', 0),
            memory_used=stats.get('memory_used', 'Unknown')
        )
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
