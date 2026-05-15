"""Slave account trade executor."""

from typing import Any, Dict, Optional

from mt5linux import MetaTrader5

from ..models.account import AccountState, SlaveConfig
from ..models.enums import OrderType, PositionType, TradeAction, TradeRetcode
from ..models.position import PositionSnapshot
from ..services.lot_calculator import LotCalculator
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SlaveExecutor:
    """
    Executes trades on a slave account.

    Handles:
    - Opening positions (mirroring master)
    - Closing positions (full or partial)
    - Modifying SL/TP
    """

    def __init__(self, config: SlaveConfig, master_balance: float = 0.0):
        """
        Initialize slave executor.

        Args:
            config: Slave account configuration
            master_balance: Master account balance (for proportional lot mode)
        """
        self.config = config
        self.mt5: Optional[MetaTrader5] = None
        self.lot_calculator = LotCalculator(config, master_balance)
        self.state = AccountState(
            name=config.name,
            role="slave",
            host=config.host,
            port=config.port,
        )
        self._initialized = False

    def initialize(self, max_retries: int = 10, retry_delay: float = 15.0) -> bool:
        """
        Initialize connection to slave MT5 and login to trading account.

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
                    "slave_connecting",
                    name=self.config.name,
                    attempt=attempt,
                    max_retries=max_retries,
                    host=self.config.host,
                )

                self.mt5 = MetaTrader5(host=self.config.host, port=self.config.port)

                if not self.mt5.initialize():
                    error = self.mt5.last_error() if self.mt5 else None
                    logger.warning(
                        "slave_init_attempt_failed",
                        name=self.config.name,
                        attempt=attempt,
                        error=error,
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            "slave_init_failed",
                            name=self.config.name,
                            host=self.config.host,
                            port=self.config.port,
                        )
                        return False

                # Login to trading account if credentials provided
                if self.config.login:
                    logger.info(
                        "slave_logging_in",
                        name=self.config.name,
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
                            "slave_login_attempt_failed",
                            name=self.config.name,
                            attempt=attempt,
                            login=self.config.login,
                            error=error,
                        )
                        if attempt < max_retries:
                            time.sleep(retry_delay)
                            continue
                        else:
                            logger.error(
                                "slave_login_failed",
                                name=self.config.name,
                                login=self.config.login,
                                error=error,
                            )
                            return False
                    logger.info(
                        "slave_login_success",
                        name=self.config.name,
                        login=self.config.login,
                    )

                account_info = self.mt5.account_info()
                if account_info:
                    self.state.update_from_account_info(account_info)
                    self.lot_calculator.update_slave_balance(self.state.balance)
                    logger.info(
                        "slave_connected",
                        name=self.config.name,
                        host=self.config.host,
                        port=self.config.port,
                        login=account_info.login,
                        balance=self.state.balance,
                    )
                self._initialized = True
                return True

            except Exception as e:
                logger.warning(
                    "slave_connection_attempt_error",
                    name=self.config.name,
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
                        "slave_connection_error",
                        name=self.config.name,
                        host=self.config.host,
                        port=self.config.port,
                        error=str(e),
                    )
                    self.state.record_error(str(e))
                    return False

        return False

    def shutdown(self) -> None:
        """Shutdown the executor."""
        if self.mt5:
            try:
                self.mt5.shutdown()
            except Exception:
                pass
        self._initialized = False
        self.state.connected = False

    def is_connected(self) -> bool:
        """Check if connected to slave."""
        return self._initialized and self.state.connected

    def update_master_balance(self, balance: float) -> None:
        """Update master balance for lot calculations."""
        self.lot_calculator.update_master_balance(balance)

    def update_account_info(self) -> None:
        """Update account state with latest info."""
        if not self.mt5:
            return

        try:
            account_info = self.mt5.account_info()
            if account_info:
                self.state.update_from_account_info(account_info)
                self.lot_calculator.update_slave_balance(self.state.balance)

        except Exception as e:
            logger.error(
                "slave_account_info_error",
                name=self.config.name,
                error=str(e),
            )
            self.state.record_error(str(e))

    def should_copy_symbol(self, symbol: str) -> bool:
        """Check if this slave should copy trades for given symbol."""
        return self.config.should_copy_symbol(symbol)

    def get_trade_direction(self, master_type: int) -> int:
        """Get trade direction, optionally inverted."""
        if self.config.invert_trades:
            return PositionType.SELL.value if master_type == PositionType.BUY.value else PositionType.BUY.value
        return master_type

    async def open_position(self, master_pos: PositionSnapshot) -> Optional[Any]:
        """
        Open a position mirroring the master.

        Args:
            master_pos: Master position to copy

        Returns:
            Trade result from MT5, or None on error
        """
        if not self.mt5:
            return None

        try:
            # Check symbol availability
            symbol_info = self.mt5.symbol_info(master_pos.symbol)
            if symbol_info is None:
                logger.error(
                    "symbol_not_found",
                    symbol=master_pos.symbol,
                    slave=self.config.name,
                )
                return None

            # Enable symbol if not visible
            if not symbol_info.visible:
                self.mt5.symbol_select(master_pos.symbol, True)

            # Calculate lot size
            lot = self.lot_calculator.calculate(master_pos.volume, symbol_info)

            # Get trade direction
            direction = self.get_trade_direction(master_pos.type)

            # Get current price
            tick = self.mt5.symbol_info_tick(master_pos.symbol)
            if tick is None:
                logger.error("tick_not_available", symbol=master_pos.symbol)
                return None

            price = tick.ask if direction == PositionType.BUY.value else tick.bid

            # Calculate SL/TP (preserve distance from master entry)
            sl = self._calculate_sl(master_pos, price, direction)
            tp = self._calculate_tp(master_pos, price, direction)

            # Prepare order request
            order_type = OrderType.BUY.value if direction == PositionType.BUY.value else OrderType.SELL.value

            # Determine filling mode from symbol info
            # SYMBOL_FILLING_FOK=1, SYMBOL_FILLING_IOC=2
            # ORDER_FILLING_FOK=0, ORDER_FILLING_IOC=1, ORDER_FILLING_RETURN=2
            filling_mode = 0  # Default to FOK
            if symbol_info.filling_mode & 1:  # FOK supported
                filling_mode = 0
            elif symbol_info.filling_mode & 2:  # IOC supported
                filling_mode = 1
            else:  # Use RETURN as fallback
                filling_mode = 2

            request = {
                "action": TradeAction.DEAL.value,
                "symbol": master_pos.symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": self.config.max_slippage,
                "magic": self.config.magic_number,
                "comment": f"CT:{master_pos.ticket}",
                "type_filling": filling_mode,
            }

            result = self.mt5.order_send(request)

            if result and result.retcode == TradeRetcode.DONE.value:
                logger.info(
                    "position_opened",
                    slave=self.config.name,
                    master_ticket=master_pos.ticket,
                    slave_ticket=result.order,
                    symbol=master_pos.symbol,
                    volume=lot,
                    direction="BUY" if direction == 0 else "SELL",
                )
            else:
                retcode = result.retcode if result else "None"
                comment = result.comment if result else "No result"
                logger.error(
                    "position_open_failed",
                    slave=self.config.name,
                    master_ticket=master_pos.ticket,
                    retcode=retcode,
                    comment=comment,
                )

            return result

        except Exception as e:
            logger.error(
                "position_open_error",
                slave=self.config.name,
                master_ticket=master_pos.ticket,
                error=str(e),
            )
            self.state.record_error(str(e))
            return None

    async def close_position(
        self,
        slave_ticket: int,
        volume: Optional[float] = None,
    ) -> Optional[Any]:
        """
        Close a position (full or partial).

        Args:
            slave_ticket: Ticket of the position to close
            volume: Volume to close (None = full close)

        Returns:
            Trade result from MT5, or None on error
        """
        if not self.mt5:
            return None

        try:
            # Get position - use positions_get() without ticket param for better compatibility
            # The ticket param may not work reliably with mt5linux remote calls
            all_positions = self.mt5.positions_get()
            pos = None
            if all_positions:
                for p in all_positions:
                    if p.ticket == slave_ticket:
                        pos = p
                        break

            if not pos:
                logger.warning(
                    "position_not_found",
                    slave=self.config.name,
                    ticket=slave_ticket,
                )
                return None
            close_volume = volume if volume else pos.volume

            # Get current price
            tick = self.mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                logger.error("tick_not_available", symbol=pos.symbol)
                return None

            # Close BUY at bid, SELL at ask
            price = tick.bid if pos.type == PositionType.BUY.value else tick.ask
            close_type = OrderType.SELL.value if pos.type == PositionType.BUY.value else OrderType.BUY.value

            # Get symbol info for filling mode
            symbol_info = self.mt5.symbol_info(pos.symbol)
            filling_mode = 0  # Default to FOK
            if symbol_info:
                if symbol_info.filling_mode & 1:  # FOK supported
                    filling_mode = 0
                elif symbol_info.filling_mode & 2:  # IOC supported
                    filling_mode = 1
                else:  # Use RETURN as fallback
                    filling_mode = 2

            request = {
                "action": TradeAction.DEAL.value,
                "symbol": pos.symbol,
                "volume": close_volume,
                "type": close_type,
                "position": slave_ticket,
                "price": price,
                "deviation": self.config.max_slippage,
                "magic": self.config.magic_number,
                "comment": "CT:close",
                "type_filling": filling_mode,
            }

            result = self.mt5.order_send(request)

            if result and result.retcode == TradeRetcode.DONE.value:
                close_type_str = "partial" if volume else "full"
                logger.info(
                    "position_closed",
                    slave=self.config.name,
                    ticket=slave_ticket,
                    close_type=close_type_str,
                    volume=close_volume,
                )
            else:
                retcode = result.retcode if result else "None"
                logger.error(
                    "position_close_failed",
                    slave=self.config.name,
                    ticket=slave_ticket,
                    retcode=retcode,
                )

            return result

        except Exception as e:
            logger.error(
                "position_close_error",
                slave=self.config.name,
                ticket=slave_ticket,
                error=str(e),
            )
            self.state.record_error(str(e))
            return None

    async def modify_position(
        self,
        slave_ticket: int,
        sl: float,
        tp: float,
    ) -> Optional[Any]:
        """
        Modify SL/TP of an existing position.

        Args:
            slave_ticket: Position ticket
            sl: New stop loss
            tp: New take profit

        Returns:
            Trade result from MT5, or None on error
        """
        if not self.mt5:
            return None

        try:
            request = {
                "action": TradeAction.SLTP.value,
                "position": slave_ticket,
                "sl": sl,
                "tp": tp,
            }

            result = self.mt5.order_send(request)

            if result and result.retcode == TradeRetcode.DONE.value:
                logger.info(
                    "position_modified",
                    slave=self.config.name,
                    ticket=slave_ticket,
                    sl=sl,
                    tp=tp,
                )
            else:
                retcode = result.retcode if result else "None"
                logger.error(
                    "position_modify_failed",
                    slave=self.config.name,
                    ticket=slave_ticket,
                    retcode=retcode,
                )

            return result

        except Exception as e:
            logger.error(
                "position_modify_error",
                slave=self.config.name,
                ticket=slave_ticket,
                error=str(e),
            )
            self.state.record_error(str(e))
            return None

    def get_position_by_ticket(self, ticket: int) -> Optional[Any]:
        """Get a position by ticket."""
        if not self.mt5:
            return None

        try:
            positions = self.mt5.positions_get(ticket=ticket)
            return positions[0] if positions else None
        except Exception:
            return None

    def get_state(self) -> AccountState:
        """Get current account state."""
        return self.state

    def _calculate_sl(
        self,
        master_pos: PositionSnapshot,
        entry_price: float,
        direction: int,
    ) -> float:
        """Calculate SL preserving distance from master."""
        if master_pos.sl <= 0:
            return 0.0

        sl_distance = abs(master_pos.price_open - master_pos.sl)
        if direction == PositionType.BUY.value:
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance

    def _calculate_tp(
        self,
        master_pos: PositionSnapshot,
        entry_price: float,
        direction: int,
    ) -> float:
        """Calculate TP preserving distance from master."""
        if master_pos.tp <= 0:
            return 0.0

        tp_distance = abs(master_pos.price_open - master_pos.tp)
        if direction == PositionType.BUY.value:
            return entry_price + tp_distance
        else:
            return entry_price - tp_distance
