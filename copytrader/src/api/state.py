"""Global state for the API."""

from typing import Optional

from fastapi import HTTPException

# Global reference to the engine
_engine = None


def set_engine(engine) -> None:
    """Set the global engine reference."""
    global _engine
    _engine = engine


def get_engine():
    """Get the global engine reference."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return _engine
