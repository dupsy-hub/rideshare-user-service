import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import uuid

from src.config.database import create_tables, close_db_connection
from src.config.settings import get_settings
#from src.routes import auth, users, health
from src.routes.auth import router as auth_router
from src.routes.users import router as users_router
from src.routes.health import router as health_router


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    settings = get_settings()
    logger.info("Starting User Management Service", service="user-management")
    
    # Create database tables
    await create_tables()
    logger.info("Database tables created/verified")
    
    yield
    
    # Cleanup
    await close_db_connection()
    logger.info("Service shutdown complete")

# Create FastAPI instance
app = FastAPI(
    title="RideShare User Management Service",
    description="Handle user registration, authentication, and profile management",
    version="1.0.0",
    docs_url="/api/users/docs",
    redoc_url="/api/users/redoc",
    openapi_url="/api/users/openapi.json",
    lifespan=lifespan
)
# @app.get("/api/users/health")
# def health():
#     return {"status": "ok"}

@app.get("/api/users/health")
def health_status():
    return {"status": "ok"}



settings = get_settings()

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with correlation ID"""
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    start_time = time.time()
    
    # Add correlation ID to response headers
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    
    # Log request
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        "HTTP request processed",
        service="user-management",
        correlation_id=correlation_id,
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration_ms=duration_ms,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    
    return response

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Include routers
# app.include_router(health.router, prefix="/api/users", tags=["Health"])
# app.include_router(auth.router, prefix="/api/users", tags=["Authentication"])
# app.include_router(users.router, prefix="/api/users", tags=["Users"])

app.include_router(health_router, prefix="/api/users", tags=["Health"])
app.include_router(auth_router, prefix="/api/users", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "user-management",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/users/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use our structured logging
    )