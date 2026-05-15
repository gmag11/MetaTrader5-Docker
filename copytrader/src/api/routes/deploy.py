"""Deployment endpoints for creating new MT5 slave containers."""

import os
import subprocess
import asyncio
from typing import Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ...models.account import SlaveConfig
from ...models.enums import LotMode
from ..state import get_engine
from ...utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class DeploySlaveRequest(BaseModel):
    """Request model for deploying a new slave container."""

    # MT5 credentials for container
    mt5_login: str = Field(..., description="MT5 account login")
    mt5_password: str = Field(..., description="MT5 account password")
    mt5_server: str = Field(..., description="MT5 server name")

    # Slave configuration
    name: Optional[str] = Field(default=None, description="Unique name for slave (auto-generated if not provided)")
    lot_mode: str = Field(default="proportional", description="Lot mode: exact, fixed, multiplier, proportional")
    lot_value: float = Field(default=1.0, description="Lot value")
    max_lot: float = Field(default=10.0, description="Maximum lot size")
    min_lot: float = Field(default=0.01, description="Minimum lot size")
    magic_number: int = Field(default=123456, description="Magic number for orders")
    invert_trades: bool = Field(default=False, description="Invert trade direction")
    max_slippage: int = Field(default=30, description="Maximum slippage in points")
    symbols_filter: Optional[List[str]] = Field(default=None, description="Symbols to copy")


class DeployResponse(BaseModel):
    """Response for deployment operation."""

    success: bool
    message: str
    container_name: Optional[str] = None
    slave_name: Optional[str] = None
    error: Optional[str] = None


def get_next_slave_port() -> int:
    """Get the next available port for a slave container VNC."""
    # Check existing containers to find highest port in use
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        containers = result.stdout.strip().split("\n")

        # Find highest slave number
        max_num = 0
        for name in containers:
            if name.startswith("mt5-slave"):
                try:
                    num = int(name.replace("mt5-slave", ""))
                    max_num = max(max_num, num)
                except ValueError:
                    pass

        # Return next port (3101 for slave1, 3102 for slave2, etc.)
        return 3100 + max_num + 1
    except Exception:
        return 3102  # Default to second slave port


def create_slave_container(
    container_name: str,
    mt5_login: str,
    mt5_password: str,
    mt5_server: str,
    vnc_port: int,
) -> bool:
    """Create a new MT5 slave container using docker."""
    try:
        # Get the network name from existing containers
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}", "mt5-master"],
            capture_output=True,
            text=True,
        )
        network_id = result.stdout.strip()

        # Get network name
        result = subprocess.run(
            ["docker", "network", "inspect", "-f", "{{.Name}}", network_id],
            capture_output=True,
            text=True,
        )
        network_name = result.stdout.strip()

        if not network_name:
            network_name = "metaTrader5-docker_copytrader-net"

        logger.info(
            "creating_slave_container",
            container=container_name,
            network=network_name,
            vnc_port=vnc_port,
        )

        # Create volume for config
        volume_name = f"{container_name.replace('-', '_')}_config"
        subprocess.run(["docker", "volume", "create", volume_name], check=True)

        # Create the container
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "--hostname", container_name,
            "--network", network_name,
            "-v", f"{volume_name}:/config",
            "-p", f"{vnc_port}:3000",
            "-e", "CUSTOM_USER=admin",
            "-e", "PASSWORD=admin",
            "-e", f"MT5_LOGIN={mt5_login}",
            "-e", f"MT5_PASSWORD={mt5_password}",
            "-e", f"MT5_SERVER={mt5_server}",
            "--restart", "unless-stopped",
            "gmag11/metatrader5_vnc",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(
                "container_creation_failed",
                container=container_name,
                error=result.stderr,
            )
            return False

        logger.info("container_created", container=container_name)
        return True

    except Exception as e:
        logger.error("container_creation_error", error=str(e))
        return False


