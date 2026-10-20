"""
API v1 router
"""
from fastapi import APIRouter
from app.api.v1.endpoints import export, providers, mapping, outline, questions

# Create main API router
api_router = APIRouter()

# Include endpoint routers
# Removed legacy upload and analyze routes
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(mapping.router, prefix="/mapping", tags=["mapping"]) 
api_router.include_router(outline.router, prefix="/outline", tags=["outline"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])