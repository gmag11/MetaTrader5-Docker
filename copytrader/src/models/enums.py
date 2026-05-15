"""Enumerations for copytrader."""

from enum import Enum


class LotMode(str, Enum):
    """Lot sizing modes for slave accounts."""

    EXACT = "exact"  # Same lot size as master
    FIXED = "fixed"  # Fixed lot size for all trades
    MULTIPLIER = "multiplier"  # Master lot * multiplier
    PROPORTIONAL = "proportional"  # Based on balance ratio


class OperationType(str, Enum):
    """Types of trading operations."""

    OPEN = "open"
    CLOSE = "close"
    MODIFY = "modify"
    PARTIAL_CLOSE = "partial_close"


class OperationStatus(str, Enum):
    """Status of queued operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PositionType(int, Enum):
    """MT5 position types."""

    BUY = 0
    SELL = 1


class OrderType(int, Enum):
    """MT5 order types."""

    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5
    BUY_STOP_LIMIT = 6
    SELL_STOP_LIMIT = 7
    CLOSE_BY = 8


class TradeAction(int, Enum):
    """MT5 trade actions."""

    DEAL = 1  # Market order
    PENDING = 5  # Pending order
    SLTP = 6  # Modify SL/TP
    MODIFY = 7  # Modify pending order
    REMOVE = 8  # Remove pending order
    CLOSE_BY = 10  # Close by opposite position


class TradeRetcode(int, Enum):
    """Common MT5 trade return codes."""

    DONE = 10009  # Request completed
    PLACED = 10008  # Order placed
    REJECT = 10006  # Request rejected
    CANCEL = 10007  # Request canceled
    INVALID_VOLUME = 10014  # Invalid volume
    INVALID_PRICE = 10015  # Invalid price
    INVALID_STOPS = 10016  # Invalid stops
    NO_MONEY = 10019  # Not enough money
    MARKET_CLOSED = 10018  # Market is closed
    CONNECTION = 10031  # No connection
