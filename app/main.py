# Corrected main.py with fixed parameter ordering
"""
Zendriver Browser Automation API - Corrected Version
Fixed parameter ordering issues and improved structure
"""

import asyncio
from fastapi import FastAPI, HTTPException, Query, Depends
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime
import os

# Import refactored modules
from app.core.config import Settings, get_settings
from app.core.browser import BrowserManager
from app.core.database import DatabaseManager, init_db, get_db
from app.core.exceptions import BrowserError, ElementNotFoundError
from app.models.requests import NavigationRequest, ClickRequest, SubstackPublicationRequest
from app.services.element import ElementService
from app.services.substack import SubstackService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================
# Dependency injection functions
# ===========================

# Browser manager singleton
_browser_manager = None

def get_browser_manager() -> BrowserManager:
    """Get browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(get_settings())
    return _browser_manager

def get_database_manager() -> DatabaseManager:
    """Get database manager instance"""
    return DatabaseManager()

def get_element_service(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)]
) -> ElementService:
    """Get element service instance"""
    return ElementService(browser_manager)

def get_substack_service(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)],
    db_session: Annotated[Any, Depends(get_db)]
) -> SubstackService:
    """Get Substack service instance"""
    return SubstackService(browser_manager, db_session)

# ===========================
# Application Lifespan
# ===========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting application...")
    init_db()  # Initialize database tables
    yield
    # Shutdown
    logger.info("Shutting down application...")
    browser_manager = get_browser_manager()
    if browser_manager:
        await browser_manager.close_browser()

# Create FastAPI app
app = FastAPI(
    title="Zendriver Browser Automation API",
    description="Browser automation API with Zendriver",
    version="3.0.0",
    lifespan=lifespan
)

# ===========================
# API Routes
# ===========================

@app.get("/")
async def root():
    """API information"""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.version,
        "status": "ready"
    }

@app.get("/health")
async def health_check(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)],
    db_manager: Annotated[DatabaseManager, Depends(get_database_manager)]
):
    """Health check endpoint"""
    browser_status = browser_manager.browser is not None
    
    # Check database
    db_healthy = False
    try:
        sessions = db_manager.get_research_sessions(limit=1)
        db_healthy = True
    except:
        pass
    
    return {
        "status": "healthy",
        "browser_running": browser_status,
        "database_healthy": db_healthy,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/navigate")
async def navigate_to_url(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)],
    request: NavigationRequest
):
    """Navigate to a URL"""
    try:
        result = await browser_manager.navigate(
            url=str(request.url),
            wait_for=request.wait_for,
            wait_timeout=request.wait_timeout
        )
        
        return {
            "status": "success",
            "url": result["url"],
            "title": result["title"],
            "message": f"Successfully navigated to {request.url}"
        }
    except BrowserError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/click")
async def click_element(
    element_service: Annotated[ElementService, Depends(get_element_service)],
    request: ClickRequest
):
    """Click an element"""
    try:
        await element_service.click_element(
            selector=request.selector,
            text=request.text,
            wait_after=request.wait_after
        )
        
        return {
            "status": "success",
            "message": "Element clicked successfully"
        }
    except ElementNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BrowserError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/substack/subscribe")
async def subscribe_to_substack(
    substack_service: Annotated[SubstackService, Depends(get_substack_service)],
    request: SubstackPublicationRequest
):
    """Subscribe to a Substack publication"""
    try:
        result = await substack_service.subscribe_to_publication(str(request.publication_url))
        return result
    except ElementNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BrowserError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/substack/interact")
async def interact_with_substack_post(
    substack_service: Annotated[SubstackService, Depends(get_substack_service)],
    action: str = Query(..., description="Action: like, comment, share"),
    comment_text: Optional[str] = Query(None, description="Comment text if commenting")
):
    """Interact with a Substack post - FIXED parameter ordering"""
    try:
        result = await substack_service.interact_with_post(action, comment_text)
        return result
    except ElementNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BrowserError as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===========================
# Workflow endpoints
# ===========================

class WorkflowService:
    """Service for managing complex workflows"""
    
    def __init__(self, browser_manager: BrowserManager, db_manager: DatabaseManager,
                 substack_service: SubstackService):
        self.browser_manager = browser_manager
        self.db_manager = db_manager
        self.substack_service = substack_service
    
    async def research_workflow(self, topic: str, max_publications: int = 10) -> Dict[str, Any]:
        """Execute research workflow with proper error handling and progress tracking"""
        workflow_id = f"research_{topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = {
            "workflow_id": workflow_id,
            "topic": topic,
            "publications_analyzed": [],
            "errors": [],
            "status": "in_progress"
        }
        
        try:
            # Search for topic
            await self.browser_manager.navigate(f"https://substack.com/search?q={topic}")
            await asyncio.sleep(2)
            
            # Get tab info
            tab_info = await self.browser_manager.get_tab()
            
            try:
                # Process publications with error handling for each
                pub_links = await tab_info.tab.find_all('a[href*="substack.com"]')
                
                for i, link in enumerate(pub_links[:max_publications]):
                    try:
                        pub_url = await link.get_attribute('href')
                        if pub_url and '/p/' not in pub_url:
                            # Process publication
                            pub_data = await self._analyze_publication(pub_url)
                            results["publications_analyzed"].append(pub_data)
                    except Exception as e:
                        logger.error(f"Error processing publication {i}: {e}")
                        results["errors"].append({
                            "index": i,
                            "error": str(e)
                        })
                
                results["status"] = "completed"
            finally:
                await self.browser_manager.release_tab(tab_info)
            
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
        
        finally:
            # Always save results, even if partially complete
            self.db_manager.save_research_session(workflow_id, topic, results)
        
        return results
    
    async def _analyze_publication(self, pub_url: str) -> Dict[str, Any]:
        """Analyze a single publication"""
        await self.browser_manager.navigate(pub_url)
        tab_info = await self.browser_manager.get_tab()
        
        try:
            return {
                "url": pub_url,
                "name": await self._safe_extract(tab_info.tab, 'h1'),
                "description": await self._safe_extract(tab_info.tab, '[class*="description"]'),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            await self.browser_manager.release_tab(tab_info)
    
    async def _safe_extract(self, tab, selector: str) -> Optional[str]:
        """Safely extract text from element"""
        try:
            elem = await tab.find(selector)
            if elem:
                return await elem.text
        except:
            pass
        return None

@app.post("/workflow/research")
async def execute_research_workflow(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)],
    db_manager: Annotated[DatabaseManager, Depends(get_database_manager)],
    substack_service: Annotated[SubstackService, Depends(get_substack_service)],
    topic: str = Query(..., description="Research topic"),
    max_publications: int = Query(10, description="Max publications to analyze")
):
    """Execute research workflow - FIXED parameter ordering"""
    workflow_service = WorkflowService(browser_manager, db_manager, substack_service)
    result = await workflow_service.research_workflow(topic, max_publications)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

# ===========================
# Run the application
# ===========================
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,  # Disable for production
        log_level="info"
    )
