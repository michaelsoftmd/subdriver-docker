from typing import Annotated, Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.browser import BrowserManager
from app.core.database import get_db
from app.services.element import ElementService
from app.services.substack import SubstackService
from app.utils.cache import CacheManager
from app.utils.rate_limiter import RateLimiter

# Settings dependency
settings = get_settings()

# Browser manager singleton
_browser_manager = None

def get_browser_manager() -> BrowserManager:
    """Get or create browser manager singleton"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(settings)
    return _browser_manager

# Database session dependency
def get_db_session() -> Generator:
    """Get database session"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# Service dependencies
def get_element_service(
    browser: Annotated[BrowserManager, Depends(get_browser_manager)]
) -> ElementService:
    """Get element service with injected dependencies"""
    return ElementService(browser)

def get_substack_service(
    browser: Annotated[BrowserManager, Depends(get_browser_manager)],
    db: Annotated[Session, Depends(get_db_session)]
) -> SubstackService:
    """Get Substack service with dependencies"""
    return SubstackService(browser, db)

# Cache dependency
_cache_manager = None

def get_cache() -> CacheManager:
    """Get cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(settings)
    return _cache_manager

# Rate limiter dependency
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(settings)
    return _rate_limiter

# Common dependencies bundle
class CommonDeps:
    """Bundle common dependencies"""
    def __init__(
        self,
        browser: Annotated[BrowserManager, Depends(get_browser_manager)],
        db: Annotated[Session, Depends(get_db_session)],
        cache: Annotated[CacheManager, Depends(get_cache)],
        rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)]
    ):
        self.browser = browser
        self.db = db
        self.cache = cache
        self.rate_limiter = rate_limiter
