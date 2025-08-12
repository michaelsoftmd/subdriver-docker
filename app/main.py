# Improved structure - main.py
"""
Zendriver Browser Automation API - Refactored Version
Split into multiple modules for better organization
"""

import asyncio
from fastapi import FastAPI, HTTPException, Query, Depends
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

# Import refactored modules
from app.core.config import Settings, get_settings
from app.core.browser import BrowserManager
from app.core.database import DatabaseManager
from app.core.exceptions import BrowserError, ElementNotFoundError
from app.api import navigation, interaction, extraction, social, substack, workflows
from app.models.requests import *
from app.utils.human_behavior import HumanBehavior
from app.utils.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================
# app/core/config.py
# ===========================
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "Zendriver Browser Automation API"
    version: str = "3.0.0"
    
    # Browser settings
    browser_headless: bool = False
    browser_args: List[str] = [
        "--enable-features=UseOzonePlatform",
        "--ozone-platform=wayland",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process"
    ]
    
    # Data paths
    data_dir: str = "/app/data"
    profiles_dir: str = "/app/data/profiles"
    exports_dir: str = "/app/data/exports"
    
    # Rate limiting
    rate_limit_delay: float = 2.0
    
    # Database
    database_path: str = "/app/data/research.db"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# ===========================
# app/core/browser.py
# ===========================
import zendriver as zd
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class BrowserManager:
    """Centralized browser management with singleton pattern"""
    
    _instance: Optional['BrowserManager'] = None
    _browser: Optional[Any] = None
    _current_page: Optional[Any] = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.settings = get_settings()
    
    async def get_browser(self):
        """Get or create browser instance with thread safety"""
        async with self._lock:
            if not self._browser:
                logger.info("Starting new browser instance")
                self._browser = await zd.start(
                    headless=self.settings.browser_headless,
                    browser_args=self.settings.browser_args
                )
            return self._browser
    
    async def get_current_page(self):
        """Get current page or create new one"""
        browser = await self.get_browser()
        
        if self._current_page is None:
            if browser.tabs and len(browser.tabs) > 0:
                self._current_page = browser.tabs[0]
            else:
                logger.info("Creating new page")
                self._current_page = await browser.get("about:blank")
                await asyncio.sleep(1)
        
        return self._current_page
    
    async def set_current_page(self, page):
        """Set the current page"""
        self._current_page = page
    
    async def close_browser(self):
        """Safely close browser"""
        async with self._lock:
            if self._browser:
                logger.info("Shutting down browser")
                try:
                    await self._browser.stop()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
                finally:
                    self._browser = None
                    self._current_page = None
    
    async def navigate(self, url: str, wait_for: Optional[str] = None, timeout: int = 10):
        """Navigate to URL with proper error handling"""
        try:
            url = self._ensure_url_protocol(url)
            browser = await self.get_browser()
            
            page = await browser.get(url)
            self._current_page = page
            
            await asyncio.sleep(2)  # Basic page load wait
            
            if wait_for:
                try:
                    await page.find(wait_for, timeout=timeout)
                    logger.info(f"Found wait element: {wait_for}")
                except:
                    logger.warning(f"Wait element not found: {wait_for}")
            
            await page.update_target()
            return {
                "url": page.url,
                "title": page.target.title if page.target else "No title"
            }
            
        except Exception as e:
            raise BrowserError(f"Navigation failed: {str(e)}")
    
    @staticmethod
    def _ensure_url_protocol(url: str) -> str:
        """Ensure URL has a protocol"""
        if not url.startswith(('http://', 'https://', 'file://', 'about:', 'chrome://')):
            return f'https://{url}'
        return url

# ===========================
# app/core/database.py
# ===========================
import sqlite3
from contextlib import contextmanager
import json
import os
from typing import Dict, Any, List, Optional

