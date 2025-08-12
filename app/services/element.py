import asyncio
from typing import Optional
from app.core.browser import BrowserManager
from app.core.exceptions import ElementNotFoundError, BrowserError

class ElementService:
    """Service for element operations with better error handling"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
    
    async def find_element(self, selector: Optional[str] = None, text: Optional[str] = None, 
                          timeout: int = 10):
        """Find element with comprehensive error handling"""
        tab_info = await self.browser_manager.get_tab()
        
        try:
            if selector:
                element = await tab_info.tab.find(selector, timeout=timeout)
            elif text:
                element = await tab_info.tab.find(text, best_match=True, timeout=timeout)
            else:
                raise ValueError("Either selector or text must be provided")
            
            if not element:
                raise ElementNotFoundError(f"Element not found: {selector or text}")
            
            return element
            
        except asyncio.TimeoutError:
            raise ElementNotFoundError(f"Timeout finding element: {selector or text}")
        except Exception as e:
            raise BrowserError(f"Error finding element: {str(e)}")
        finally:
            await self.browser_manager.release_tab(tab_info)
    
    async def click_element(self, selector: Optional[str] = None, 
                           text: Optional[str] = None, wait_after: float = 1.0):
        """Click an element"""
        element = await self.find_element(selector, text)
        await element.click()
        await asyncio.sleep(wait_after)
        return True
    
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
