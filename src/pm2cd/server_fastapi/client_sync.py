#!/usr/bin/env python
# coding: utf-8
"""PM16C16 用の同期 FastAPI クライアント。"""

from typing import Any, Optional

from ese774_frame.clients.sync_device_client import SyncDeviceClient


class SyncPM2CDClient(
    SyncDeviceClient,
):
    """PM16C16 FastAPI サーバーへ接続する同期クライアント。"""

    def __init__(
        self,
        server_ip: str,
        server_port: int,
        logger: Optional[Any] = None,
        log_level: str = "INFO",
    ):
        if logger is None:
            import logging

            logging.basicConfig(level=log_level)
            logger = logging.getLogger(__name__)

        self._logger = logger

        base_url = "http://{}:{}".format(
            server_ip,
            server_port,
        )
        self._base_url = base_url

        self._logger.info("[CLIENT] server_ip = {}".format(server_ip))
        self._logger.info("[CLIENT] server_port = {}".format(server_port))
        self._logger.info("[CLIENT] base_url = {}".format(base_url))

        super().__init__(
            server_ip=server_ip,
            server_port=server_port,
            object_name="pm16c16",
            api_spec=None,
            base_url=base_url,
            logger=logger,
        )
