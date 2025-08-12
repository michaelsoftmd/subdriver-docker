from fastapi import APIRouter, Depends
from typing import Annotated

from app.api.dependencies import CommonDeps

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post("/research")
async def research_workflow(
    topic: str,
    deps: CommonDeps = Depends()
):
    """Research workflow"""
    # Simple placeholder implementation
    return {
        "status": "success",
        "topic": topic,
        "message": "Research workflow would run here"
    }
