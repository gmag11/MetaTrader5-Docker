"""Retry manager with exponential backoff."""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional

from ..models.enums import OperationStatus, TradeRetcode
from ..models.position import QueuedOperation
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RetryManager:
    """
    Manages operation retries with exponential backoff.

    Non-retryable error codes:
    - REJECT: Request rejected
    - INVALID_VOLUME: Invalid volume
    - INVALID_PRICE: Invalid price
    - INVALID_STOPS: Invalid stops
    - NO_MONEY: Not enough money
    """

    NON_RETRYABLE_CODES = {
        TradeRetcode.REJECT.value,
        TradeRetcode.INVALID_VOLUME.value,
        TradeRetcode.INVALID_PRICE.value,
        TradeRetcode.INVALID_STOPS.value,
        TradeRetcode.NO_MONEY.value,
    }

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        """
        Initialize retry manager.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds (doubled each retry)
            max_delay: Maximum delay between retries
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute_with_retry(
        self,
        operation: QueuedOperation,
        executor: Callable,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
    ) -> bool:
        """
        Execute operation with retry logic.

        Args:
            operation: The operation to execute
            executor: Async function to execute the operation
            on_success: Optional callback on success
            on_failure: Optional callback on failure

        Returns:
            True if successful, False if all retries exhausted
        """
        while operation.attempts < operation.max_attempts:
            operation.attempts += 1
            operation.status = OperationStatus.PROCESSING

            try:
                result = await executor(operation.payload)

                if result and result.retcode == TradeRetcode.DONE.value:
                    operation.status = OperationStatus.COMPLETED
                    operation.completed_at = datetime.now()

                    logger.info(
                        "operation_succeeded",
                        operation_type=operation.operation_type.value,
                        master_ticket=operation.master_ticket,
                        slave_name=operation.slave_name,
                        attempts=operation.attempts,
                    )

                    if on_success:
                        await on_success(operation, result)

                    return True

                # Trade server rejection
                error_msg = f"Retcode: {result.retcode if result else 'None'}"
                if result:
                    error_msg += f" - {result.comment}"
                operation.error_message = error_msg

                # Check if retryable
                if result and not self._is_retryable(result.retcode):
                    operation.status = OperationStatus.FAILED

                    logger.error(
                        "operation_failed_non_retryable",
                        operation_type=operation.operation_type.value,
                        master_ticket=operation.master_ticket,
                        slave_name=operation.slave_name,
                        retcode=result.retcode,
                        error=error_msg,
                    )

                    if on_failure:
                        await on_failure(operation, error_msg)

                    return False

            except Exception as e:
                operation.error_message = str(e)
                logger.warning(
                    "operation_attempt_failed",
                    operation_type=operation.operation_type.value,
                    master_ticket=operation.master_ticket,
                    slave_name=operation.slave_name,
                    attempt=operation.attempts,
                    error=str(e),
                )

            # Calculate next retry delay (exponential backoff)
            delay = min(
                self.base_delay * (2 ** (operation.attempts - 1)),
                self.max_delay,
            )
            operation.next_retry_at = datetime.now() + timedelta(seconds=delay)
            operation.status = OperationStatus.PENDING

            logger.info(
                "operation_retry_scheduled",
                operation_type=operation.operation_type.value,
                master_ticket=operation.master_ticket,
                slave_name=operation.slave_name,
                attempt=operation.attempts,
                next_retry_in_seconds=delay,
            )

            await asyncio.sleep(delay)

        # All retries exhausted
        operation.status = OperationStatus.FAILED
        operation.completed_at = datetime.now()

        logger.error(
            "operation_failed_max_retries",
            operation_type=operation.operation_type.value,
            master_ticket=operation.master_ticket,
            slave_name=operation.slave_name,
            attempts=operation.attempts,
            last_error=operation.error_message,
        )

        if on_failure:
            await on_failure(operation, operation.error_message or "Max retries exceeded")

        return False

    def _is_retryable(self, retcode: int) -> bool:
        """Check if the error code is retryable."""
        return retcode not in self.NON_RETRYABLE_CODES

    def create_operation(
        self,
        operation_type,
        master_ticket: int,
        slave_name: str,
        payload: dict,
    ) -> QueuedOperation:
        """Create a new queued operation."""
        return QueuedOperation(
            operation_type=operation_type,
            master_ticket=master_ticket,
            slave_name=slave_name,
            payload=payload,
            max_attempts=self.max_attempts,
        )
