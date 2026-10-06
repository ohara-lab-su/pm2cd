import time

from pm2cd.pm2cd_ctrl import PM2CD

# from pm2cd.pm2cd_single import PM2CDsingle as PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTION_TIMEOUT_SEC = 30.0

###############
TARGET = 2000
# TARGET = 0
###############


def main():
    logger = XLogger(log_level="INFO")
    ctrl = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )

    try:
        ctrl.stop()
        time.sleep(0.05)
        ctrl.remote()
        ctrl.motor = 0
        # ctrl.motor = 1

        print("[INFO] status:", ctrl.get_status())
        print("[INFO] position:", ctrl.get_position())
        print("[INFO] move:", TARGET)

        if not ctrl.move(TARGET, backlash=True):
            raise RuntimeError("move() に失敗しました")

        # backlash を含む正しい完了判定は wait_for_complete() に任せる。
        # wait_for_complete() が内部で取得した現在位置を各ポーリングで表示する。
        status = ctrl.wait_for_complete(
            timeout_sec=MOTION_TIMEOUT_SEC,
            show_position=True,
        )
        if status is None:
            raise RuntimeError("移動が完了しませんでした")

        print("[PASS] move: OK")

    finally:
        try:
            ctrl.stop()
        finally:
            ctrl.close()


if __name__ == "__main__":
    main()
