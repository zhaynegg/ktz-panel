from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas import AiSummaryResponse
from app.services.ai_analysis_ru import get_ai_analysis_service
from app.services.auth import get_current_user_from_request

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"], dependencies=[Depends(get_current_user_from_request)])


@router.get("/ai-summary", response_model=AiSummaryResponse)
async def get_ai_summary() -> AiSummaryResponse:
    return get_ai_analysis_service().summarize_last_window()
