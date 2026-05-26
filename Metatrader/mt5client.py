#!/usr/bin/env python3
import os
import socket
from mt5linux import MetaTrader5 as _MT5
from rpyc.core.stream import SocketStream
from rpyc.utils import factory
from rpyc.core import SlaveService

class MetaTrader5(_MT5):
    def __init__(self, host="localhost", port=18812, token=None, timeout=300):
        self._token = token if token is not None else os.environ.get("MT5_AUTH_TOKEN", "")
        sock = socket.create_connection((host, port))
        if self._token:
            sock.sendall(self._token.encode("utf-8"))
        stream = SocketStream(sock)
        self.__conn = factory.connect_stream(stream, SlaveService)
        self.__conn._config["sync_request_timeout"] = timeout
        self.__conn.execute("import MetaTrader5 as mt5")
        self.__conn.execute("import datetime")
