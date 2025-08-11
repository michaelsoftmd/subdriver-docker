from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from app.api.dependencies import get_browser_manager, get_rate_limiter, CommonDeps
from app.core.browser import BrowserManager
from app.utils.rate_limiter import RateLimiter
from app.models.requests import NavigationRequest
from app.models.responses import NavigationResponse

router = APIRouter(prefix="/navigation", tags=["navigation"])

@router.post("/navigate")
async def navigate(
    request: NavigationRequest,
    browser: Annotated[BrowserManager, Depends(get_browser_manager)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)]
):
    """Navigate to URL with dependency injection"""
    # Rate limit check
    await rate_limiter.check_rate_limit(request.url)
    
    # Use injected browser manager
    result = await browser.navigate(
        url=request.url,
        wait_for=request.wait_for
    )
    
    return NavigationResponse(**result)

@router.post("/navigate-with-all")
async def navigate_with_all_deps(
    request: NavigationRequest,
    deps: CommonDeps = Depends()
):
    """Example using bundled dependencies"""
    # Access all dependencies through deps
    await deps.rate_limiter.check_rate_limit(request.url)
    result = await deps.browser.navigate(request.url)
    
    # Cache the result
    await deps.cache.set(f"nav:{request.url}", result)
    
    return result

