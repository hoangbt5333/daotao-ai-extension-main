"""
Analysis endpoints
"""
from fastapi import APIRouter, Form, Query, Depends
from typing import Optional
from app.services.llm.base import LLMService
from app.models.schemas.requests import AnalysisRequest
from app.models.schemas.responses import AnalysisResponse
from app.core.exceptions import LLMServiceError
from app.api.dependencies import get_llm_service

router = APIRouter()


@router.post("/", response_model=AnalysisResponse)
async def analyze_text(
    text: str = Form(...),
    provider: Optional[str] = Query(None),
    custom_prompt: Optional[str] = Form(None),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Analyze text and generate outline + questions"""
    try:
        # Create analysis request
        request = AnalysisRequest(text=text, provider=provider)
        
        # Use custom prompt if provided, otherwise use default from provider
        system_prompt = custom_prompt
        
        # Analyze text using LLM service
        result = llm_service.analyze_text(
            text=request.text,
            provider_name=request.provider,
            prompt=system_prompt
        )
        
        return AnalysisResponse(
            success=True,
            data=result,
            provider=request.provider or llm_service.get_default_provider(),
            message="Text analyzed successfully"
        )
    except LLMServiceError as e:
        return AnalysisResponse(
            success=False,
            data={},
            provider=provider,
            message=str(e)
        )
    except Exception as e:
        return AnalysisResponse(
            success=False,
            data={},
            provider=provider,
            message=f"Unexpected error: {str(e)}"
        ) 