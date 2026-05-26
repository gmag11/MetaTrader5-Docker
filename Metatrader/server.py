#!/usr/bin/env python3
import os
from rpyc.utils.server import ThreadedServer
from rpyc.core import SlaveService
from rpyc.utils.authenticators import AuthenticationError

AUTH_TOKEN = os.environ.get("MT5_AUTH_TOKEN", "")

def token_authenticator(sock):
    if not AUTH_TOKEN:
        return sock, None
    try:
        sock.settimeout(5)
        data = sock.recv(4096)
        sock.settimeout(None)
        if data.strip().decode("utf-8", errors="replace") != AUTH_TOKEN:
            raise AuthenticationError("Invalid authentication token")
        return sock, {"token": AUTH_TOKEN}
    except AuthenticationError:
        sock.close()
        raise
    except Exception as e:
        sock.close()
        raise AuthenticationError(f"Authentication failed: {e}")

def main():
    host = os.environ.get("MT5_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("MT5_SERVER_PORT", "8001"))
    authenticator = token_authenticator if AUTH_TOKEN else None
    print(f"[{__file__}] Starting mt5linux server on {host}:{port}")
    if AUTH_TOKEN:
        print("[auth] Token authentication is ENABLED")
    else:
        print("[auth] Token authentication is DISABLED (set MT5_AUTH_TOKEN to enable)")
    server = ThreadedServer(
        SlaveService,
        hostname=host,
        port=port,
        reuse_addr=True,
        authenticator=authenticator,
    )
    server.start()

if __name__ == "__main__":
    main()
