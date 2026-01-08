from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config.settings import settings
from config.database import init_db, close_db
from config.redis_client import redis_client
from api.health import router as health_router
from api.bridge import router as bridge_router
from services.event_consumer import event_consumer
from services.pubsub_handler import pubsub_listener

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI application"""
    # Startup
    logger.info("🚀 Starting Python Backend...")
    
    try:
        # Initialize database
        await init_db()
        
        # Initialize Redis
        await redis_client.connect()
        
        # Start background services
        await event_consumer.start()
        await pubsub_listener.start()
        
        logger.info("✅ Python Backend started successfully")
        logger.info(f"📡 API available at http://0.0.0.0:8000")
        logger.info(f"📚 API docs at http://0.0.0.0:8000/docs")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("⏳ Shutting down Python Backend...")
    
    try:
        # Stop background services
        await event_consumer.stop()
        await pubsub_listener.stop()
        
        # Close connections
        await redis_client.disconnect()
        await close_db()
        
        logger.info("✅ Python Backend shut down gracefully")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Initialize FastAPI app
app = FastAPI(
    title="Adaptive Student Navigator - Python Backend",
    description="AI Agent orchestration service with LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.NODE_BACKEND_URL,
        "http://localhost:3000",
        "http://localhost:3002"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(bridge_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Adaptive Student Navigator - Python Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
