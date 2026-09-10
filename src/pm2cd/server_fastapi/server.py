#!/usr/bin/env python
# coding: utf-8
"""PM16C16 FastAPI サーバー起動用モジュール。"""

import argparse

from ese774_frame.api_server import FastApiServer
from pm2cd.pm2cd_ctrl import PM2CD


def create_server(
    ip_address: str,
    device_port: int = 7777,
    timeout_sec: float = 3.0,
) -> FastApiServer:
    """PM16C16 用 FastApiServer を作成する。"""
    return FastApiServer(
        device_cls=PM2CD,
        router_cls=None,
        config=None,
        api_spec=None,
        object_name="pm2cd",
        device_kwargs={
            "ip_address": ip_address,
            "port": device_port,
            "timeout_sec": timeout_sec,
        },
        lifespan_msg_prefix="PM2CD",
    )


def run(
    ip_address: str,
    device_port: int = 7777,
    timeout_sec: float = 3.0,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """PM2CD FastAPI サーバーを起動する。"""
    server = create_server(
        ip_address=ip_address,
        device_port=device_port,
        timeout_sec=timeout_sec,
    )
    server.run(
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    """コマンドライン引数を読み込み FastAPI サーバーを起動する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("ip_address")
    parser.add_argument("--device-port", type=int, default=7777)
    parser.add_argument("--timeout-sec", type=float, default=3.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    run(
        ip_address=args.ip_address,
        device_port=args.device_port,
        timeout_sec=args.timeout_sec,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
