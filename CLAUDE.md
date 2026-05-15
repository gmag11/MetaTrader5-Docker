# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker containerization project for MetaTrader 5, providing:
- MetaTrader 5 running in a Docker container via Wine
- Web-based VNC access through KasmVNC (port 3000)
- Python remote access via RPyC/mt5linux (port 8001)

**Base Image**: `ghcr.io/linuxserver/baseimage-kasmvnc:debianbookworm`
**Platform**: linux/amd64 only

## Build and Run Commands

```bash
# Build the Docker image
docker build -t mt5 .

# Run the container
docker run -d -p 3000:3000 -p 8001:8001 -v config:/config mt5

# Using Docker Compose (Linux - uses bind mount)
docker compose up -d

# Using Docker Compose (Windows - uses named volume)
docker compose -f docker-compose-windows.yaml up -d
```

## Architecture

```
Container Startup Flow (Metatrader/start.sh):
1. Check dependencies (Wine, curl)
2. Install Mono if not present
3. Install MetaTrader 5 via mt5setup.exe
4. Launch MetaTrader terminal64.exe via Wine
5. Install Python 3.9.13 in Wine environment
6. Install Python libraries (MetaTrader5, mt5linux) in both Wine and Linux
7. Start mt5linux RPyC server on port 8001
```

**Key paths inside container:**
- MetaTrader installation: `/config/.wine/drive_c/Program Files/MetaTrader 5/`
- Wine prefix: `/config/.wine`
- MQL5 files: `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `CUSTOM_USER` | Container username |
| `PASSWORD` | VNC/web interface password |
| `MT5_LOGIN` | MT5 account login number (preferred over MT5_CMD_OPTIONS) |
| `MT5_PASSWORD` | MT5 account password |
| `MT5_SERVER` | MT5 server name (e.g., `Weltrade-Demo`) |
| `MT5_PORTABLE` | Set to `true` to run MT5 in portable mode |
| `MT5_CMD_OPTIONS` | Legacy: MetaTrader command line options (e.g., `/login:123 /password:xxx`) |
| `MT5_SERVER_PORT` | RPyC server port (default: 8001) |
| `MT5_SETUP_URL` | Custom MT5 installer URL (default: official MetaQuotes) |
| `WINEPREFIX` | Wine environment path (default: /config/.wine) |

**Note**: Use individual `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` variables instead of `MT5_CMD_OPTIONS` to avoid issues with special characters in passwords.

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-publish.yml`):
- Triggers on tag push or manual workflow dispatch
- Publishes to Docker Hub (`gmag11/metatrader5_vnc`) and GHCR
- Required secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`

## Key Files

- `Dockerfile` - Container build definition
- `Metatrader/start.sh` - Initialization script that installs MT5, Python, and starts services
- `root/defaults/autostart` - KasmVNC autostart configuration
- `docker-compose.yaml` - Linux configuration (bind mount)
- `docker-compose-windows.yaml` - Windows configuration (named volume)
