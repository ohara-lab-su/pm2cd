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
    original_high = ctrl.get_high_speed(MOTOR)
    original_middle = ctrl.get_middle_speed(MOTOR)
    original_low = ctrl.get_low_speed(MOTOR)

    try:
        ctrl.set_speed(MOTOR, original_high)
        expected_middle = max(original_high // 3, 5)
        expected_low = max(original_high // 10, 5)

        if ctrl.get_middle_speed(MOTOR) != expected_middle:
            raise AssertionError("set_speed MSPD不一致")
        if ctrl.get_low_speed(MOTOR) != expected_low:
            raise AssertionError("set_speed LSPD不一致")
        print(f"[PASS] {'set_speed'}: {'OK'}")
    finally:
        ctrl.set_speed_profile(MOTOR, original_low, original_middle, original_high)
finally:
    try:
        # ctrl.emergency_stop_all()
        ctrl.stop()
    finally:
        ctrl.close()
