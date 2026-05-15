"""Main synchronization engine."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from ..db.base import DatabaseInterface
from ..models.account import AccountState, MasterConfig, SlaveConfig
from ..models.enums import OperationType, TradeRetcode
from ..models.position import (
    ChangeSet,
    Modification,
    PartialClose,
    PositionMapping,
    PositionSnapshot,
)
from ..services.lot_calculator import LotCalculator
from ..services.retry_manager import RetryManager
from ..utils.logging import get_logger
from .executor import SlaveExecutor
from .monitor import MasterMonitor

logger = get_logger(__name__)


class SyncEngine:
    """
    Main copytrader synchronization engine.

    Orchestrates:
    - Master account monitoring
    - Slave account execution
    - Position mapping persistence
    - Error handling and retries
    """

    def __init__(
        self,
        master_config: MasterConfig,
        slaves_config: List[SlaveConfig],
        db: DatabaseInterface,
        polling_interval_ms: int = 500,
        retry_attempts: int = 3,
    ):
        """
        Initialize sync engine.

        Args:
            master_config: Master account configuration
            slaves_config: List of slave account configurations
            db: Database interface for persistence
            polling_interval_ms: Polling interval in milliseconds
            retry_attempts: Number of retry attempts for failed operations
        """
        self.master = MasterMonitor(master_config, polling_interval_ms)
        self.slaves: Dict[str, SlaveExecutor] = {}
        self.db = db
        self.polling_interval = polling_interval_ms / 1000.0
        self.retry_manager = RetryManager(max_attempts=retry_attempts)

        # Position mapping: master_ticket -> list of slave mappings
        self.position_map: Dict[int, List[PositionMapping]] = {}

        # Initialize slaves
        for config in slaves_config:
            if config.enabled:
                self.slaves[config.name] = SlaveExecutor(config)

        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self, initial_delay: float = 60.0) -> bool:
        """
        Start the sync engine.

        Args:
            initial_delay: Initial delay in seconds to wait for MT5 to start

        Returns:
            True if started successfully
        """
        import time

        logger.info("sync_engine_starting")

        # Wait for MT5 containers to fully initialize
        logger.info(
            "waiting_for_mt5_startup",
            delay_seconds=initial_delay,
        )
        time.sleep(initial_delay)

        # Initialize master connection with more retries for startup
        if not self.master.initialize(max_retries=10, retry_delay=15.0):
            logger.error("master_initialization_failed")
            return False

        # Initialize slave connections
        failed_slaves = []
        for name, slave in self.slaves.items():
            if not slave.initialize(max_retries=10, retry_delay=15.0):
                logger.error("slave_initialization_failed", slave=name)
                failed_slaves.append(name)

        # Remove failed slaves
        for name in failed_slaves:
            del self.slaves[name]

        if not self.slaves:
            logger.error("no_slaves_connected")
            return False

        # Update master balance for all slaves (for proportional mode)
        master_balance = self.master.get_balance()
        for slave in self.slaves.values():
            slave.update_master_balance(master_balance)

        # Load existing position mappings from database
        self.position_map = await self.db.load_position_mappings()
        logger.info(
            "position_mappings_loaded",
            count=sum(len(v) for v in self.position_map.values()),
        )

        self._running = True

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info(
            "sync_engine_started",
            master=self.master.config.name,
            slaves=list(self.slaves.keys()),
        )

        return True

    async def stop(self) -> None:
        """Stop the sync engine."""
        logger.info("sync_engine_stopping")

        self._running = False

        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Shutdown connections
        self.master.shutdown()
        for slave in self.slaves.values():
            slave.shutdown()

        logger.info("sync_engine_stopped")

    async def run(self) -> None:
        """
        Main loop: monitor master and propagate changes.

        This runs indefinitely until stop() is called.
        """
        if not self._running:
            if not await self.start():
                return

        logger.info("sync_engine_running")

        while self._running:
            try:
                # Detect changes on master
                changes = self.master.detect_changes()

                if not changes.is_empty():
                    await self._process_changes(changes)

                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("sync_engine_error", error=str(e))
                await asyncio.sleep(1)

    async def _process_changes(self, changes: ChangeSet) -> None:
        """Process detected position changes."""
        tasks = []

        # Handle new positions
        for pos in changes.new_positions:
            tasks.append(self._handle_new_position(pos))

        # Handle closed positions
        for pos in changes.closed_positions:
            tasks.append(self._handle_close_position(pos.ticket))

        # Handle modifications
        for mod in changes.modifications:
            tasks.append(self._handle_modify_position(mod))

        # Handle partial closes
        for partial in changes.partial_closes:
            tasks.append(self._handle_partial_close(partial))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_new_position(self, master_pos: PositionSnapshot) -> None:
        """Open position on all slave accounts."""
        logger.info(
            "handling_new_position",
            master_ticket=master_pos.ticket,
            symbol=master_pos.symbol,
            volume=master_pos.volume,
        )

        tasks = []
        for slave_name, slave in self.slaves.items():
            if slave.should_copy_symbol(master_pos.symbol):
                tasks.append(self._copy_to_slave(slave_name, slave, master_pos))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful mappings
        mappings = []
        for result in results:
            if isinstance(result, PositionMapping):
                mappings.append(result)

        if mappings:
            self.position_map[master_pos.ticket] = mappings
            await self.db.save_position_mappings(master_pos.ticket, mappings)

    async def _copy_to_slave(
        self,
        slave_name: str,
        slave: SlaveExecutor,
        master_pos: PositionSnapshot,
    ) -> Optional[PositionMapping]:
        """Copy a single position to a slave account."""
        try:
            result = await slave.open_position(master_pos)

            if result and result.retcode == TradeRetcode.DONE.value:
                mapping = PositionMapping(
                    master_ticket=master_pos.ticket,
                    slave_ticket=result.order,
                    slave_name=slave_name,
                    master_volume=master_pos.volume,
                    slave_volume=slave.lot_calculator.calculate(master_pos.volume),
                    symbol=master_pos.symbol,
                    direction=master_pos.type,
                )
                return mapping

        except Exception as e:
            logger.error(
                "copy_to_slave_failed",
                slave=slave_name,
                master_ticket=master_pos.ticket,
                error=str(e),
            )

        return None

    async def _handle_close_position(self, master_ticket: int) -> None:
        """Close position on all slaves."""
        if master_ticket not in self.position_map:
            logger.warning(
                "no_slave_mappings",
                master_ticket=master_ticket,
            )
            return

        logger.info("handling_close_position", master_ticket=master_ticket)

        tasks = []
        for mapping in self.position_map[master_ticket]:
            slave = self.slaves.get(mapping.slave_name)
            if slave:
                tasks.append(slave.close_position(mapping.slave_ticket))

        await asyncio.gather(*tasks, return_exceptions=True)

        # Update mappings status
        for mapping in self.position_map[master_ticket]:
            mapping.status = "closed"
            mapping.closed_at = datetime.now()

        await self.db.update_mappings_status(master_ticket, "closed")

        # Remove from active map
        del self.position_map[master_ticket]

    async def _handle_modify_position(self, mod: Modification) -> None:
        """Modify SL/TP on all slaves."""
        if mod.ticket not in self.position_map:
            return

        logger.info(
            "handling_modify_position",
            master_ticket=mod.ticket,
            new_sl=mod.new_sl,
            new_tp=mod.new_tp,
        )

        tasks = []
        for mapping in self.position_map[mod.ticket]:
            slave = self.slaves.get(mapping.slave_name)
            if slave:
                # Get slave position to calculate relative SL/TP
                slave_pos = slave.get_position_by_ticket(mapping.slave_ticket)
                if slave_pos:
                    sl, tp = self._calculate_slave_sltp(
                        mod, slave_pos.price_open, mapping.direction
                    )
                    tasks.append(
                        slave.modify_position(mapping.slave_ticket, sl, tp)
                    )

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_partial_close(self, partial: PartialClose) -> None:
        """Handle partial close on all slaves."""
        if partial.ticket not in self.position_map:
            return

        logger.info(
            "handling_partial_close",
            master_ticket=partial.ticket,
            closed_volume=partial.closed_volume,
            remaining_volume=partial.remaining_volume,
        )

        # Calculate close ratio
        close_ratio = partial.closed_volume / partial.original_volume

        tasks = []
        for mapping in self.position_map[partial.ticket]:
            slave = self.slaves.get(mapping.slave_name)
            if slave:
                # Calculate proportional close volume
                slave_close_volume = round(mapping.slave_volume * close_ratio, 2)

                # Get symbol info for minimum volume
                slave_pos = slave.get_position_by_ticket(mapping.slave_ticket)
                if slave_pos:
                    symbol_info = slave.mt5.symbol_info(mapping.symbol)
                    if symbol_info:
                        volume_min = getattr(symbol_info, "volume_min", 0.01)
                        if slave_close_volume < volume_min:
                            slave_close_volume = volume_min

                tasks.append(
                    slave.close_position(mapping.slave_ticket, slave_close_volume)
                )

                # Update mapping volume
                mapping.slave_volume -= slave_close_volume

        await asyncio.gather(*tasks, return_exceptions=True)

        # Update in database
        for mapping in self.position_map[partial.ticket]:
            await self.db.update_mapping_volume(
                mapping.master_ticket,
                mapping.slave_name,
                mapping.slave_volume,
            )

    def _calculate_slave_sltp(
        self,
        mod: Modification,
        slave_entry_price: float,
        direction: int,
    ) -> tuple[float, float]:
        """Calculate SL/TP for slave based on master modification."""
        sl = 0.0
        tp = 0.0

        # We need to preserve the distance, not the absolute value
        # This is complex because we don't have the master entry price
        # For now, just pass through the values
        # TODO: Improve by storing master entry price in mapping

        return mod.new_sl, mod.new_tp

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to update account info."""
        while self._running:
            try:
                # Update master account info
                self.master.update_account_info()

                # Update master balance for slaves
                master_balance = self.master.get_balance()
                for slave in self.slaves.values():
                    slave.update_master_balance(master_balance)
                    slave.update_account_info()

                await asyncio.sleep(10)  # Heartbeat every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("heartbeat_error", error=str(e))
                await asyncio.sleep(5)

    def get_status(self) -> Dict:
        """Get current engine status."""
        return {
            "running": self._running,
            "master": {
                "name": self.master.config.name,
                "connected": self.master.is_connected(),
                "state": self._account_state_to_dict(self.master.get_state()),
            },
            "slaves": {
                name: {
                    "connected": slave.is_connected(),
                    "state": self._account_state_to_dict(slave.get_state()),
                }
                for name, slave in self.slaves.items()
            },
            "active_mappings": sum(len(v) for v in self.position_map.values()),
        }

    def _account_state_to_dict(self, state: AccountState) -> Dict:
        """Convert account state to dictionary."""
        return {
            "name": state.name,
            "role": state.role,
            "connected": state.connected,
            "balance": state.balance,
            "equity": state.equity,
            "positions_count": state.positions_count,
            "error_count": state.error_count,
            "last_error": state.last_error,
        }

    def get_position_mappings(self) -> Dict[int, List[Dict]]:
        """Get all active position mappings."""
        return {
            ticket: [
                {
                    "master_ticket": m.master_ticket,
                    "slave_ticket": m.slave_ticket,
                    "slave_name": m.slave_name,
                    "symbol": m.symbol,
                    "master_volume": m.master_volume,
                    "slave_volume": m.slave_volume,
                    "status": m.status,
                }
                for m in mappings
            ]
            for ticket, mappings in self.position_map.items()
        }

    # Dynamic account management methods

    async def add_slave(self, config: SlaveConfig) -> Dict:
        """
        Add a new slave account dynamically.

        Args:
            config: Slave account configuration

        Returns:
            Result dictionary with success status and details
        """
        if config.name in self.slaves:
            return {
                "success": False,
                "error": f"Slave '{config.name}' already exists",
            }

        logger.info(
            "adding_slave",
            name=config.name,
            host=config.host,
            port=config.port,
        )

        # Create executor
        master_balance = self.master.get_balance() if self.master.is_connected() else 0.0
        executor = SlaveExecutor(config, master_balance)

        # Try to initialize connection
        if config.enabled:
            if not executor.initialize(max_retries=3, retry_delay=5.0):
                return {
                    "success": False,
                    "error": f"Failed to connect to slave '{config.name}'",
                    "state": self._account_state_to_dict(executor.get_state()),
                }

        # Add to slaves dict
        self.slaves[config.name] = executor

        logger.info(
            "slave_added",
            name=config.name,
            connected=executor.is_connected(),
        )

        return {
            "success": True,
            "name": config.name,
            "connected": executor.is_connected(),
            "state": self._account_state_to_dict(executor.get_state()),
        }

    async def remove_slave(self, name: str, close_positions: bool = False) -> Dict:
        """
        Remove a slave account.

        Args:
            name: Name of the slave to remove
            close_positions: If True, close all positions on this slave before removing

        Returns:
            Result dictionary with success status
        """
        if name not in self.slaves:
            return {
                "success": False,
                "error": f"Slave '{name}' not found",
            }

        logger.info("removing_slave", name=name, close_positions=close_positions)

        slave = self.slaves[name]

        # Optionally close all positions on this slave
        if close_positions and slave.is_connected():
            for master_ticket, mappings in list(self.position_map.items()):
                for mapping in mappings:
                    if mapping.slave_name == name and mapping.status == "open":
                        try:
                            await slave.close_position(mapping.slave_ticket)
                            mapping.status = "closed"
                        except Exception as e:
                            logger.error(
                                "close_position_on_remove_failed",
                                slave=name,
                                ticket=mapping.slave_ticket,
                                error=str(e),
                            )

        # Shutdown connection
        slave.shutdown()

        # Remove from slaves dict
        del self.slaves[name]

        # Clean up mappings for this slave
        for master_ticket in list(self.position_map.keys()):
            self.position_map[master_ticket] = [
                m for m in self.position_map[master_ticket]
                if m.slave_name != name
            ]
            # Remove empty entries
            if not self.position_map[master_ticket]:
                del self.position_map[master_ticket]

        logger.info("slave_removed", name=name)

        return {
            "success": True,
            "name": name,
            "message": f"Slave '{name}' removed successfully",
        }

    async def enable_slave(self, name: str) -> Dict:
        """
        Enable a slave account and connect it.

        Args:
            name: Name of the slave to enable

        Returns:
            Result dictionary with success status
        """
        if name not in self.slaves:
            return {
                "success": False,
                "error": f"Slave '{name}' not found",
            }

        slave = self.slaves[name]

        if slave.config.enabled and slave.is_connected():
            return {
                "success": True,
                "message": f"Slave '{name}' is already enabled and connected",
            }

        logger.info("enabling_slave", name=name)

        slave.config.enabled = True

        # Try to connect if not already connected
        if not slave.is_connected():
            master_balance = self.master.get_balance() if self.master.is_connected() else 0.0
            slave.update_master_balance(master_balance)

            if not slave.initialize(max_retries=3, retry_delay=5.0):
                return {
                    "success": False,
                    "error": f"Failed to connect slave '{name}'",
                    "state": self._account_state_to_dict(slave.get_state()),
                }

        logger.info("slave_enabled", name=name)

        return {
            "success": True,
            "name": name,
            "connected": slave.is_connected(),
            "state": self._account_state_to_dict(slave.get_state()),
        }

    async def disable_slave(self, name: str, close_positions: bool = False) -> Dict:
        """
        Disable a slave account (stop copying to it).

        Args:
            name: Name of the slave to disable
            close_positions: If True, close all positions on this slave

        Returns:
            Result dictionary with success status
        """
        if name not in self.slaves:
            return {
                "success": False,
                "error": f"Slave '{name}' not found",
            }

        logger.info("disabling_slave", name=name, close_positions=close_positions)

        slave = self.slaves[name]

        # Optionally close all positions
        if close_positions and slave.is_connected():
            closed_count = 0
            for master_ticket, mappings in list(self.position_map.items()):
                for mapping in mappings:
                    if mapping.slave_name == name and mapping.status == "open":
                        try:
                            result = await slave.close_position(mapping.slave_ticket)
                            if result:
                                mapping.status = "closed"
                                closed_count += 1
                        except Exception as e:
                            logger.error(
                                "close_position_on_disable_failed",
                                slave=name,
                                ticket=mapping.slave_ticket,
                                error=str(e),
                            )
            logger.info("positions_closed_on_disable", name=name, count=closed_count)

        # Mark as disabled (won't receive new trades)
        slave.config.enabled = False

        # Optionally disconnect
        slave.shutdown()

        logger.info("slave_disabled", name=name)

        return {
            "success": True,
            "name": name,
            "message": f"Slave '{name}' disabled",
            "positions_closed": close_positions,
        }

    async def update_slave(self, name: str, updates: Dict) -> Dict:
        """
        Update slave configuration.

        Args:
            name: Name of the slave to update
            updates: Dictionary of fields to update

        Returns:
            Result dictionary with success status
        """
        if name not in self.slaves:
            return {
                "success": False,
                "error": f"Slave '{name}' not found",
            }

        slave = self.slaves[name]
        config = slave.config

        logger.info("updating_slave", name=name, updates=updates)

        # Update allowed fields
        allowed_fields = [
            "lot_mode", "lot_value", "max_lot", "min_lot",
            "symbols_filter", "magic_number", "invert_trades", "max_slippage"
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                if field == "lot_mode":
                    from ..models.enums import LotMode
                    value = LotMode(value)
                setattr(config, field, value)

        # Update lot calculator with new config
        slave.lot_calculator = LotCalculator(config, slave.lot_calculator.master_balance)

        logger.info("slave_updated", name=name)

        return {
            "success": True,
            "name": name,
            "message": f"Slave '{name}' configuration updated",
        }

    def get_slave_config(self, name: str) -> Optional[SlaveConfig]:
        """Get slave configuration by name."""
        if name in self.slaves:
            return self.slaves[name].config
        return None

    def list_all_slaves(self) -> List[Dict]:
        """List all slaves with their configuration and state."""
        result = []
        for name, slave in self.slaves.items():
            result.append({
                "name": name,
                "host": slave.config.host,
                "port": slave.config.port,
                "enabled": slave.config.enabled,
                "connected": slave.is_connected(),
                "lot_mode": slave.config.lot_mode.value,
                "lot_value": slave.config.lot_value,
                "max_lot": slave.config.max_lot,
                "min_lot": slave.config.min_lot,
                "magic_number": slave.config.magic_number,
                "invert_trades": slave.config.invert_trades,
                "max_slippage": slave.config.max_slippage,
                "symbols_filter": slave.config.symbols_filter,
                "state": self._account_state_to_dict(slave.get_state()),
            })
        return result
