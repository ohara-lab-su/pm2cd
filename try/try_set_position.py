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
    # 現在のポジションを set_position する
    # ほぼ純粋に機能テスト
    original = ctrl.get_position(MOTOR)
    ctrl.set_position(MOTOR, original)

    actual = ctrl.get_position(MOTOR)
    if actual != original:
        raise AssertionError("PS read-back不一致")
    print(f"[PASS] {'set_position'}: {actual}")

    # 任意の座標をセットする
    # # ctrl.set_position(MOTOR, 100)
    # ctrl.set_position(MOTOR, 0)
    # actual = ctrl.get_position(MOTOR)
    # print(f"[PASS] {'set_position'}: {actual}")

finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
