from pm2cd.server_fastapi.client_sync import SyncPM2CDClient
from x_logger import XLogger
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 8000

logger = XLogger(log_level="DEBUG")
ctrl = SyncPM2CDClient(
    server_ip=SERVER_IP,
    server_port=SERVER_PORT,
    logger=logger,
)

MOTOR = 0
target = 5

MOTION_TIMEOUT_SEC = 10
result = ctrl.get_position(MOTOR)

print(f"[INFO] {'move'}: {target}")
ctrl.move(MOTOR, target, backlash=False)

# status = ctrl.wait_for_complete(
#     MOTOR,
#     timeout_sec=MOTION_TIMEOUT_SEC,
#     target_position=target,
# )
ctrl.wait_for_complete()

# ret = ctrl.get_position(MOTOR)
ret = ctrl.get_position()
print(ret)
