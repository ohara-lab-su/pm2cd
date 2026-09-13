import time
from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"

PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
# TEST_PULSE = 10
MOTION_TIMEOUT_SEC = 30.0

logger = XLogger(log_level="DEBUG")
# ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
ctrl = PM2CD(
    ip_address=IP_ADDRESS,
    port=PORT,
    timeout_sec=TIMEOUT_SEC,
    logger=logger,
)
try:
    ctrl.emergency_stop_all()
    time.sleep(0.05)
    ctrl.remote()
    status = ctrl.get_status(MOTOR)

    if status is None:
        raise AssertionError("STS?応答を取得できません")
    if status.remote_local != "R":
        raise AssertionError(f"REMOTEへ移行していません: {status.raw!r}")
    if status.is_busy:
        raise AssertionError(f"motor {MOTOR} が停止していません")

    before = ctrl.get_position(MOTOR)

    # target = before + T1EST_PULSE
    # target = before + 10
    # target = before + 10

    # if target > 8388607:
    #     # target = before - TEST_PULSE
    #     target = before - 10
    target = 0
    # target = 100
    # target = 1000

    print(f"[INFO] {'move'}: {target}")
    ctrl.move(MOTOR, target, backlash=False)
    # time.sleep(10)
    status = ctrl.wait_for_complete(
        MOTOR,
        timeout_sec=MOTION_TIMEOUT_SEC,
        target_position=target,
    )
    if status is None:
        raise AssertionError("ABS移動が完了しませんでした")
    if ctrl.get_position(MOTOR) != target:
        raise AssertionError("ABS移動位置不一致")

    print(f"[PASS] {'move'}: {'OK'}")

finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
