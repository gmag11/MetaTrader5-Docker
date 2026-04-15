#!/usr/bin/env bash
# Safely restart the MetaTrader 5 container without touching persisted data.
#
# What this does:
#   1. Verifies the ./config bind mount (where all MT5 data lives) is present
#      and contains the terminal install before touching the container.
#   2. Restarts the container in-place via `docker compose restart` — this
#      preserves the container, the bind mount, and all on-disk state.
#   3. Waits for both ports (3000 VNC, 8001 mt5linux RPC) to come back up.
#   4. Re-verifies terminal64.exe is still present after the restart.
#
# What this will NEVER do:
#   - docker compose down (would stop but not delete; we avoid it anyway)
#   - docker compose down -v (would remove volumes — NEVER)
#   - rm / mv / chown on ./config
#   - docker volume rm
#   - docker system prune
#
# Exit codes: 0 ok, 1 pre-flight failed, 2 restart failed, 3 post-check failed.

set -euo pipefail

cd "$(dirname "$0")"

SERVICE="mt5"
CONFIG_DIR="./config"
TERMINAL_REL="/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
VNC_PORT=3000
RPC_PORT=8001
WAIT_SECONDS=180

log()  { printf '[restart] %s\n' "$*"; }
fail() { printf '[restart] ERROR: %s\n' "$*" >&2; exit "${2:-1}"; }

# --- Pre-flight: data integrity checks -------------------------------------
log "pre-flight: checking persisted data in ${CONFIG_DIR}"

[[ -d "${CONFIG_DIR}" ]] \
  || fail "${CONFIG_DIR} not found — refusing to restart (data would be lost on fresh init)" 1

[[ -f "${CONFIG_DIR}${TERMINAL_REL}" ]] \
  || fail "terminal64.exe missing under ${CONFIG_DIR}${TERMINAL_REL} — refusing to restart" 1

BEFORE_HASH=$(find "${CONFIG_DIR}/.wine/drive_c/Program Files/MetaTrader 5" \
  -maxdepth 2 -type f -printf '%s %p\n' 2>/dev/null | sort | sha256sum | awk '{print $1}')
log "pre-flight: terminal install fingerprint ${BEFORE_HASH:0:12}…"

# --- Restart ---------------------------------------------------------------
log "restarting service '${SERVICE}' in-place (bind mount preserved)"
docker compose restart "${SERVICE}" \
  || fail "docker compose restart failed" 2

# --- Wait for ports --------------------------------------------------------
log "waiting up to ${WAIT_SECONDS}s for ports ${VNC_PORT} and ${RPC_PORT}"
deadline=$(( $(date +%s) + WAIT_SECONDS ))
while :; do
  ports=$(docker exec "${SERVICE}" ss -tuln 2>/dev/null | awk '{print $5}') || ports=""
  vnc_up=0; rpc_up=0
  grep -q ":${VNC_PORT}\$" <<<"${ports}" && vnc_up=1
  grep -q ":${RPC_PORT}\$" <<<"${ports}" && rpc_up=1
  if (( vnc_up == 1 && rpc_up == 1 )); then
    log "both ports listening"
    break
  fi
  if (( $(date +%s) >= deadline )); then
    log "--- last 40 log lines ---"
    docker logs --tail 40 "${SERVICE}" || true
    fail "timed out waiting for ports (vnc=${vnc_up} rpc=${rpc_up})" 3
  fi
  sleep 3
done

# --- Post-check: data still intact -----------------------------------------
[[ -f "${CONFIG_DIR}${TERMINAL_REL}" ]] \
  || fail "POST-CHECK: terminal64.exe missing after restart — investigate immediately" 3

AFTER_HASH=$(find "${CONFIG_DIR}/.wine/drive_c/Program Files/MetaTrader 5" \
  -maxdepth 2 -type f -printf '%s %p\n' 2>/dev/null | sort | sha256sum | awk '{print $1}')

if [[ "${BEFORE_HASH}" != "${AFTER_HASH}" ]]; then
  log "NOTE: terminal dir fingerprint changed (${BEFORE_HASH:0:12}… -> ${AFTER_HASH:0:12}…)"
  log "      this is normal if MT5 rewrote config/log files during shutdown"
fi

log "done — mt5 is up, data intact"
