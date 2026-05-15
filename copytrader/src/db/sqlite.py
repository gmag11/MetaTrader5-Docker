"""SQLite database implementation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite

from ..models.enums import OperationStatus, OperationType
from ..models.position import PositionMapping, QueuedOperation
from ..utils.logging import get_logger
from .base import DatabaseInterface

logger = get_logger(__name__)

SCHEMA = """
-- Position mappings: tracks master ticket to slave tickets
CREATE TABLE IF NOT EXISTS position_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_ticket INTEGER NOT NULL,
    slave_name TEXT NOT NULL,
    slave_ticket INTEGER NOT NULL,
    master_volume REAL NOT NULL,
    slave_volume REAL NOT NULL,
    symbol TEXT NOT NULL,
    direction INTEGER NOT NULL,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    UNIQUE(master_ticket, slave_name)
);

-- Operation queue for retries
CREATE TABLE IF NOT EXISTS operation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,
    master_ticket INTEGER NOT NULL,
    slave_name TEXT NOT NULL,
    payload TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_retry_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    master_ticket INTEGER,
    slave_name TEXT,
    slave_ticket INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mappings_master ON position_mappings(master_ticket);
CREATE INDEX IF NOT EXISTS idx_mappings_status ON position_mappings(status);
CREATE INDEX IF NOT EXISTS idx_queue_status ON operation_queue(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
"""


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation of the database interface."""

    def __init__(self, db_path: str = "/app/data/copytrader.db"):
        """
        Initialize SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize database connection and schema."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        # Create schema
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

        logger.info("database_initialized", path=self.db_path)

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    # Position Mappings

    async def save_position_mappings(
        self,
        master_ticket: int,
        mappings: List[PositionMapping],
    ) -> None:
        """Save position mappings for a master ticket."""
        if not self._conn:
            return

        for mapping in mappings:
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO position_mappings
                (master_ticket, slave_name, slave_ticket, master_volume,
                 slave_volume, symbol, direction, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping.master_ticket,
                    mapping.slave_name,
                    mapping.slave_ticket,
                    mapping.master_volume,
                    mapping.slave_volume,
                    mapping.symbol,
                    mapping.direction,
                    mapping.status,
                    mapping.created_at.isoformat(),
                ),
            )

        await self._conn.commit()

        logger.debug(
            "mappings_saved",
            master_ticket=master_ticket,
            count=len(mappings),
        )

    async def load_position_mappings(self) -> Dict[int, List[PositionMapping]]:
        """Load all active position mappings."""
        if not self._conn:
            return {}

        cursor = await self._conn.execute(
            """
            SELECT * FROM position_mappings
            WHERE status = 'open'
            ORDER BY master_ticket
            """
        )
        rows = await cursor.fetchall()

        mappings: Dict[int, List[PositionMapping]] = {}
        for row in rows:
            mapping = PositionMapping(
                id=row["id"],
                master_ticket=row["master_ticket"],
                slave_name=row["slave_name"],
                slave_ticket=row["slave_ticket"],
                master_volume=row["master_volume"],
                slave_volume=row["slave_volume"],
                symbol=row["symbol"],
                direction=row["direction"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                closed_at=(
                    datetime.fromisoformat(row["closed_at"])
                    if row["closed_at"]
                    else None
                ),
            )

            if mapping.master_ticket not in mappings:
                mappings[mapping.master_ticket] = []
            mappings[mapping.master_ticket].append(mapping)

        return mappings

    async def update_mappings_status(
        self,
        master_ticket: int,
        status: str,
    ) -> None:
        """Update status for all mappings of a master ticket."""
        if not self._conn:
            return

        closed_at = datetime.now().isoformat() if status == "closed" else None

        await self._conn.execute(
            """
            UPDATE position_mappings
            SET status = ?, closed_at = ?
            WHERE master_ticket = ?
            """,
            (status, closed_at, master_ticket),
        )
        await self._conn.commit()

    async def update_mapping_volume(
        self,
        master_ticket: int,
        slave_name: str,
        new_volume: float,
    ) -> None:
        """Update volume for a specific mapping."""
        if not self._conn:
            return

        await self._conn.execute(
            """
            UPDATE position_mappings
            SET slave_volume = ?
            WHERE master_ticket = ? AND slave_name = ?
            """,
            (new_volume, master_ticket, slave_name),
        )
        await self._conn.commit()

    async def get_mapping(
        self,
        master_ticket: int,
        slave_name: str,
    ) -> Optional[PositionMapping]:
        """Get a specific mapping."""
        if not self._conn:
            return None

        cursor = await self._conn.execute(
            """
            SELECT * FROM position_mappings
            WHERE master_ticket = ? AND slave_name = ?
            """,
            (master_ticket, slave_name),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return PositionMapping(
            id=row["id"],
            master_ticket=row["master_ticket"],
            slave_name=row["slave_name"],
            slave_ticket=row["slave_ticket"],
            master_volume=row["master_volume"],
            slave_volume=row["slave_volume"],
            symbol=row["symbol"],
            direction=row["direction"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            closed_at=(
                datetime.fromisoformat(row["closed_at"])
                if row["closed_at"]
                else None
            ),
        )

    # Operation Queue

    async def queue_operation(self, operation: QueuedOperation) -> int:
        """Add operation to queue, return operation ID."""
        if not self._conn:
            return -1

        cursor = await self._conn.execute(
            """
            INSERT INTO operation_queue
            (operation_type, master_ticket, slave_name, payload,
             attempts, max_attempts, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                operation.operation_type.value,
                operation.master_ticket,
                operation.slave_name,
                json.dumps(operation.payload),
                operation.attempts,
                operation.max_attempts,
                operation.status.value,
                operation.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

        return cursor.lastrowid or -1

    async def get_pending_operations(self) -> List[QueuedOperation]:
        """Get all pending operations."""
        if not self._conn:
            return []

        cursor = await self._conn.execute(
            """
            SELECT * FROM operation_queue
            WHERE status = 'pending'
            AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY created_at
            """,
            (datetime.now().isoformat(),),
        )
        rows = await cursor.fetchall()

        operations = []
        for row in rows:
            op = QueuedOperation(
                id=row["id"],
                operation_type=OperationType(row["operation_type"]),
                master_ticket=row["master_ticket"],
                slave_name=row["slave_name"],
                payload=json.loads(row["payload"]),
                attempts=row["attempts"],
                max_attempts=row["max_attempts"],
                status=OperationStatus(row["status"]),
                error_message=row["error_message"],
                created_at=datetime.fromisoformat(row["created_at"]),
                next_retry_at=(
                    datetime.fromisoformat(row["next_retry_at"])
                    if row["next_retry_at"]
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"]
                    else None
                ),
            )
            operations.append(op)

        return operations

    async def update_operation(self, operation: QueuedOperation) -> None:
        """Update operation status."""
        if not self._conn or not operation.id:
            return

        await self._conn.execute(
            """
            UPDATE operation_queue
            SET status = ?, attempts = ?, error_message = ?,
                next_retry_at = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                operation.status.value,
                operation.attempts,
                operation.error_message,
                (
                    operation.next_retry_at.isoformat()
                    if operation.next_retry_at
                    else None
                ),
                (
                    operation.completed_at.isoformat()
                    if operation.completed_at
                    else None
                ),
                operation.id,
            ),
        )
        await self._conn.commit()

    # Audit Log

    async def log_event(
        self,
        event_type: str,
        master_ticket: Optional[int] = None,
        slave_name: Optional[str] = None,
        slave_ticket: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Log an audit event."""
        if not self._conn:
            return

        await self._conn.execute(
            """
            INSERT INTO audit_log
            (event_type, master_ticket, slave_name, slave_ticket, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_type,
                master_ticket,
                slave_name,
                slave_ticket,
                json.dumps(details) if details else None,
            ),
        )
        await self._conn.commit()
