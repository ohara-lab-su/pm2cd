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
    original = ctrl.get_jog_pulse(MOTOR)
    ctrl.set_jog_pulse(MOTOR, original)
    actual = ctrl.get_jog_pulse(MOTOR)
    if actual != original:
        raise AssertionError("SETJG read-back不一致")
    print(f"[PASS] {'set_jog_pulse'}: {actual}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
