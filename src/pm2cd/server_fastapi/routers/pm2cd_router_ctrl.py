from typing import Any

from ese774_frame.routers.device_router import DeviceRouter


class PM2CDRouterCtrl(DeviceRouter):
    def __init__(self, device_instance, api_spec=None, logger: Any = None, log_level: str = "INFO"):
        super().__init__(device_instance, api_spec=api_spec, logger=logger, log_level=log_level)
