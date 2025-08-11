import logging
import json
from pythonjsonlogger import jsonlogger
from typing import Any, Dict
import sys

class ContextFilter(logging.Filter):
    """Add context to log records"""
    
    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        self.context = context
    
    def filter(self, record):
        for key, value in self.context.items():
            setattr(record, key, value)
        return True

def setup_logger(name: str, level: str = "INFO", context: Dict = None) -> logging.Logger:
    """Setup structured logger"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    
    # JSON formatter
    format_str = '%(timestamp)s %(level)s %(name)s %(message)s'
    formatter = jsonlogger.JsonFormatter(
        format_str,
        rename_fields={'levelname': 'level', 'asctime': 'timestamp'}
    )
    console_handler.setFormatter(formatter)
    
    # Add context filter if provided
    if context:
        console_handler.addFilter(ContextFilter(context))
    
    logger.addHandler(console_handler)
    
    return logger

# Usage in services
class SubstackService:
    def __init__(self):
        self.logger = setup_logger(
            "substack_service",
            context={"service": "substack", "version": "1.0"}
        )
    
    async def collect_posts(self, url: str):
        self.logger.info(
            "Starting post collection",
            extra={
                "url": url,
                "action": "collect_posts",
                "timestamp": time.time()
            }
        )
        
        try:
            # ... collection logic ...
            self.logger.info(
                "Collection completed",
                extra={
                    "url": url,
                    "posts_collected": len(posts),
                    "duration": time.time() - start_time
                }
            )
        except Exception as e:
            self.logger.error(
                "Collection failed",
                extra={
                    "url": url,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            )
