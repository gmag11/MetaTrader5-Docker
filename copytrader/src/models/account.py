"""Account configuration models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import LotMode


@dataclass
class MasterConfig:
    """Configuration for the master account."""

    name: str
    host: str
    port: int = 8001
    # MT5 login credentials
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None


@dataclass
class SlaveConfig:
    """Configuration for a slave account."""

    name: str
    host: str
    port: int = 8001
    enabled: bool = True
    # MT5 login credentials
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    # Lot configuration
    lot_mode: LotMode = LotMode.EXACT
    lot_value: float = 1.0  # Meaning depends on lot_mode
    max_lot: float = 10.0
    min_lot: float = 0.01
    symbols_filter: Optional[list[str]] = None  # None = all symbols
    magic_number: int = 123456
    invert_trades: bool = False  # For hedge accounts
    max_slippage: int = 20

    def should_copy_symbol(self, symbol: str) -> bool:
        """Check if this slave should copy trades for given symbol."""
        if self.symbols_filter is None:
            return True
        return symbol in self.symbols_filter


@dataclass
class AccountState:
    """Runtime state for an account connection."""

    name: str
    role: str  # 'master' or 'slave'
    host: str
    port: int
    connected: bool = False
    last_heartbeat: Optional[datetime] = None
    positions_count: int = 0
    balance: float = 0.0
    equity: float = 0.0
    margin_level: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None

    def update_from_account_info(self, info) -> None:
        """Update state from MT5 account info."""
        if info:
            self.balance = info.balance
            self.equity = info.equity
            self.margin_level = info.margin_level if hasattr(info, "margin_level") else 0.0
            self.last_heartbeat = datetime.now()
            self.connected = True
            self.error_count = 0
            self.last_error = None

    def record_error(self, error: str) -> None:
        """Record an error."""
        self.error_count += 1
        self.last_error = error
        self.connected = False


@dataclass
class Settings:
    """Global copytrader settings."""

    polling_interval_ms: int = 500
    retry_attempts: int = 3
    retry_delay_ms: int = 1000
    connection_timeout_ms: int = 5000
    heartbeat_interval_ms: int = 10000
