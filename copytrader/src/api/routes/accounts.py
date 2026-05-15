"""Account management endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...models.account import SlaveConfig
from ...models.enums import LotMode
from ..state import get_engine

router = APIRouter()


class AccountInfo(BaseModel):
    """Account information response model."""

    name: str
    role: str
    host: str
    port: int
    connected: bool
    balance: float
    equity: float
    positions_count: int
    error_count: int
    last_error: str | None


class AccountList(BaseModel):
    """List of accounts response model."""

    master: AccountInfo
    slaves: List[AccountInfo]


class CreateSlaveRequest(BaseModel):
    """Request model for creating a new slave account."""

    name: str = Field(..., description="Unique name for the slave account")
    host: str = Field(..., description="Hostname or IP of the MT5 container")
    port: int = Field(default=8001, description="RPyC port")
    login: Optional[int] = Field(default=None, description="MT5 account login")
    password: Optional[str] = Field(default=None, description="MT5 account password")
    server: Optional[str] = Field(default=None, description="MT5 server name")
    enabled: bool = Field(default=True, description="Whether to enable immediately")
    lot_mode: str = Field(default="exact", description="Lot mode: exact, fixed, multiplier, proportional")
    lot_value: float = Field(default=1.0, description="Lot value (interpretation depends on lot_mode)")
    max_lot: float = Field(default=10.0, description="Maximum lot size")
    min_lot: float = Field(default=0.01, description="Minimum lot size")
    symbols_filter: Optional[List[str]] = Field(default=None, description="Symbols to copy (None = all)")
    magic_number: int = Field(default=123456, description="Magic number for orders")
    invert_trades: bool = Field(default=False, description="Invert trade direction")
    max_slippage: int = Field(default=20, description="Maximum slippage in points")


class UpdateSlaveRequest(BaseModel):
    """Request model for updating slave configuration."""

    lot_mode: Optional[str] = Field(default=None, description="Lot mode: exact, fixed, multiplier, proportional")
    lot_value: Optional[float] = Field(default=None, description="Lot value")
    max_lot: Optional[float] = Field(default=None, description="Maximum lot size")
    min_lot: Optional[float] = Field(default=None, description="Minimum lot size")
    symbols_filter: Optional[List[str]] = Field(default=None, description="Symbols to copy")
    magic_number: Optional[int] = Field(default=None, description="Magic number")
    invert_trades: Optional[bool] = Field(default=None, description="Invert trades")
    max_slippage: Optional[int] = Field(default=None, description="Max slippage")


class SlaveDetailInfo(BaseModel):
    """Detailed slave information."""

    name: str
    host: str
    port: int
    enabled: bool
    connected: bool
    lot_mode: str
    lot_value: float
    max_lot: float
    min_lot: float
    magic_number: int
    invert_trades: bool
    max_slippage: int
    symbols_filter: Optional[List[str]]
    state: dict


class ActionResponse(BaseModel):
    """Generic action response."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("", response_model=AccountList)
async def list_accounts():
    """
    List all connected accounts.

    Returns master and all slave account information.
    """
    engine = get_engine()
    status = engine.get_status()

    master_state = status["master"]["state"]
    master = AccountInfo(
        name=master_state["name"],
        role=master_state["role"],
        host=engine.master.config.host,
        port=engine.master.config.port,
        connected=master_state["connected"],
        balance=master_state["balance"],
        equity=master_state["equity"],
        positions_count=master_state["positions_count"],
        error_count=master_state["error_count"],
        last_error=master_state["last_error"],
    )

    slaves = []
    for name, slave_info in status["slaves"].items():
        state = slave_info["state"]
        slave = engine.slaves.get(name)
        if slave:
            slaves.append(
                AccountInfo(
                    name=state["name"],
                    role=state["role"],
                    host=slave.config.host,
                    port=slave.config.port,
                    connected=state["connected"],
                    balance=state["balance"],
                    equity=state["equity"],
                    positions_count=state["positions_count"],
                    error_count=state["error_count"],
                    last_error=state["last_error"],
                )
            )

    return AccountList(master=master, slaves=slaves)


@router.get("/slaves", response_model=List[SlaveDetailInfo])
async def list_slaves():
    """
    List all slave accounts with detailed configuration.
    """
    engine = get_engine()
    slaves = engine.list_all_slaves()
    return slaves


