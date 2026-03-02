"""
FastAPI Application Entry Point

Main application configuration, middleware, and route registration.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.database.connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Application lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting Auto-KenBurns Video Generator API...")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Create upload directories
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(os.path.join(upload_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(upload_dir, "audios"), exist_ok=True)

    output_dir = os.getenv("OUTPUT_DIR", "./output")
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title="Auto-KenBurns Video Generator",
    description="API for generating Ken-Burns effect videos from images and audio",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    import traceback
    error_detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception: {exc}\n{error_detail}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "request_id": id(request),
            }
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Auto-KenBurns Video Generator",
        "version": "1.0.0"
    }


# Import and register routers
from backend.routers import upload, project, render, websocket, settings, quick_render

app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(project.router, prefix="/api/v1", tags=["Projects"])
app.include_router(render.router, prefix="/api/v1", tags=["Render"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(settings.router, prefix="/api/v1", tags=["Settings"])
app.include_router(quick_render.router, prefix="/api/v1", tags=["QuickRender"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Auto-KenBurns Video Generator API",
        "docs": "/docs",
        "health": "/health"
    }
