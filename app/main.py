from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import get_settings
from app.core.database import init_db
from app.api.routes import navigation, interaction, extraction, substack, workflows
from app.utils.logger import setup_logger
from app.utils.metrics import MetricsCollector

# Get settings
settings = get_settings()

# Setup logging
logger = setup_logger("main", level=settings.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application...")
    
    # Initialize database
    init_db()
    
    # Initialize services
    app.state.metrics = MetricsCollector()
    
    yield
    
    logger.info("Shutting down application...")

# Create app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan
)

# Include routers
app.include_router(navigation.router, prefix="/api/v1")
app.include_router(interaction.router, prefix="/api/v1")
app.include_router(extraction.router, prefix="/api/v1")
app.include_router(substack.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")

# Add middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "json": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "formatter": "json",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"]
            }
        }
    )
