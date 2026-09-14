from pm2cd.server_fastapi.client_sync import SyncPM2CDClient
from x_logger import XLogger

SERVER_IP = "127.0.0.1"
SERVER_PORT = 8000

logger = XLogger(log_level="DEBUG")
ctrl = SyncPM2CDClient(
    server_ip=SERVER_IP,
    server_port=SERVER_PORT,
    logger=logger,
)

MOTOR = 0

result = ctrl.get_position(MOTOR)
print(result)
