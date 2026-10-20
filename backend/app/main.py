"""
Main FastAPI application entry point
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router

# Setup logging
setup_logging()

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    description="Daotao AI Extension Backend API for educational content processing and export"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create exports directory if it doesn't exist
os.makedirs(settings.file.export_dir, exist_ok=True)

# Mount static files for exports
app.mount("/exports", StaticFiles(directory=settings.file.export_dir), name="exports")

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "endpoints": {
            "upload": "/api/v1/upload/",
            "analyze": "/api/v1/analyze/",
            "export": "/api/v1/export/",
            "export-library": "/api/v1/export/library",
            "export-exam": "/api/v1/export/exam",
            "export-exam-subsection": "/api/v1/export/exam-subsection",
            "export-exam-questions-library": "/api/v1/export/exam-questions-library",
            "export-exam-section": "/api/v1/export/exam-section",
            "export-video-quiz": "/api/v1/export/video-quiz",
            "mapping": "/api/v1/mapping/pdfs",
            "providers": "/api/v1/providers/",
            "questions-process": "/api/v1/questions/process",
            "questions-from-library": "/api/v1/questions/from-library"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.version,
        "debug": settings.debug
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        reload=settings.debug
    ) 