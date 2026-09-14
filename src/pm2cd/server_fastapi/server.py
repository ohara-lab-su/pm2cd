#!/usr/bin/env python
# coding: utf-8
"""PM2CD FastAPI サーバー起動用モジュール。"""

from ese774_frame.api_server import FastApiServer
from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
DEVICE_PORT = 7777
TIMEOUT_SEC = 3.0
HOST = "127.0.0.1"
PORT = 8000


def create_server() -> FastApiServer:
    """PM2CD 用 FastApiServer を作成する。"""
    return FastApiServer(
        device_cls=PM2CD,
        router_cls=None,
        config=None,
        api_spec=None,
        object_name="pm2cd",
        device_kwargs={
            "ip_address": IP_ADDRESS,
            "port": DEVICE_PORT,
            "timeout_sec": TIMEOUT_SEC,
        },
        lifespan_msg_prefix="PM2CD",
    )


def run() -> None:
    """PM2CD FastAPI サーバーを起動する。"""
    server = create_server()
    server.run(
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    run()
