import time

from pm2cd.server_fastapi.client_sync import SyncPM2CDClient
from x_logger import XLogger

SERVER_IP = "127.0.0.1"
SERVER_PORT = 8000
MOTOR = 0
MOTION_TIMEOUT_SEC = 30.0

logger = XLogger(log_level="DEBUG")
ctrl = SyncPM2CDClient(
    server_ip=SERVER_IP,
    server_port=SERVER_PORT,
    logger=logger,
)

try:
    ctrl.stop()
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

    target = 0

    print(f"[INFO] {'move'}: {target}")
    ctrl.move(MOTOR, target, backlash=False)
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
