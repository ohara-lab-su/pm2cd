from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0

logger = XLogger(log_level="DEBUG")
# ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
ctrl = PM2CD(
    ip_address=IP_ADDRESS,
    port=PORT,
    timeout_sec=TIMEOUT_SEC,
    logger=logger,
)
try:
    ctrl.close()

    if ctrl.is_connected():
        raise AssertionError("TCP接続が閉じられていません")
    print(f"[PASS] {'close'}: {ctrl.is_connected()}")

except Exception:
    try:
        ctrl.close()
    finally:
        raise
