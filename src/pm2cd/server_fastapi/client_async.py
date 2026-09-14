#!/usr/bin/env python
# coding: utf-8
"""PM16C16 用の非同期 FastAPI クライアント。"""

from typing import Any, Optional

from ese774_frame.clients.async_device_client import AsyncDeviceClient


class AsyncPM2CDClient(AsyncDeviceClient):
    """PM2CD へ接続する非同期クライアント。"""

    def __init__(
        self,
        server_ip: str = "127.0.0.1",
        server_port: int = 8000,
        logger: Optional[Any] = None,
        log_level: str = "INFO",
    ):
        super().__init__(
            server_ip=server_ip,
            server_port=server_port,
            object_name="pm2cd",
            api_spec=None,
            logger=logger,
            log_level=log_level,
        )
