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
    ctrl.stop_all()
    ctrl.local()
    status = ctrl.get_status(MOTOR)
    if status is None or status.remote_local != "L":
        raise AssertionError("LOCALへ移行していません")
    print(f"[PASS] {'local'}: {status.raw}")
    # ctrl.remote()

finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
