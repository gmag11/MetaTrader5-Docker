"""Database interface definition."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..models.position import PositionMapping, QueuedOperation


class DatabaseInterface(ABC):
    """Abstract database interface for copytrader persistence."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database connection and schema."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""
        pass

    # Position Mappings

    @abstractmethod
    async def save_position_mappings(
        self,
        master_ticket: int,
        mappings: List[PositionMapping],
    ) -> None:
        """Save position mappings for a master ticket."""
        pass

    @abstractmethod
    async def load_position_mappings(self) -> Dict[int, List[PositionMapping]]:
        """Load all active position mappings."""
        pass

    @abstractmethod
    async def update_mappings_status(
        self,
        master_ticket: int,
        status: str,
    ) -> None:
        """Update status for all mappings of a master ticket."""
        pass

    @abstractmethod
    async def update_mapping_volume(
        self,
        master_ticket: int,
        slave_name: str,
        new_volume: float,
    ) -> None:
        """Update volume for a specific mapping."""
        pass

    @abstractmethod
    async def get_mapping(
        self,
        master_ticket: int,
        slave_name: str,
    ) -> Optional[PositionMapping]:
        """Get a specific mapping."""
        pass

    # Operation Queue

    @abstractmethod
    async def queue_operation(self, operation: QueuedOperation) -> int:
        """Add operation to queue, return operation ID."""
        pass

    @abstractmethod
    async def get_pending_operations(self) -> List[QueuedOperation]:
        """Get all pending operations."""
        pass

    @abstractmethod
    async def update_operation(self, operation: QueuedOperation) -> None:
        """Update operation status."""
        pass

    # Audit Log

    @abstractmethod
    async def log_event(
        self,
        event_type: str,
        master_ticket: Optional[int] = None,
        slave_name: Optional[str] = None,
        slave_ticket: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Log an audit event."""
        pass
