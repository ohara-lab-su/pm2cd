from ese774_frame.clients import DeviceProxy
import pm2cd.server_fastapi  # DeviceProxy登録

client = DeviceProxy("PM2CDCtrl", server_ip="127.0.0.1", server_port=8000, async_mode=False)
print(client.version())
