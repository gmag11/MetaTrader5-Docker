"""Main entry point for the copytrader service."""

import asyncio
import signal
import sys
from typing import Optional

import uvicorn

from .api.app import create_app
from .api.state import set_engine
from .core.engine import SyncEngine
from .db.sqlite import SQLiteDatabase
from .models.account import MasterConfig, SlaveConfig
from .models.enums import LotMode
from .utils.config import ConfigManager
from .utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class CopyTraderService:
    """Main copytrader service orchestrator."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the service.

        Args:
            config_path: Path to configuration file
        """
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load()
        self.db: Optional[SQLiteDatabase] = None
        self.engine: Optional[SyncEngine] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the copytrader service."""
        # Setup logging
        setup_logging(
            level=self.config.logging.level,
            format_type=self.config.logging.format,
        )

        logger.info(
            "copytrader_starting",
            master=self.config.master.name,
            slaves=[s.name for s in self.config.slaves if s.enabled],
        )

        # Initialize database
        self.db = SQLiteDatabase(self.config.database.path)
        await self.db.initialize()

        # Create engine
        master_config = MasterConfig(
            name=self.config.master.name,
            host=self.config.master.host,
            port=self.config.master.port,
            login=self.config.master.login,
            password=self.config.master.password,
            server=self.config.master.server,
        )

        slaves_config = [
            SlaveConfig(
                name=s.name,
                host=s.host,
                port=s.port,
                enabled=s.enabled,
                login=s.login,
                password=s.password,
                server=s.server,
                lot_mode=s.lot_mode,
                lot_value=s.lot_value,
                max_lot=s.max_lot,
                min_lot=s.min_lot,
                symbols_filter=s.symbols_filter,
                magic_number=s.magic_number,
                invert_trades=s.invert_trades,
                max_slippage=s.max_slippage,
            )
            for s in self.config.slaves
        ]

        self.engine = SyncEngine(
            master_config=master_config,
            slaves_config=slaves_config,
            db=self.db,
            polling_interval_ms=self.config.settings.polling_interval_ms,
            retry_attempts=self.config.settings.retry_attempts,
        )

        # Set engine for API
        set_engine(self.engine)

        # Start engine
        if not await self.engine.start():
            logger.error("engine_start_failed")
            return

        logger.info("copytrader_started")

    async def run(self) -> None:
        """Run the service (engine loop)."""
        if self.engine:
            await self.engine.run()

    async def stop(self) -> None:
        """Stop the service."""
        logger.info("copytrader_stopping")

        if self.engine:
            await self.engine.stop()

        if self.db:
            await self.db.close()

        logger.info("copytrader_stopped")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()


async def run_api(config) -> None:
    """Run the API server."""
    app = create_app()

    config_uvicorn = uvicorn.Config(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="warning",
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()


async def main() -> None:
    """Main entry point."""
    # Get config path from environment or use default
    import os

    config_path = os.getenv("CONFIG_PATH", "/app/config/copytrader.yaml")

    # Initialize service
    service = CopyTraderService(config_path)

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("shutdown_signal_received")
        service.request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Start service
        await service.start()

        # Run API and engine concurrently
        await asyncio.gather(
            run_api(service.config),
            service.run(),
        )

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("service_error", error=str(e))
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
