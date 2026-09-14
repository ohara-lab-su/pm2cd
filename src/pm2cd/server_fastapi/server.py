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
WORKER_COUNT = 2


def create_server(
    worker_count: int = WORKER_COUNT,
) -> FastApiServer:
    """PM2CD 用 FastApiServer を作成する。

    Args:
        worker_count: ProcessExecutor の worker process 数。

    Returns:
        PM2CD 用 FastApiServer。
    """
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
            "worker_count": worker_count,
        },
        lifespan_msg_prefix="PM2CD",
    )


def run(
    worker_count: int = WORKER_COUNT,
) -> None:
    """PM2CD FastAPI サーバーを起動する。

    Args:
        worker_count: ProcessExecutor の worker process 数。
    """
    server = create_server(
        worker_count=worker_count,
    )
    server.run(
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    run()
