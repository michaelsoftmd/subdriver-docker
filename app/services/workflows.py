import asyncio
from typing import List, Dict, Any
from app.core.exceptions import BrowserError

class WorkflowService:
    """Service for complex workflows with async optimization"""
    
    async def analyze_multiple_publications(self, urls: List[str]) -> List[Dict]:
        """Analyze multiple publications concurrently"""
        # Create tasks for concurrent execution
        tasks = []
        for url in urls:
            task = self._analyze_with_error_handling(url)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "url": urls[i],
                    "error": str(result)
                })
            else:
                successful_results.append(result)
        
        return {
            "successful": successful_results,
            "failed": failed_results,
            "total": len(urls),
            "success_rate": len(successful_results) / len(urls)
        }
    
    async def _analyze_with_error_handling(self, url: str) -> Dict:
        """Analyze single publication with error handling"""
        try:
            return await self._analyze_publication(url)
        except Exception as e:
            # Log error but don't fail entire batch
            return {"url": url, "error": str(e)}
    
    async def parallel_data_extraction(self, page, selectors: List[str]):
        """Extract data from multiple selectors in parallel"""
        tasks = []
        for selector in selectors:
            task = page.find(selector)
            tasks.append(task)
        
        elements = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for selector, element in zip(selectors, elements):
            if not isinstance(element, Exception) and element:
                results[selector] = await element.text
            else:
                results[selector] = None
        
        return results
    
    async def rate_limited_batch_operation(self, operations: List, rate_limit: float = 1.0):
        """Execute operations with rate limiting"""
        results = []
        
        for i, operation in enumerate(operations):
            # Execute operation
            result = await operation()
            results.append(result)
            
            # Rate limit (except for last item)
            if i < len(operations) - 1:
                await asyncio.sleep(rate_limit)
        
        return results
