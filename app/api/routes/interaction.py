from fastapi import APIRouter, Depends
from typing import Annotated

from app.api.dependencies import get_element_service
from app.models.requests import ClickRequest, TypeRequest
from app.models.responses import ClickResponse
from app.services.element import ElementService

router = APIRouter(prefix="/interaction", tags=["interaction"])

@router.post("/click", response_model=ClickResponse)
async def click_element(
    request: ClickRequest,
    element_service: Annotated[ElementService, Depends(get_element_service)]
):
    """Click an element"""
    await element_service.click_element(
        selector=request.selector,
        text=request.text,
        wait_after=request.wait_after
    )
    
    return ClickResponse(
        selector=request.selector,
        text=request.text
    )

@router.post("/type")
async def type_text(
    request: TypeRequest,
    element_service: Annotated[ElementService, Depends(get_element_service)]
):
    """Type text into element"""
    # Implementation would go here
    return {"status": "success", "message": "Text typed"}
