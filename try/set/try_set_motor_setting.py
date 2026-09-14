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
    original = ctrl.get_motor_setting(MOTOR)
    ctrl.set_motor_setting(
        MOTOR, original.drive_enabled, original.hold_mode, original.output_mode
    )

    actual = ctrl.get_motor_setting(MOTOR)
    if actual.raw != original.raw:
        raise AssertionError("SETMT read-back不一致")
    print(f"[PASS] {'set_motor_setting'}: {actual}")

finally:
    try:
        # ctrl.emergency_stop_all()
        ctrl.stop()
    finally:
        ctrl.close()
