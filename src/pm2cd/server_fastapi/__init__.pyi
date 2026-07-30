from typing import Any, Literal, Optional, overload

from pm2cd.server_fastapi.spec_ctrl import pm2cd_ctrl_api_spec
from pm2cd.server_fastapi.routers.pm2cd_router_ctrl import PM2CDRouterCtrl
from pm2cd.server_fastapi.clients.sync_pm2cd_client import SyncPM2CDClient
from pm2cd.server_fastapi.clients.async_pm2cd_client import AsyncPM2CDClient

@overload
def DeviceProxy(
    device_class: Literal["PM2CDCtrl"],
    *args: Any,
    async_mode: Literal[False] = False,
    **kwargs: Any,
) -> SyncPM2CDClient: ...

@overload
def DeviceProxy(
    device_class: Literal["PM2CDCtrl"],
    *args: Any,
    async_mode: Literal[True],
    **kwargs: Any,
) -> AsyncPM2CDClient: ...

@overload
def DeviceProxy(
    device_class: Literal["pm2cd"],
    *args: Any,
    async_mode: Literal[False] = False,
    **kwargs: Any,
) -> SyncPM2CDClient: ...

@overload
def DeviceProxy(
    device_class: Literal["pm2cd"],
    *args: Any,
    async_mode: Literal[True],
    **kwargs: Any,
) -> AsyncPM2CDClient: ...

def DeviceProxy(
    device_class: str,
    *args: Any,
    async_mode: Optional[bool] = None,
    **kwargs: Any,
) -> Any: ...

__all__ = [
    "pm2cd_ctrl_api_spec",
    "PM2CDRouterCtrl",
    "SyncPM2CDClient",
    "AsyncPM2CDClient",
    "DeviceProxy",
]
