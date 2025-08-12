import asyncio
from typing import Optional, List, Set, Dict, Any
from dataclasses import dataclass
import zendriver as zd
from queue import Queue
import time

@dataclass
class TabInfo:
    """Information about a browser tab"""
    tab: any  # zendriver tab object
    url: str
    in_use: bool = False
    created_at: float = None
    last_used: float = None

class TabPool:
    """Manage a pool of browser tabs for reuse"""
    
    def __init__(self, max_tabs: int = 5, max_idle_time: int = 300):
        self.max_tabs = max_tabs
        self.max_idle_time = max_idle_time  # seconds
        self.available_tabs: asyncio.Queue = asyncio.Queue()
        self.in_use_tabs: Set[TabInfo] = set()
        self.lock = asyncio.Lock()
        self.browser = None
    
    async def initialize(self, browser):
        """Initialize pool with browser instance"""
        self.browser = browser
    
    async def acquire(self, url: Optional[str] = None) -> TabInfo:
        """Get a tab from pool or create new one"""
        async with self.lock:
            # Try to get an available tab
            try:
                tab_info = await asyncio.wait_for(
                    self.available_tabs.get(), 
                    timeout=0.1
                )
                
                # Check if tab is still valid
                if time.time() - tab_info.last_used > self.max_idle_time:
                    # Tab too old, close it and create new
                    await tab_info.tab.close()
                    tab_info = await self._create_tab(url)
                else:
                    # Navigate to new URL if provided
                    if url:
                        await tab_info.tab.get(url)
                        tab_info.url = url
                
            except asyncio.TimeoutError:
                # No available tabs, create new if under limit
                if len(self.in_use_tabs) < self.max_tabs:
                    tab_info = await self._create_tab(url)
                else:
                    # Wait for a tab to become available
                    tab_info = await self.available_tabs.get()
                    if url:
                        await tab_info.tab.get(url)
                        tab_info.url = url
            
            tab_info.in_use = True
            tab_info.last_used = time.time()
            self.in_use_tabs.add(tab_info)
            
            return tab_info
    
    async def release(self, tab_info: TabInfo):
        """Return tab to pool"""
        async with self.lock:
            tab_info.in_use = False
            tab_info.last_used = time.time()
            
            if tab_info in self.in_use_tabs:
                self.in_use_tabs.remove(tab_info)
            
            # Clear sensitive data from tab
            await tab_info.tab.evaluate("window.localStorage.clear()")
            await tab_info.tab.evaluate("window.sessionStorage.clear()")
            
            await self.available_tabs.put(tab_info)
    
    async def _create_tab(self, url: Optional[str] = None) -> TabInfo:
        """Create a new tab"""
        tab = await self.browser.get(url or "about:blank")
        return TabInfo(
            tab=tab,
            url=url or "about:blank",
            created_at=time.time(),
            last_used=time.time()
        )
    
    async def cleanup(self):
        """Close all tabs and cleanup"""
        async with self.lock:
            # Close in-use tabs
            for tab_info in self.in_use_tabs:
                await tab_info.tab.close()
            
            # Close available tabs
            while not self.available_tabs.empty():
                tab_info = await self.available_tabs.get()
                await tab_info.tab.close()

class BrowserManager:
    """Enhanced browser manager with tab pooling"""
    
    def __init__(self, settings):
        self.settings = settings
        self.browser = None
        self.tab_pool = TabPool(max_tabs=5)
        self.lock = asyncio.Lock()
    
    async def get_browser(self):
        """Get or create browser instance"""
        async with self.lock:
            if not self.browser:
                self.browser = await zd.start(
                    headless=self.settings.browser_headless,
                    browser_args=self.settings.browser_args
                )
                await self.tab_pool.initialize(self.browser)
            return self.browser
    
    async def get_tab(self, url: Optional[str] = None) -> TabInfo:
        """Get a tab from pool"""
        await self.get_browser()  # Ensure browser exists
        return await self.tab_pool.acquire(url)
    
    async def release_tab(self, tab_info: TabInfo):
        """Release tab back to pool"""
        await self.tab_pool.release(tab_info)
    
    async def navigate_with_pool(self, url: str):
        """Navigate using pooled tab"""
        tab_info = await self.get_tab(url)
        try:
            # Do navigation work
            await tab_info.tab.wait(2)
            title = await tab_info.tab.evaluate("document.title")
            return {"url": url, "title": title}
        finally:
            # Always release tab back to pool
            await self.release_tab(tab_info)
    
    async def navigate(self, url: str, wait_for: Optional[str] = None, 
                      wait_timeout: int = 10) -> Dict[str, Any]:
        """Navigate to URL with optional wait condition (NEW METHOD)"""
        tab_info = await self.get_tab(url)
        try:
            # Wait for page load
            await asyncio.sleep(2)
            
            # Optional wait for specific element
            if wait_for:
                try:
                    await tab_info.tab.find(wait_for, timeout=wait_timeout)
                except:
                    pass  # Element not found, but don't fail navigation
            
            # Get page title
            title = await tab_info.tab.evaluate("document.title")
            
            return {
                "url": url,
                "title": title
            }
        finally:
            # Always release tab back to pool
            await self.release_tab(tab_info)
