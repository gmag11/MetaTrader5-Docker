"""Health check endpoints."""

from fastapi import APIRouter

from ..state import get_engine

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns basic service health status.
    """
    try:
        engine = get_engine()
        status = engine.get_status()

        return {
            "status": "healthy" if status["running"] else "degraded",
            "running": status["running"],
            "master_connected": status["master"]["connected"],
            "slaves_connected": sum(
                1 for s in status["slaves"].values() if s["connected"]
            ),
            "slaves_total": len(status["slaves"]),
            "active_mappings": status["active_mappings"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("/status")
async def get_status():
    """
    Get detailed service status.

    Returns complete status including all accounts and mappings count.
    """
    engine = get_engine()
    return engine.get_status()


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Returns 200 if the service is ready to handle requests.
    """
    engine = get_engine()
    status = engine.get_status()

    if not status["running"]:
        return {"ready": False, "reason": "Engine not running"}

    if not status["master"]["connected"]:
        return {"ready": False, "reason": "Master not connected"}

    if not any(s["connected"] for s in status["slaves"].values()):
        return {"ready": False, "reason": "No slaves connected"}

    return {"ready": True}
