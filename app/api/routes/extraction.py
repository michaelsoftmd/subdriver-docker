from fastapi import APIRouter, Depends
from typing import Annotated

from app.api.dependencies import get_browser_manager
from app.core.browser import BrowserManager
from app.models.requests import ExtractRequest
from app.models.responses import ExtractResponse

router = APIRouter(prefix="/extraction", tags=["extraction"])

@router.post("/extract", response_model=ExtractResponse)
async def extract_content(
    request: ExtractRequest,
    browser: Annotated[BrowserManager, Depends(get_browser_manager)]
):
    """Extract content from page"""
    tab_info = await browser.get_tab()
    
    try:
        results = []
        
        if request.selector:
            if request.extract_all:
                elements = await tab_info.tab.find_all(request.selector)
            else:
                element = await tab_info.tab.find(request.selector)
                elements = [element] if element else []
        else:
            # Extract from whole page
            elements = [tab_info.tab]
        
        for element in elements:
            if not element:
                continue
            
            item = {}
            if request.extract_text:
                item["text"] = await element.text if hasattr(element, 'text') else None
            if request.extract_href:
                item["href"] = await element.get_attribute("href") if hasattr(element, 'get_attribute') else None
            
            if item:
                results.append(item)
        
        return ExtractResponse(
            count=len(results),
            data=results if request.extract_all else (results[0] if results else None)
        )
        
    finally:
        await browser.release_tab(tab_info)
