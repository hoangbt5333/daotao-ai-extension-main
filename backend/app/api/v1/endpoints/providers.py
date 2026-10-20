"""
Provider endpoints
"""
from fastapi import APIRouter, Depends
from app.models.schemas.responses import ProviderResponse
from app.services.llm.base import get_llm_service
from app.api.dependencies import get_llm_service as get_llm_service_dep
from app.config.settings import get_llm_settings

router = APIRouter()


@router.get("/", response_model=ProviderResponse)
async def get_providers(llm_service = Depends(get_llm_service_dep)):
    """Get available LLM providers"""
    try:
        available = llm_service.get_available_providers()
        default = llm_service.get_default_provider()
        
        return ProviderResponse(
            success=True,
            available=available,
            default=default,
            message="Providers retrieved successfully"
        )
    except Exception as e:
        return ProviderResponse(
            success=False,
            available={},
            default=None,
            message=f"Failed to get providers: {str(e)}"
        )


@router.post("/reload")
async def reload_providers(llm_service = Depends(get_llm_service_dep)):
    """Reload LLM providers and settings"""
    try:
        llm_service.reload_settings()
        
        available = llm_service.get_available_providers()
        default = llm_service.get_default_provider()
        
        return ProviderResponse(
            success=True,
            available=available,
            default=default,
            message="Providers reloaded successfully"
        )
    except Exception as e:
        return ProviderResponse(
            success=False,
            available={},
            default=None,
            message=f"Failed to reload providers: {str(e)}"
        )


@router.get("/debug")
async def debug_settings():
    """Debug endpoint to show current settings"""
    try:
        settings = get_llm_settings()
        return {
            "success": True,
            "settings": {
                "default_provider": settings.default_provider,
                "gemini_api_key": "***" if settings.gemini_api_key else None,
                "openai_api_key": "***" if settings.openai_api_key else None,
                "deepseek_api_key": "***" if settings.deepseek_api_key else None,
                "all_fields": settings.dict()
            },
            "message": "Settings debug info"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get settings debug info"
        } 