class DatabaseManager:
    """Database operations manager with better abstraction"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_settings().database_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS research_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT UNIQUE,
                    topic TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data JSON
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS collected_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    publication TEXT,
                    title TEXT,
                    author TEXT,
                    published_date TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data JSON
                )
            ''')
    
    def save_research_session(self, workflow_id: str, topic: str, data: Dict[str, Any]):
        """Save research session data"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO research_sessions (workflow_id, topic, data)
                VALUES (?, ?, ?)
            ''', (workflow_id, topic, json.dumps(data)))
    
    def get_research_sessions(self, workflow_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get research sessions"""
        with self.get_connection() as conn:
            if workflow_id:
                cursor = conn.execute(
                    "SELECT * FROM research_sessions WHERE workflow_id = ?",
                    (workflow_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM research_sessions ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_collected_post(self, post_data: Dict[str, Any]):
        """Save collected post data"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO collected_posts 
                (url, publication, title, author, published_date, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                post_data.get('url'),
                post_data.get('publication'),
                post_data.get('title'),
                post_data.get('author'),
                post_data.get('published_date'),
                json.dumps(post_data)
            ))

# ===========================
# app/core/exceptions.py
# ===========================
class BrowserError(Exception):
    """Browser operation error"""
    pass

class ElementNotFoundError(Exception):
    """Element not found error"""
    pass

class NavigationError(Exception):
    """Navigation error"""
    pass

# ===========================
# app/services/element_service.py
# ===========================
class ElementService:
    """Service for element operations with better error handling"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
    
    async def find_element(self, selector: Optional[str] = None, text: Optional[str] = None, 
                          timeout: int = 10):
        """Find element with comprehensive error handling"""
        page = await self.browser_manager.get_current_page()
        
        try:
            if selector:
                element = await page.find(selector, timeout=timeout)
            elif text:
                element = await page.find(text, best_match=True, timeout=timeout)
            else:
                raise ValueError("Either selector or text must be provided")
            
            if not element:
                raise ElementNotFoundError(f"Element not found: {selector or text}")
            
            return element
            
        except asyncio.TimeoutError:
            raise ElementNotFoundError(f"Timeout finding element: {selector or text}")
        except Exception as e:
            raise BrowserError(f"Error finding element: {str(e)}")
    
    async def click_element(self, element, wait_after: float = 1.0):
        """Click element with proper waiting"""
        await element.click()
        await asyncio.sleep(wait_after)
    
    async def type_text(self, element, text: str, clear_first: bool = True, 
                       delay: float = 0.1, press_enter: bool = False):
        """Type text into element"""
        if clear_first:
            await element.clear()
            await asyncio.sleep(0.1)
        
        await element.send_keys(text, delay=delay)
        
        if press_enter:
            await element.send_keys("\n")
            await asyncio.sleep(1)

# ===========================
# app/services/substack_service.py
# ===========================
class SubstackService:
    """Specialized service for Substack operations"""
    
    SELECTORS = {
        "subscribe": [
            'button[class*="subscribe-button"]',
            'button:has-text("Subscribe")',
            'button:has-text("Sign up")',
        ],
        "like": [
            'button[aria-label*="Like"]',
            'button:has-text("Like")',
            '.like-button',
        ],
        "comment": [
            'button:has-text("Comment")',
            'button[aria-label*="Comment"]',
            '.comment-button'
        ],
        "share": [
            'button[aria-label*="Share"]',
            'button:has-text("Share")',
            '.share-button'
        ]
    }
    
    def __init__(self, browser_manager: BrowserManager, element_service: ElementService):
        self.browser_manager = browser_manager
        self.element_service = element_service
    
    async def subscribe_to_publication(self, publication_url: str):
        """Subscribe to a Substack publication"""
        # Navigate to publication
        await self.browser_manager.navigate(publication_url)
        
        # Try to find and click subscribe button
        for selector in self.SELECTORS["subscribe"]:
            try:
                element = await self.element_service.find_element(selector=selector, timeout=3)
                if element:
                    button_text = await element.text
                    
                    if "Subscribed" in button_text or "Following" in button_text:
                        return {
                            "status": "already_subscribed",
                            "message": "Already subscribed or following"
                        }
                    
                    await self.element_service.click_element(element)
                    return {
                        "status": "success",
                        "message": f"Clicked {button_text} button"
                    }
            except ElementNotFoundError:
                continue
        
        raise ElementNotFoundError("Subscribe button not found")
    
    async def interact_with_post(self, action: str, comment_text: Optional[str] = None):
        """Interact with a Substack post"""
        selectors = self.SELECTORS.get(action, [])
        
        for selector in selectors:
            try:
                element = await self.element_service.find_element(selector=selector, timeout=3)
                if element:
                    await self.element_service.click_element(element)
                    
                    # Handle comment text if provided
                    if action == "comment" and comment_text:
                        await self._post_comment(comment_text)
                    
                    return {"status": "success", "action": action}
            except ElementNotFoundError:
                continue
        
        raise ElementNotFoundError(f"Could not find {action} button")
    
    async def _post_comment(self, comment_text: str):
        """Post a comment"""
        comment_selectors = [
            'div[role="textbox"][contenteditable="true"]',
            'textarea[placeholder*="comment"]',
            '.comment-input'
        ]
        
        for selector in comment_selectors:
            try:
                element = await self.element_service.find_element(selector=selector, timeout=3)
                if element:
                    await element.click()
                    await element.send_keys(comment_text)
                    
                    # Find and click post button
                    post_btn = await self.element_service.find_element(
                        text="Post", timeout=3
                    )
                    if post_btn:
                        await post_btn.click()
                    break
            except ElementNotFoundError:
                continue

# ===========================
# app/api/dependencies.py
# ===========================
from typing import Annotated

# Dependency injection for services
async def get_browser_manager() -> BrowserManager:
    """Get browser manager instance"""
    return BrowserManager()

async def get_database_manager() -> DatabaseManager:
    """Get database manager instance"""
    return DatabaseManager()

async def get_element_service(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)]
) -> ElementService:
    """Get element service instance"""
    return ElementService(browser_manager)

async def get_substack_service(
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)],
    element_service: Annotated[ElementService, Depends(get_element_service)]
) -> SubstackService:
    """Get Substack service instance"""
    return SubstackService(browser_manager, element_service)

# ===========================
# Main Application Setup
# ===========================

# Initialize managers
browser_manager = BrowserManager()
db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting application...")
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await browser_manager.close_browser()

# Create FastAPI app
app = FastAPI(
    title="Zendriver Browser Automation API",
    description="Refactored browser automation API with better organization",
    version="3.0.0",
    lifespan=lifespan
)

# ===========================
# API Routes (simplified examples)
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
    browser_status = browser_manager._browser is not None
    
    # Check database
    db_healthy = False
    try:
        with db_manager.get_connection() as conn:
            conn.execute("SELECT 1")
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
    request: NavigationRequest,
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)]
):
    """Navigate to a URL"""
    try:
        result = await browser_manager.navigate(
            url=request.url,
            wait_for=request.wait_for,
            timeout=request.wait_timeout
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
    request: ClickRequest,
    element_service: Annotated[ElementService, Depends(get_element_service)]
):
    """Click an element"""
    try:
        element = await element_service.find_element(
            selector=request.selector,
            text=request.text
        )
        await element_service.click_element(element, wait_after=request.wait_after)
        
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
    request: SubstackPublicationRequest,
    substack_service: Annotated[SubstackService, Depends(get_substack_service)]
):
    """Subscribe to a Substack publication"""
    try:
        result = await substack_service.subscribe_to_publication(request.publication_url)
        return result
    except ElementNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BrowserError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/substack/interact")
async def interact_with_substack_post(
    action: str = Query(..., description="Action: like, comment, share"),
    comment_text: Optional[str] = Query(None, description="Comment text if commenting"),
    substack_service: Annotated[SubstackService, Depends(get_substack_service)]
):
    """Interact with a Substack post"""
    try:
        result = await substack_service.interact_with_post(action, comment_text)
        return result
    except ElementNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BrowserError as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===========================
# Example of improved workflow with better error handling
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
            
            # Process publications with error handling for each
            page = await self.browser_manager.get_current_page()
            pub_links = await page.find_all('a[href*="substack.com"]')
            
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
        page = await self.browser_manager.get_current_page()
        
        return {
            "url": pub_url,
            "name": await self._safe_extract(page, 'h1'),
            "description": await self._safe_extract(page, '[class*="description"]'),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _safe_extract(self, page, selector: str) -> Optional[str]:
        """Safely extract text from element"""
        try:
            elem = await page.find(selector)
            if elem:
                return await elem.text
        except:
            pass
        return None

# Register workflow endpoints
@app.post("/workflow/research")
async def execute_research_workflow(
    topic: str = Query(..., description="Research topic"),
    max_publications: int = Query(10, description="Max publications to analyze"),
    browser_manager: Annotated[BrowserManager, Depends(get_browser_manager)],
    db_manager: Annotated[DatabaseManager, Depends(get_database_manager)],
    substack_service: Annotated[SubstackService, Depends(get_substack_service)]
):
    """Execute research workflow"""
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
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # Enable for development
        log_level="info"
    )
