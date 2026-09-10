"""PM16C16 の FastAPI クライアント公開入口。"""

from ese774_frame import DeviceProxy
from ese774_frame.clients import register_device_proxy

from .client_async import AsyncPM2CDClient
from .client_sync import SyncPM2CDClient

register_device_proxy(
    "PM2CD",
    async_client_cls=AsyncPM2CDClient,
    sync_client_cls=SyncPM2CDClient,
    api_spec=None,
    object_name="pm2cd",
    default_async_mode=True,
    aliases=["pm2cd"],
)


__all__ = [
    "AsyncPM2CDClient",
    "SyncPM2CDClient",
    "DeviceProxy",
]
