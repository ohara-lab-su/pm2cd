from ese774_frame.clients import register_device_proxy

from pm2cd.server_fastapi.clients.async_pm2cd_client import AsyncPM2CDClient
from pm2cd.server_fastapi.clients.sync_pm2cd_client import SyncPM2CDClient
from pm2cd.server_fastapi.routers.pm2cd_router_ctrl import PM2CDRouterCtrl
from pm2cd.server_fastapi.spec_ctrl import pm2cd_ctrl_api_spec


register_device_proxy(
    "PM2CDCtrl",
    async_client_cls=AsyncPM2CDClient,
    sync_client_cls=SyncPM2CDClient,
    api_spec=pm2cd_ctrl_api_spec,
    default_async_mode=True,
    aliases=["pm2cd"],
)

__all__ = [
    "pm2cd_ctrl_api_spec",
    "PM2CDRouterCtrl",
    "SyncPM2CDClient",
    "AsyncPM2CDClient",
]
