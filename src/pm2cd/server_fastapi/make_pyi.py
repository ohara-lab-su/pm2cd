#!/usr/bin/env python
# coding: utf-8
"""PM16C16 server_fastapi 用 .pyi 生成スクリプト。"""

from pathlib import Path

from ese774_frame.clients.make_pyi_device_client import make_pyi_device_client
from ese774_frame.clients.make_pyi_device_proxy import make_pyi_device_proxy
from pm2cd.pm2cd_ctrl import PM2CD


def main():
    """server_fastapi 配下の client / DeviceProxy .pyi を生成する。"""
    root = Path(__file__).resolve().parent

    make_pyi_device_client(
        filename=str(root / "client_async.pyi"),
        device_class=PM2CD,
        class_name="AsyncPM2CDClient",
        async_mode=True,
    )

    make_pyi_device_client(
        filename=str(root / "client_sync.pyi"),
        device_class=PM2CD,
        class_name="SyncPM2CDClient",
        async_mode=False,
    )

    make_pyi_device_proxy(
        filename=str(root / "__init__.pyi"),
        device_names=["PM2CD", "pm2cd"],
        async_client_module="pm2cd.server_fastapi.client_async",
        async_client_class="AsyncPM2CDClient",
        sync_client_module="pm2cd.server_fastapi.client_sync",
        sync_client_class="SyncPM2CDClient",
        default_async_mode=True,
    )


if __name__ == "__main__":
    main()
