from pathlib import Path

from ese774_frame.clients.make_pyi_device_client import make_pyi_device_client
from ese774_frame.clients.make_pyi_device_proxy import make_pyi_device_proxy
from ese774_frame.routers.make_pyi_device_router import make_pyi_device_router

from pm2cd.server_fastapi.spec_ctrl import pm2cd_ctrl_api_spec


def main():
    root = Path(__file__).resolve().parent
    make_pyi_device_client(
        filename=str(root / "clients" / "sync_pm2cd_client.pyi"),
        api_spec=pm2cd_ctrl_api_spec,
        class_name="SyncPM2CDClient",
        async_mode=False,
    )
    make_pyi_device_client(
        filename=str(root / "clients" / "async_pm2cd_client.pyi"),
        api_spec=pm2cd_ctrl_api_spec,
        class_name="AsyncPM2CDClient",
        async_mode=True,
    )
    make_pyi_device_router(
        filename=str(root / "routers" / "pm2cd_router_ctrl.pyi"),
        api_spec=pm2cd_ctrl_api_spec,
        class_name="PM2CDRouterCtrl",
    )
    make_pyi_device_proxy(
        filename=str(root / "__init__.pyi"),
        import_lines=[
            "from pm2cd.server_fastapi.spec_ctrl import pm2cd_ctrl_api_spec",
            "from pm2cd.server_fastapi.routers.pm2cd_router_ctrl import PM2CDRouterCtrl",
            "from pm2cd.server_fastapi.clients.sync_pm2cd_client import SyncPM2CDClient",
            "from pm2cd.server_fastapi.clients.async_pm2cd_client import AsyncPM2CDClient",
        ],
        device_class="PM2CDCtrl",
        aliases=["pm2cd"],
        sync_client_class_name="SyncPM2CDClient",
        async_client_class_name="AsyncPM2CDClient",
        all_names=[
            "pm2cd_ctrl_api_spec",
            "PM2CDRouterCtrl",
            "SyncPM2CDClient",
            "AsyncPM2CDClient",
            "DeviceProxy",
        ],
    )


if __name__ == "__main__":
    main()
