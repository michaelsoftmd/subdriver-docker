from fastapi import APIRouter, Depends
from typing import Annotated

from app.api.dependencies import get_substack_service
from app.services.substack import SubstackService
from app.models.requests import SubstackRequest

router = APIRouter(prefix="/substack", tags=["substack"])

@router.post("/subscribe")
async def subscribe(
    request: SubstackRequest,
    substack: Annotated[SubstackService, Depends(get_substack_service)]
):
    """Subscribe to Substack publication"""
    result = await substack.subscribe_to_publication(request.publication_url)
    return result
