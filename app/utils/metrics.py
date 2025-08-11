from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
from functools import wraps
from typing import Dict

# Define metrics
navigation_counter = Counter(
    'browser_navigations_total',
    'Total number of navigations',
    ['status', 'domain']
)

navigation_duration = Histogram(
    'browser_navigation_duration_seconds',
    'Navigation duration in seconds',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)

active_tabs = Gauge(
    'browser_active_tabs',
    'Number of active browser tabs'
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

error_counter = Counter(
    'browser_errors_total',
    'Total browser errors',
    ['error_type']
)

# Metrics decorator
def track_metrics(metric_name: str):
    """Decorator to track function metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_counter.labels(error_type=type(e).__name__).inc()
                raise
            finally:
                duration = time.time() - start_time
                
                if metric_name == "navigation":
                    navigation_counter.labels(
                        status=status,
                        domain=kwargs.get('domain', 'unknown')
                    ).inc()
                    navigation_duration.observe(duration)
        
        return wrapper
    return decorator

class MetricsCollector:
    """Collect and expose metrics"""
    
    def __init__(self):
        self.custom_metrics: Dict[str, float] = {}
    
    def record_custom_metric(self, name: str, value: float):
        """Record custom metric"""
        self.custom_metrics[name] = value
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest()
    
    def get_stats(self) -> Dict:
        """Get metrics as dictionary"""
        return {
            "navigations": {
                "total": navigation_counter._value.sum(),
                "success": navigation_counter.labels(status="success")._value.get(),
                "errors": navigation_counter.labels(status="error")._value.get()
            },
            "cache": {
                "hits": cache_hits._value.sum(),
                "misses": cache_misses._value.sum(),
                "hit_rate": cache_hits._value.sum() / (cache_hits._value.sum() + cache_misses._value.sum() + 1)
            },
            "tabs": {
                "active": active_tabs._value.get()
            },
            "custom": self.custom_metrics
        }

# Add metrics endpoint to FastAPI
from fastapi import Response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    collector = MetricsCollector()
    return Response(
        content=collector.get_metrics(),
        media_type="text/plain"
    )
