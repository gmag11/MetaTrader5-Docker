"""Configuration management."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from ..models.enums import LotMode


class MasterConfigModel(BaseModel):
    """Master account configuration."""

    name: str = "master"
    host: str = "mt5-master"
    port: int = 8001
    # MT5 login credentials (optional - for auto-login)
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None


class SlaveConfigModel(BaseModel):
    """Slave account configuration."""

    name: str
    host: str
    port: int = 8001
    enabled: bool = True
    # MT5 login credentials (optional - for auto-login)
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    # Lot configuration
    lot_mode: LotMode = LotMode.EXACT
    lot_value: float = 1.0
    max_lot: float = 10.0
    min_lot: float = 0.01
    symbols_filter: Optional[list[str]] = None
    magic_number: int = 123456
    invert_trades: bool = False
    max_slippage: int = 20


class SettingsModel(BaseModel):
    """Copytrader settings."""

    polling_interval_ms: int = 500
    retry_attempts: int = 3
    retry_delay_ms: int = 1000
    connection_timeout_ms: int = 5000
    heartbeat_interval_ms: int = 10000


class DatabaseConfigModel(BaseModel):
    """Database configuration."""

    type: str = "sqlite"
    path: str = "/app/data/copytrader.db"
    # PostgreSQL options
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None


class ApiConfigModel(BaseModel):
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8080


class LoggingConfigModel(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"  # json or text


class CopyTraderConfig(BaseModel):
    """Complete copytrader configuration."""

    master: MasterConfigModel = Field(default_factory=MasterConfigModel)
    slaves: list[SlaveConfigModel] = Field(default_factory=list)
    settings: SettingsModel = Field(default_factory=SettingsModel)
    database: DatabaseConfigModel = Field(default_factory=DatabaseConfigModel)
    api: ApiConfigModel = Field(default_factory=ApiConfigModel)
    logging: LoggingConfigModel = Field(default_factory=LoggingConfigModel)


class Settings(BaseSettings):
    """Environment-based settings."""

    config_path: str = "/app/config/copytrader.yaml"
    log_level: str = "INFO"
    database_path: str = "/app/data/copytrader.db"

    class Config:
        env_prefix = ""
        case_sensitive = False


class ConfigManager:
    """Manages copytrader configuration."""

    def __init__(self, config_path: Optional[str] = None):
        self.settings = Settings()
        self.config_path = Path(config_path or self.settings.config_path)
        self._config: Optional[CopyTraderConfig] = None

    def load(self) -> CopyTraderConfig:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if self.config_path.exists():
            with open(self.config_path) as f:
                data = yaml.safe_load(f) or {}
            self._config = CopyTraderConfig(**data)
        else:
            self._config = CopyTraderConfig()

        # Apply environment overrides
        self._apply_env_overrides()

        return self._config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if not self._config:
            return

        # Override log level from environment
        if self.settings.log_level:
            self._config.logging.level = self.settings.log_level

        # Override database path from environment
        if self.settings.database_path:
            self._config.database.path = self.settings.database_path

        # Master host/port from environment
        master_host = os.getenv("MASTER_HOST")
        master_port = os.getenv("MASTER_PORT")
        if master_host:
            self._config.master.host = master_host
        if master_port:
            self._config.master.port = int(master_port)

    def get_config(self) -> CopyTraderConfig:
        """Get loaded configuration."""
        if self._config is None:
            return self.load()
        return self._config

    def reload(self) -> CopyTraderConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load()
