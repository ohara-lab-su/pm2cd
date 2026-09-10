"""PM16C16 の FastAPI クライアント公開入口。"""

from ese774_frame import DeviceProxy
from ese774_frame.clients import register_device_proxy

from .client_async import AsyncPM2CDClient
from .client_sync import SyncPM2CDClient

register_device_proxy(
    "PM16C16",
    async_client_cls=AsyncPM2CDClient,
    sync_client_cls=SyncPM2CDClient,
    api_spec=None,
    object_name="pm16c16",
    default_async_mode=True,
    aliases=["pm16c16"],
)


__all__ = [
    "AsyncPM16C16Client",
    "SyncPM16C16Client",
    "DeviceProxy",
]
