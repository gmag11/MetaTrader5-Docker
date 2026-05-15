"""Master account position monitoring."""

from typing import Dict, Optional

from mt5linux import MetaTrader5

from ..models.account import AccountState, MasterConfig
from ..models.position import ChangeSet, PositionSnapshot
from ..utils.logging import get_logger
from .detector import ChangeDetector

logger = get_logger(__name__)


class MasterMonitor:
    """
    Monitors the master account for position changes.

    Polls positions at configurable intervals and detects:
    - New positions (opens)
    - Closed positions
    - Modified positions (SL/TP changes)
    - Partial closes (volume decreases)
    """

    def __init__(
        self,
        config: MasterConfig,
        poll_interval_ms: int = 500,
    ):
        """
        Initialize master monitor.

        Args:
            config: Master account configuration
            poll_interval_ms: Polling interval in milliseconds
        """
        self.config = config
        self.poll_interval = poll_interval_ms / 1000.0
        self.mt5: Optional[MetaTrader5] = None
        self.detector = ChangeDetector()
        self.state = AccountState(
            name=config.name,
            role="master",
            host=config.host,
            port=config.port,
        )
        self._initialized = False

    def initialize(self, max_retries: int = 10, retry_delay: float = 15.0) -> bool:
        """
        Initialize connection to master MT5 and login to trading account.

        Args:
            max_retries: Maximum connection attempts
            retry_delay: Delay between retries in seconds

        Returns:
            True if connection successful, False otherwise
        """
        import time
        import rpyc.core.protocol

        # Increase RPyC timeout for Wine IPC (default 30s is too short)
        rpyc.core.protocol.DEFAULT_CONFIG['sync_request_timeout'] = 120

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "master_connecting",
                    attempt=attempt,
                    max_retries=max_retries,
                    host=self.config.host,
                )

                self.mt5 = MetaTrader5(host=self.config.host, port=self.config.port)

                if not self.mt5.initialize():
                    error = self.mt5.last_error() if self.mt5 else None
                    logger.warning(
                        "master_init_attempt_failed",
                        attempt=attempt,
                        error=error,
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            "master_init_failed",
                            host=self.config.host,
                            port=self.config.port,
                        )
                        return False

                # Login to trading account if credentials provided
                if self.config.login:
                    logger.info(
                        "master_logging_in",
                        login=self.config.login,
                        server=self.config.server,
                    )
                    authorized = self.mt5.login(
                        login=self.config.login,
                        password=self.config.password,
                        server=self.config.server,
                        timeout=60000,
                    )
                    if not authorized:
                        error = self.mt5.last_error()
                        logger.warning(
                            "master_login_attempt_failed",
                            attempt=attempt,
                            login=self.config.login,
                            error=error,
                        )
                        if attempt < max_retries:
                            time.sleep(retry_delay)
                            continue
                        else:
                            logger.error(
                                "master_login_failed",
                                login=self.config.login,
                                error=error,
                            )
                            return False
                    logger.info(
                        "master_login_success",
                        login=self.config.login,
                    )

                # Get initial account info
                account_info = self.mt5.account_info()
                if account_info:
                    self.state.update_from_account_info(account_info)
                    logger.info(
                        "master_connected",
                        host=self.config.host,
                        port=self.config.port,
                        login=account_info.login,
                        balance=self.state.balance,
                    )

                # Set initial snapshot to avoid copying existing positions
                current_positions = self.get_current_positions()
                self.detector.set_initial_snapshot(current_positions)
                self.state.positions_count = len(current_positions)
                self._initialized = True
                return True

            except Exception as e:
                logger.warning(
                    "master_connection_attempt_error",
                    attempt=attempt,
                    host=self.config.host,
                    port=self.config.port,
                    error=str(e),
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(
                        "master_connection_error",
                        host=self.config.host,
                        port=self.config.port,
                        error=str(e),
                    )
                    self.state.record_error(str(e))
                    return False

        return False

    def shutdown(self) -> None:
        """Shutdown the monitor."""
        if self.mt5:
            try:
                self.mt5.shutdown()
            except Exception:
                pass
        self._initialized = False
        self.state.connected = False

    def is_connected(self) -> bool:
        """Check if connected to master."""
        return self._initialized and self.state.connected

    def get_current_positions(self) -> Dict[int, PositionSnapshot]:
        """
        Fetch all current positions from master.

        Returns:
            Dictionary of positions keyed by ticket
        """
        if not self.mt5:
            return {}

        try:
            positions = self.mt5.positions_get()
            if positions is None:
                return {}

            return {
                pos.ticket: PositionSnapshot.from_mt5_position(pos)
                for pos in positions
            }

        except Exception as e:
            logger.error("get_positions_error", error=str(e))
            self.state.record_error(str(e))
            return {}

    def detect_changes(self) -> ChangeSet:
        """
        Detect position changes since last check.

        Returns:
            ChangeSet containing all detected changes
        """
        current = self.get_current_positions()
        self.state.positions_count = len(current)

        changes = self.detector.compute_diff(current)

        if not changes.is_empty():
            logger.debug(
                "changes_detected",
                new=len(changes.new_positions),
                closed=len(changes.closed_positions),
                modified=len(changes.modifications),
                partial=len(changes.partial_closes),
            )

        return changes

    def update_account_info(self) -> None:
        """Update account state with latest info."""
        if not self.mt5:
            return

        try:
            account_info = self.mt5.account_info()
            if account_info:
                self.state.update_from_account_info(account_info)

        except Exception as e:
            logger.error("account_info_error", error=str(e))
            self.state.record_error(str(e))

    def get_state(self) -> AccountState:
        """Get current account state."""
        return self.state

    def get_balance(self) -> float:
        """Get master account balance."""
        return self.state.balance
