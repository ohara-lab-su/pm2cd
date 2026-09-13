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
    low = ctrl.get_low_speed(MOTOR)
    middle = ctrl.get_middle_speed(MOTOR)
    high = ctrl.get_high_speed(MOTOR)
    ctrl.set_speed_profile(MOTOR, low, middle, high)
    print(f"[PASS] {'set_speed_profile'}: {(low, middle, high)}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
