from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0

logger = XLogger(log_level="DEBUG")
# ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
ctrl = PM2CD(
    ip_address=IP_ADDRESS,
    port=PORT,
    timeout_sec=TIMEOUT_SEC,
    logger=logger,
)
try:
    cw = ctrl.get_limit(MOTOR, "cw")
    ccw = ctrl.get_limit(MOTOR, "ccw")
    print(f"[PASS] {'get_limit'}: {(cw, ccw)}")

finally:
    try:
        # ctrl.emergency_stop_all()
        ctrl.stop()
    finally:
        ctrl.close()
