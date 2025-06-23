from fastapi import APIRouter, status, HTTPException
from datetime import datetime
import structlog
import asyncio
import psutil
import redis.asyncio as redis

from src.models.schemas import HealthResponse, ReadinessResponse
from src.config.database import check_db_health
from src.config.settings import get_settings

logger = structlog.get_logger()
router = APIRouter()

async def check_redis_health() -> bool:
    """Check Redis connection health"""
    try:
        settings = get_settings()
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Simple ping test
        await redis_client.ping()
        await redis_client.close()
        return True
        
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False

async def check_memory_usage() -> dict:
    """Check system memory usage"""
    try:
        memory = psutil.virtual_memory()
        return {
            "usage_percent": memory.percent,
            "available_gb": round(memory.available / (1024**3), 2),
            "total_gb": round(memory.total / (1024**3), 2)
        }
    except Exception:
        return {"status": "unavailable"}

async def check_disk_usage() -> dict:
    """Check disk usage"""
    try:
        disk = psutil.disk_usage('/')
        return {
            "usage_percent": round((disk.used / disk.total) * 100, 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2)
        }
    except Exception:
        return {"status": "unavailable"}

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint for Kubernetes liveness probe
    Returns 200 if service is running
    """
    settings = get_settings()
    
    # Basic service health
    health_data = {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "timestamp": datetime.utcnow(),
        "dependencies": {
            "database": "unknown",
            "redis": "unknown"
        }
    }
    
    try:
        # Quick dependency checks (with timeout)
        db_task = asyncio.create_task(check_db_health())
        redis_task = asyncio.create_task(check_redis_health())
        
        # Wait for checks with timeout
        db_healthy, redis_healthy = await asyncio.wait_for(
            asyncio.gather(db_task, redis_task, return_exceptions=True),
            timeout=settings.HEALTH_CHECK_TIMEOUT
        )
        
        health_data["dependencies"]["database"] = "connected" if db_healthy else "disconnected"
        health_data["dependencies"]["redis"] = "connected" if redis_healthy else "disconnected"
        
    except asyncio.TimeoutError:
        logger.warning("Health check timeout")
        health_data["dependencies"]["database"] = "timeout"
        health_data["dependencies"]["redis"] = "timeout"
    except Exception as e:
        logger.error("Health check error", error=str(e))
    
    return HealthResponse(**health_data)

@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes readiness probe
    Returns 200 only if service is ready to handle requests
    """
    settings = get_settings()
    
    readiness_data = {
        "status": "ready",
        "service": settings.SERVICE_NAME,
        "timestamp": datetime.utcnow(),
        "dependencies": {},
        "checks": {}
    }
    
    all_healthy = True
    
    try:
        # Comprehensive dependency checks
        db_task = asyncio.create_task(check_db_health())
        redis_task = asyncio.create_task(check_redis_health())
        memory_task = asyncio.create_task(check_memory_usage())
        disk_task = asyncio.create_task(check_disk_usage())
        
        # Wait for all checks with timeout
        results = await asyncio.wait_for(
            asyncio.gather(
                db_task, redis_task, memory_task, disk_task,
                return_exceptions=True
            ),
            timeout=settings.HEALTH_CHECK_TIMEOUT
        )
        
        db_healthy, redis_healthy, memory_info, disk_info = results
        
        # Database check
        readiness_data["dependencies"]["database"] = "connected" if db_healthy else "disconnected"
        readiness_data["checks"]["database_query"] = "success" if db_healthy else "failed"
        if not db_healthy:
            all_healthy = False
        
        # Redis check
        readiness_data["dependencies"]["redis"] = "connected" if redis_healthy else "disconnected"
        readiness_data["checks"]["redis_ping"] = "success" if redis_healthy else "failed"
        if not redis_healthy:
            all_healthy = False
        
        # Memory check
        if isinstance(memory_info, dict) and "usage_percent" in memory_info:
            memory_usage = memory_info["usage_percent"]
            readiness_data["checks"]["memory_usage"] = f"{memory_usage}%"
            # Consider unhealthy if memory usage > 90%
            if memory_usage > 90:
                all_healthy = False
        else:
            readiness_data["checks"]["memory_usage"] = "unavailable"
        
        # Disk check
        if isinstance(disk_info, dict) and "usage_percent" in disk_info:
            disk_usage = disk_info["usage_percent"]
            readiness_data["checks"]["disk_space"] = f"{disk_usage}%"
            # Consider unhealthy if disk usage > 85%
            if disk_usage > 85:
                all_healthy = False
        else:
            readiness_data["checks"]["disk_space"] = "unavailable"
        
    except asyncio.TimeoutError:
        logger.warning("Readiness check timeout")
        readiness_data["status"] = "not_ready"
        readiness_data["dependencies"] = {"timeout": "health_check_timeout"}
        all_healthy = False
        
    except Exception as e:
        logger.error("Readiness check error", error=str(e))
        readiness_data["status"] = "not_ready"
        readiness_data["checks"]["error"] = str(e)
        all_healthy = False
    
    # Set overall status
    if not all_healthy:
        readiness_data["status"] = "not_ready"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=readiness_data
        )
    
    return ReadinessResponse(**readiness_data)

@router.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint for monitoring
    Returns service metrics in a simple format
    """
    try:
        memory_info = await check_memory_usage()
        disk_info = await check_disk_usage()
        
        metrics_data = {
            "service": "user_management",
            "version": "1.0.0",
            "uptime_seconds": int(psutil.boot_time()),
            "memory": memory_info,
            "disk": disk_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return metrics_data
        
    except Exception as e:
        logger.error("Metrics collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics collection failed"
        )