async def wait_for_container_ready(container_name: str, timeout: int = 180) -> bool:
    """Wait for container to be ready and MT5 server to be accessible."""
    import time

    logger.info("waiting_for_container", container=container_name, timeout=timeout)

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if container is running
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip() != "true":
                await asyncio.sleep(5)
                continue

            # Check if port 8001 is listening inside the container
            result = subprocess.run(
                ["docker", "exec", container_name, "ss", "-tuln"],
                capture_output=True,
                text=True,
            )
            if ":8001" in result.stdout:
                logger.info("container_ready", container=container_name)
                return True

        except Exception as e:
            logger.warning("container_check_error", error=str(e))

        await asyncio.sleep(10)

    logger.warning("container_timeout", container=container_name)
    return False


@router.post("/slave", response_model=DeployResponse)
async def deploy_slave(request: DeploySlaveRequest, background_tasks: BackgroundTasks):
    """
    Deploy a new MT5 slave container and register it with the copytrader.

    This endpoint:
    1. Creates a new Docker container with the MT5 credentials
    2. Waits for the container to be ready
    3. Registers the slave with the copytrader engine
    """
    # Generate name if not provided
    slave_name = request.name or f"slave-{request.mt5_login}"
    container_name = f"mt5-{slave_name.replace('slave-', 'slave')}"

    if not container_name.startswith("mt5-slave"):
        container_name = f"mt5-slave-{request.mt5_login}"

    # Check if container already exists
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if container_name in result.stdout:
        raise HTTPException(
            status_code=400,
            detail=f"Container '{container_name}' already exists",
        )

    # Check if slave already registered
    engine = get_engine()
    if slave_name in engine.slaves:
        raise HTTPException(
            status_code=400,
            detail=f"Slave '{slave_name}' already registered",
        )

    # Get next available port
    vnc_port = get_next_slave_port()

    # Create the container
    success = create_slave_container(
        container_name=container_name,
        mt5_login=request.mt5_login,
        mt5_password=request.mt5_password,
        mt5_server=request.mt5_server,
        vnc_port=vnc_port,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create slave container",
        )

    # Wait for container to be ready
    ready = await wait_for_container_ready(container_name, timeout=180)

    if not ready:
        return DeployResponse(
            success=True,
            message=f"Container created but not yet ready. It may take a few minutes for MT5 to initialize.",
            container_name=container_name,
            slave_name=slave_name,
        )

    # Register slave with engine
    try:
        lot_mode = LotMode(request.lot_mode)
    except ValueError:
        lot_mode = LotMode.PROPORTIONAL

    config = SlaveConfig(
        name=slave_name,
        host=container_name,  # Docker network hostname
        port=8001,
        enabled=True,
        login=int(request.mt5_login),
        password=request.mt5_password,
        server=request.mt5_server,
        lot_mode=lot_mode,
        lot_value=request.lot_value,
        max_lot=request.max_lot,
        min_lot=request.min_lot,
        magic_number=request.magic_number,
        invert_trades=request.invert_trades,
        max_slippage=request.max_slippage,
        symbols_filter=request.symbols_filter,
    )

    result = await engine.add_slave(config)

    if result["success"]:
        return DeployResponse(
            success=True,
            message=f"Slave container deployed and registered successfully",
            container_name=container_name,
            slave_name=slave_name,
        )
    else:
        return DeployResponse(
            success=True,
            message=f"Container created but slave registration failed: {result.get('error', 'Unknown error')}. The container is running and you can try reconnecting later.",
            container_name=container_name,
            slave_name=slave_name,
            error=result.get("error"),
        )


@router.delete("/slave/{name}")
async def remove_slave_container(name: str, close_positions: bool = False):
    """
    Remove a slave container and unregister it from copytrader.

    Args:
        name: Slave name or container name
        close_positions: If true, close all positions before removing
    """
    engine = get_engine()

    # Determine container name
    container_name = name if name.startswith("mt5-") else f"mt5-{name.replace('slave-', 'slave')}"
    slave_name = name.replace("mt5-", "").replace("slave", "slave-") if name.startswith("mt5-") else name

    # Remove from engine first
    if slave_name in engine.slaves:
        result = await engine.remove_slave(slave_name, close_positions)
        if not result["success"]:
            logger.warning("engine_remove_failed", error=result.get("error"))

    # Stop and remove container
    try:
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=30)
        subprocess.run(["docker", "rm", container_name], capture_output=True, timeout=10)

        logger.info("container_removed", container=container_name)

        return {
            "success": True,
            "message": f"Container '{container_name}' stopped and removed",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove container: {str(e)}",
        )
