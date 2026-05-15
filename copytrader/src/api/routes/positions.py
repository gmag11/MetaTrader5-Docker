"""Position management endpoints."""

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from ..state import get_engine

router = APIRouter()


class PositionMappingInfo(BaseModel):
    """Position mapping information."""

    master_ticket: int
    slave_ticket: int
    slave_name: str
    symbol: str
    master_volume: float
    slave_volume: float
    status: str


class PositionMappingsResponse(BaseModel):
    """Response containing all position mappings."""

    total: int
    mappings: Dict[int, List[PositionMappingInfo]]


@router.get("", response_model=PositionMappingsResponse)
async def list_positions():
    """
    List all active position mappings.

    Returns mapping between master positions and their slave copies.
    """
    engine = get_engine()
    mappings_dict = engine.get_position_mappings()

    # Convert to response model
    result = {}
    total = 0
    for master_ticket, mappings in mappings_dict.items():
        result[master_ticket] = [
            PositionMappingInfo(
                master_ticket=m["master_ticket"],
                slave_ticket=m["slave_ticket"],
                slave_name=m["slave_name"],
                symbol=m["symbol"],
                master_volume=m["master_volume"],
                slave_volume=m["slave_volume"],
                status=m["status"],
            )
            for m in mappings
        ]
        total += len(mappings)

    return PositionMappingsResponse(total=total, mappings=result)


@router.get("/master/{ticket}")
async def get_position_mapping(ticket: int):
    """
    Get mappings for a specific master position.

    Args:
        ticket: Master position ticket
    """
    engine = get_engine()
    mappings_dict = engine.get_position_mappings()

    if ticket not in mappings_dict:
        return {"master_ticket": ticket, "mappings": [], "found": False}

    return {
        "master_ticket": ticket,
        "mappings": [
            PositionMappingInfo(
                master_ticket=m["master_ticket"],
                slave_ticket=m["slave_ticket"],
                slave_name=m["slave_name"],
                symbol=m["symbol"],
                master_volume=m["master_volume"],
                slave_volume=m["slave_volume"],
                status=m["status"],
            )
            for m in mappings_dict[ticket]
        ],
        "found": True,
    }


@router.get("/stats")
async def get_position_stats():
    """
    Get position statistics.

    Returns summary statistics about copied positions.
    """
    engine = get_engine()
    mappings_dict = engine.get_position_mappings()

    # Calculate stats
    total_mappings = sum(len(m) for m in mappings_dict.values())
    by_slave = {}
    by_symbol = {}

    for mappings in mappings_dict.values():
        for m in mappings:
            # By slave
            slave_name = m["slave_name"]
            if slave_name not in by_slave:
                by_slave[slave_name] = 0
            by_slave[slave_name] += 1

            # By symbol
            symbol = m["symbol"]
            if symbol not in by_symbol:
                by_symbol[symbol] = 0
            by_symbol[symbol] += 1

    return {
        "total_master_positions": len(mappings_dict),
        "total_slave_positions": total_mappings,
        "positions_by_slave": by_slave,
        "positions_by_symbol": by_symbol,
    }
