#!/usr/bin/env python
# coding: utf-8
"""PM2CD FastAPI サーバー起動例。"""

from pm2cd.server_fastapi.server import run

WORKER_COUNT = 2


def main() -> None:
    """PM2CD FastAPI サーバーを起動する。"""
    run(
        worker_count=WORKER_COUNT,
    )


if __name__ == "__main__":
    main()
