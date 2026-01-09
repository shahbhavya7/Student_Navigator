from fastapi import APIRouter
from datetime import datetime
import httpx
from sqlalchemy import text

from models.schemas import HealthCheckResponse, AgentHealthResponse
from config.database import async_engine
from config.redis_client import redis_client
from config.settings import settings
from agents.graph import clr_agent_instance, performance_agent, engagement_agent, curriculum_agent, motivation_agent
from services.clr_monitoring import clr_monitoring_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Basic health check for all services"""
    
    services = {}
    
    # Check PostgreSQL
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "connected"
    except Exception as e:
        services["postgres"] = f"disconnected: {str(e)}"
    
    # Check Redis
    try:
        await redis_client.data_client.ping()
        services["redis"] = "connected"
    except Exception as e:
        services["redis"] = f"disconnected: {str(e)}"
    
    # Check Node.js backend
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.NODE_BACKEND_URL}/api/health", timeout=5.0)
            if response.status_code == 200:
                services["node_backend"] = "connected"
            else:
                services["node_backend"] = f"unhealthy: {response.status_code}"
    except Exception as e:
        services["node_backend"] = f"disconnected: {str(e)}"
    
    status = "ok" if all(s == "connected" for s in services.values()) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )


@router.get("/health/agents", response_model=AgentHealthResponse)
async def agent_health():
    """Detailed agent health and statistics"""
    
    # Get CLR agent health from monitoring service
    clr_health = clr_monitoring_service.get_health_status()
    
    agents = {
        "clr_agent": {
            **clr_health,
            "type": "enhanced_clr_agent"
        },
        "performance_agent": performance_agent.get_stats(),
        "engagement_agent": engagement_agent.get_stats(),
        "curriculum_agent": curriculum_agent.get_stats(),
        "motivation_agent": motivation_agent.get_stats()
    }
    
    # Workflow statistics
    total_executions = sum(a.get("metrics", {}).get("total_executions", 0) if isinstance(a, dict) and "metrics" in a else a.get("execution_count", 0) for a in agents.values())
    total_errors = sum(a.get("metrics", {}).get("failed_executions", 0) if isinstance(a, dict) and "metrics" in a else a.get("error_count", 0) for a in agents.values())
    
    workflow_stats = {
        "total_executions": total_executions,
        "total_errors": total_errors,
        "average_success_rate": (
            sum(a.get("success_rate", 0) if "success_rate" in a else (1.0 - a.get("metrics", {}).get("error_rate", 0)) for a in agents.values()) / len(agents)
            if agents else 0
        ),
        "clr_agent_status": clr_health["status"]
    }
    
    # Check pub/sub status
    try:
        await redis_client.pubsub_client.ping()
        pubsub_status = "connected"
    except:
        pubsub_status = "disconnected"
    
    return AgentHealthResponse(
        status="ok",
        agents=agents,
        workflow_stats=workflow_stats,
        pubsub_status=pubsub_status
    )


@router.get("/health/clr")
async def clr_health_detailed():
    """
    Detailed CLR Agent health and performance metrics.
    """
    try:
        metrics = clr_monitoring_service.get_metrics()
        health_status = clr_monitoring_service.get_health_status()
        
        return {
            "status": health_status["status"],
            "message": health_status["message"],
            "detailed_metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve CLR metrics: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
