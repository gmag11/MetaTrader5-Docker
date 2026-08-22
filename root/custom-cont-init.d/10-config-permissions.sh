#!/bin/sh

set -eu

if [ ! -d /config ]; then
    echo "Configuration directory /config does not exist." >&2
    exit 1
fi

# Ensure the wine prefix and everything under /config is owned by the user
# the services run as (abc, mapped to PUID/PGID at boot). Without this, a
# /config volume initialized by a different host UID (e.g. rootless Podman,
# bind mounts created before the first boot) leaves ~/.wine and ~/.cache
# unwritable for wine/MT5 and every start fails with "is not owned by you"
# or ".cache: Permission denied".
chown -R abc:abc /config

# u+rwX keeps directories traversable and files writable for the owner while
# leaving group/other bits untouched, so rootless setups that map the abc UID
# to a different host UID keep working.
chmod -R u+rwX /config
