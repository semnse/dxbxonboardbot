"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database.connection import get_db

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "ok",
        "service": "onboarding-bot"
    }


@router.get("/db")
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """Database connection health check"""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/full")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """Full health check with all dependencies"""
    health_status = {
        "status": "ok",
        "database": "unknown",
        "redis": "unknown",
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Note: Redis health check would be added here

    return health_status


@router.get("/test-bitrix/{item_id}")
async def test_bitrix(item_id: int):
    """Test Bitrix integration"""
    from app.services.bitrix_polling_service import BitrixPollingService
    
    bitrix = BitrixPollingService()
    result = await bitrix.get_item_by_id(item_id)
    
    return {
        "item_id": item_id,
        "found": result is not None,
        "title": result.get("title", "")[:100] if result else None,
        "stage": result.get("stageId") if result else None,
        "telegram": result.get("ufCrm20_1747732557645") if result else None,
    }
