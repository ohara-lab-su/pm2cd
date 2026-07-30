from typing import Any, Optional

from ese774_frame.clients.async_device_client import AsyncDeviceClient

from pm2cd.server_fastapi.spec_ctrl import pm2cd_ctrl_api_spec


class AsyncPM2CDClient(AsyncDeviceClient):
    def __init__(
        self,
        config=None,
        server_ip: Optional[str] = None,
        server_port: Optional[int] = None,
        logger: Any = None,
        log_level: str = "INFO",
    ):
        if logger is None:
            import logging

            logging.basicConfig(level=log_level.upper())
            logger = logging.getLogger(__name__)

        if config is not None:
            server_ip = config.SERVER_IP
            server_port = config.SERVER_PORT
        base_url = f"http://{server_ip}:{server_port}"

        super().__init__(
            server_ip=server_ip,
            server_port=server_port,
            api_spec=pm2cd_ctrl_api_spec,
            base_url=base_url,
            logger=logger,
        )
