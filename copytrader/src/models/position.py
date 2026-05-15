"""Position-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import OperationStatus, OperationType


@dataclass
class PositionSnapshot:
    """Snapshot of a position at a point in time."""

    ticket: int
    symbol: str
    type: int  # 0=BUY, 1=SELL
    volume: float
    price_open: float
    sl: float
    tp: float
    magic: int
    comment: str
    time: int
    profit: float

    @classmethod
    def from_mt5_position(cls, pos) -> "PositionSnapshot":
        """Create from MT5 position object."""
        return cls(
            ticket=pos.ticket,
            symbol=pos.symbol,
            type=pos.type,
            volume=pos.volume,
            price_open=pos.price_open,
            sl=pos.sl,
            tp=pos.tp,
            magic=pos.magic,
            comment=pos.comment,
            time=pos.time,
            profit=pos.profit,
        )


@dataclass
class PositionMapping:
    """Maps a master position to a slave position."""

    master_ticket: int
    slave_ticket: int
    slave_name: str
    master_volume: float
    slave_volume: float
    symbol: str
    direction: int  # 0=BUY, 1=SELL
    status: str = "open"  # open, closed, error
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    id: Optional[int] = None


@dataclass
class PartialClose:
    """Represents a partial close event."""

    ticket: int
    closed_volume: float
    remaining_volume: float
    original_volume: float


@dataclass
class Modification:
    """Represents a SL/TP modification event."""

    ticket: int
    old_sl: float
    new_sl: float
    old_tp: float
    new_tp: float


@dataclass
class ChangeSet:
    """Set of detected changes between position snapshots."""

    new_positions: list[PositionSnapshot] = field(default_factory=list)
    closed_positions: list[PositionSnapshot] = field(default_factory=list)
    partial_closes: list[PartialClose] = field(default_factory=list)
    modifications: list[Modification] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if there are no changes."""
        return not any(
            [
                self.new_positions,
                self.closed_positions,
                self.partial_closes,
                self.modifications,
            ]
        )

    def __len__(self) -> int:
        """Total number of changes."""
        return (
            len(self.new_positions)
            + len(self.closed_positions)
            + len(self.partial_closes)
            + len(self.modifications)
        )


@dataclass
class QueuedOperation:
    """Operation queued for execution/retry."""

    operation_type: OperationType
    master_ticket: int
    slave_name: str
    payload: dict
    id: Optional[int] = None
    attempts: int = 0
    max_attempts: int = 3
    status: OperationStatus = OperationStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    next_retry_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
