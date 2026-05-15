"""Lot size calculation service."""

from typing import Optional

from ..models.account import SlaveConfig
from ..models.enums import LotMode
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LotCalculator:
    """
    Calculates appropriate lot size for slave accounts based on configured mode.

    Modes:
    - EXACT: Same lot size as master
    - FIXED: Fixed lot size for all trades
    - MULTIPLIER: Master lot * multiplier
    - PROPORTIONAL: Based on balance ratio (slave_balance / master_balance)
    """

    def __init__(self, config: SlaveConfig, master_balance: float = 0.0):
        """
        Initialize lot calculator.

        Args:
            config: Slave account configuration
            master_balance: Master account balance (for proportional mode)
        """
        self.config = config
        self.master_balance = master_balance
        self.slave_balance: float = 0.0

    def update_master_balance(self, balance: float) -> None:
        """Update master account balance."""
        self.master_balance = balance

    def update_slave_balance(self, balance: float) -> None:
        """Update slave account balance."""
        self.slave_balance = balance

    def calculate(
        self,
        master_lot: float,
        symbol_info: Optional[object] = None,
    ) -> float:
        """
        Calculate lot size based on mode.

        Args:
            master_lot: Lot size on master account
            symbol_info: Symbol information from MT5 (optional, for constraints)

        Returns:
            Calculated lot size, clamped to valid range
        """
        mode = self.config.lot_mode

        if mode == LotMode.EXACT:
            lot = master_lot

        elif mode == LotMode.FIXED:
            lot = self.config.lot_value

        elif mode == LotMode.MULTIPLIER:
            lot = master_lot * self.config.lot_value

        elif mode == LotMode.PROPORTIONAL:
            if self.master_balance > 0:
                ratio = self.slave_balance / self.master_balance
                lot = master_lot * ratio
            else:
                # Fallback to exact copy if master balance unknown
                lot = master_lot
                logger.warning(
                    "proportional_fallback",
                    reason="master_balance_zero",
                    slave=self.config.name,
                )

        else:
            lot = master_lot  # Fallback to exact copy

        # Apply user-defined constraints
        lot = max(self.config.min_lot, min(self.config.max_lot, lot))

        # Apply symbol constraints if available
        if symbol_info:
            volume_min = getattr(symbol_info, "volume_min", 0.01)
            volume_max = getattr(symbol_info, "volume_max", 1000.0)
            volume_step = getattr(symbol_info, "volume_step", 0.01)

            lot = max(volume_min, lot)
            lot = min(volume_max, lot)

            # Round to lot step
            if volume_step > 0:
                lot = round(lot / volume_step) * volume_step

        # Final rounding to avoid floating point issues
        lot = round(lot, 2)

        logger.debug(
            "lot_calculated",
            mode=mode.value,
            master_lot=master_lot,
            slave_lot=lot,
            slave=self.config.name,
        )

        return lot

    def calculate_partial_close_volume(
        self,
        master_closed_volume: float,
        master_original_volume: float,
        slave_current_volume: float,
        symbol_info: Optional[object] = None,
    ) -> float:
        """
        Calculate volume to close for partial close.

        Uses the same proportion as master.

        Args:
            master_closed_volume: Volume closed on master
            master_original_volume: Original volume on master before partial close
            slave_current_volume: Current volume on slave
            symbol_info: Symbol information for constraints

        Returns:
            Volume to close on slave
        """
        if master_original_volume <= 0:
            return 0.0

        # Calculate close ratio
        close_ratio = master_closed_volume / master_original_volume

        # Apply ratio to slave volume
        close_volume = slave_current_volume * close_ratio

        # Apply symbol constraints
        if symbol_info:
            volume_min = getattr(symbol_info, "volume_min", 0.01)
            volume_step = getattr(symbol_info, "volume_step", 0.01)

            # Ensure minimum volume
            if close_volume < volume_min:
                close_volume = volume_min

            # Round to step
            if volume_step > 0:
                close_volume = round(close_volume / volume_step) * volume_step

        close_volume = round(close_volume, 2)

        logger.debug(
            "partial_close_volume_calculated",
            close_ratio=close_ratio,
            slave_close_volume=close_volume,
        )

        return close_volume
