"""Position change detection."""

from typing import Dict

from ..models.position import (
    ChangeSet,
    Modification,
    PartialClose,
    PositionSnapshot,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ChangeDetector:
    """
    Detects position changes by comparing snapshots.

    Why polling over events:
    - MT5 RPyC doesn't support event subscriptions
    - Polling at 500ms provides acceptable latency for most use cases
    - Simpler to implement and debug
    - More resilient to connection issues
    """

    def __init__(self, volume_tolerance: float = 0.001):
        """
        Initialize detector.

        Args:
            volume_tolerance: Tolerance for volume comparisons (floating point)
        """
        self.previous_snapshot: Dict[int, PositionSnapshot] = {}
        self.volume_tolerance = volume_tolerance

    def compute_diff(
        self, current: Dict[int, PositionSnapshot]
    ) -> ChangeSet:
        """
        Compare current positions against last snapshot.

        Args:
            current: Current positions keyed by ticket

        Returns:
            ChangeSet containing all detected changes
        """
        changes = ChangeSet()

        current_tickets = set(current.keys())
        previous_tickets = set(self.previous_snapshot.keys())

        # New positions: in current but not in previous
        for ticket in current_tickets - previous_tickets:
            changes.new_positions.append(current[ticket])
            logger.info(
                "new_position_detected",
                ticket=ticket,
                symbol=current[ticket].symbol,
                volume=current[ticket].volume,
                type=current[ticket].type,
            )

        # Closed positions: in previous but not in current
        for ticket in previous_tickets - current_tickets:
            changes.closed_positions.append(self.previous_snapshot[ticket])
            logger.info(
                "closed_position_detected",
                ticket=ticket,
                symbol=self.previous_snapshot[ticket].symbol,
            )

        # Check existing positions for modifications
        for ticket in current_tickets & previous_tickets:
            curr = current[ticket]
            prev = self.previous_snapshot[ticket]

            # Volume decrease = partial close
            if curr.volume < prev.volume - self.volume_tolerance:
                partial = PartialClose(
                    ticket=ticket,
                    closed_volume=round(prev.volume - curr.volume, 2),
                    remaining_volume=curr.volume,
                    original_volume=prev.volume,
                )
                changes.partial_closes.append(partial)
                logger.info(
                    "partial_close_detected",
                    ticket=ticket,
                    closed_volume=partial.closed_volume,
                    remaining_volume=partial.remaining_volume,
                )

            # SL/TP change = modification
            sl_changed = abs(curr.sl - prev.sl) > 0.00001
            tp_changed = abs(curr.tp - prev.tp) > 0.00001
            if sl_changed or tp_changed:
                mod = Modification(
                    ticket=ticket,
                    old_sl=prev.sl,
                    new_sl=curr.sl,
                    old_tp=prev.tp,
                    new_tp=curr.tp,
                )
                changes.modifications.append(mod)
                logger.info(
                    "modification_detected",
                    ticket=ticket,
                    old_sl=prev.sl,
                    new_sl=curr.sl,
                    old_tp=prev.tp,
                    new_tp=curr.tp,
                )

        # Update snapshot for next comparison
        self.previous_snapshot = current.copy()

        return changes

    def reset(self) -> None:
        """Reset the detector state."""
        self.previous_snapshot.clear()

    def set_initial_snapshot(
        self, positions: Dict[int, PositionSnapshot]
    ) -> None:
        """
        Set initial snapshot without detecting changes.

        Useful for initialization to avoid copying existing positions.

        Args:
            positions: Current positions to use as baseline
        """
        self.previous_snapshot = positions.copy()
        logger.info(
            "initial_snapshot_set",
            position_count=len(positions),
        )
