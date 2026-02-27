"""
API Routes модуль
"""
from app.api.routes.webhook import router as webhook_router
from app.api.routes.health import router as health_router

__all__ = ["webhook_router", "health_router"]