@router.post("/slaves", status_code=201)
async def add_slave(request: CreateSlaveRequest):
    """
    Add a new slave account dynamically.

    The slave will be connected immediately if enabled=true.
    """
    engine = get_engine()

    # Convert lot_mode string to enum
    try:
        lot_mode = LotMode(request.lot_mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lot_mode: {request.lot_mode}. Valid values: exact, fixed, multiplier, proportional"
        )

    # Create SlaveConfig
    config = SlaveConfig(
        name=request.name,
        host=request.host,
        port=request.port,
        enabled=request.enabled,
        login=request.login,
        password=request.password,
        server=request.server,
        lot_mode=lot_mode,
        lot_value=request.lot_value,
        max_lot=request.max_lot,
        min_lot=request.min_lot,
        symbols_filter=request.symbols_filter,
        magic_number=request.magic_number,
        invert_trades=request.invert_trades,
        max_slippage=request.max_slippage,
    )

    result = await engine.add_slave(config)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to add slave"))

    return result


@router.delete("/slaves/{name}")
async def remove_slave(name: str, close_positions: bool = False):
    """
    Remove a slave account.

    Args:
        name: Name of the slave to remove
        close_positions: If true, close all open positions on this slave before removing
    """
    engine = get_engine()
    result = await engine.remove_slave(name, close_positions)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Slave not found"))

    return result


@router.put("/slaves/{name}")
async def update_slave(name: str, request: UpdateSlaveRequest):
    """
    Update slave account configuration.

    Only non-null fields will be updated.
    """
    engine = get_engine()

    # Build updates dict from non-None fields
    updates = {}
    if request.lot_mode is not None:
        updates["lot_mode"] = request.lot_mode
    if request.lot_value is not None:
        updates["lot_value"] = request.lot_value
    if request.max_lot is not None:
        updates["max_lot"] = request.max_lot
    if request.min_lot is not None:
        updates["min_lot"] = request.min_lot
    if request.symbols_filter is not None:
        updates["symbols_filter"] = request.symbols_filter
    if request.magic_number is not None:
        updates["magic_number"] = request.magic_number
    if request.invert_trades is not None:
        updates["invert_trades"] = request.invert_trades
    if request.max_slippage is not None:
        updates["max_slippage"] = request.max_slippage

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await engine.update_slave(name, updates)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Slave not found"))

    return result


@router.post("/slaves/{name}/enable")
async def enable_slave(name: str):
    """
    Enable a slave account and connect it.

    The slave will start receiving copied trades.
    """
    engine = get_engine()
    result = await engine.enable_slave(name)

    if not result["success"]:
        status_code = 404 if "not found" in result.get("error", "") else 400
        raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to enable slave"))

    return result


@router.post("/slaves/{name}/disable")
async def disable_slave(name: str, close_positions: bool = False):
    """
    Disable a slave account (stop copying trades to it).

    Args:
        name: Name of the slave to disable
        close_positions: If true, close all open positions on this slave
    """
    engine = get_engine()
    result = await engine.disable_slave(name, close_positions)

    if not result["success"]:
        status_code = 404 if "not found" in result.get("error", "") else 400
        raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to disable slave"))

    return result


@router.get("/{name}")
async def get_account(name: str):
    """
    Get specific account information.

    Args:
        name: Account name (master or slave name)
    """
    engine = get_engine()

    if name == "master" or name == engine.master.config.name:
        state = engine.master.get_state()
        return AccountInfo(
            name=state.name,
            role=state.role,
            host=engine.master.config.host,
            port=engine.master.config.port,
            connected=state.connected,
            balance=state.balance,
            equity=state.equity,
            positions_count=state.positions_count,
            error_count=state.error_count,
            last_error=state.last_error,
        )

    if name in engine.slaves:
        slave = engine.slaves[name]
        state = slave.get_state()
        return AccountInfo(
            name=state.name,
            role=state.role,
            host=slave.config.host,
            port=slave.config.port,
            connected=state.connected,
            balance=state.balance,
            equity=state.equity,
            positions_count=state.positions_count,
            error_count=state.error_count,
            last_error=state.last_error,
        )

    raise HTTPException(status_code=404, detail=f"Account '{name}' not found")


@router.post("/{name}/reconnect")
async def reconnect_account(name: str):
    """
    Attempt to reconnect an account.

    Args:
        name: Account name to reconnect
    """
    engine = get_engine()

    if name == "master" or name == engine.master.config.name:
        success = engine.master.initialize()
        return {
            "account": name,
            "action": "reconnect",
            "success": success,
        }

    if name in engine.slaves:
        success = engine.slaves[name].initialize()
        return {
            "account": name,
            "action": "reconnect",
            "success": success,
        }

    raise HTTPException(status_code=404, detail=f"Account '{name}' not found")
