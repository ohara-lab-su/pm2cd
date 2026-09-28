import time

from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTION_TIMEOUT_SEC = 30.0
POLL_INTERVAL_SEC = 0.1
TARGET = 0


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
        ctrl.motor = 1

        print("[INFO] status:", ctrl.get_status())
        print("[INFO] position:", ctrl.get_position())
        print("[INFO] move:", TARGET)

        # この例はクライアント側で busy/position を直接追うため、
        # backlash の中間到達と最終到達を区別する必要がない条件に限定する。
        if not ctrl.move(TARGET, backlash=False):
            raise RuntimeError("move() に失敗しました")

        deadline = time.monotonic() + MOTION_TIMEOUT_SEC
        inactive_count = 0

        while True:
            status = ctrl.get_status()
            if status is None:
                raise RuntimeError("状態を取得できませんでした")

            print(status.position, flush=True)

            if status.is_busy:
                inactive_count = 0
            else:
                inactive_count += 1

            # 短距離移動で busy を取り逃しても即終了しないよう、
            # inactive を2回連続で確認し、最終位置も確認する。
            if inactive_count >= 2 and status.position == TARGET:
                break

            if time.monotonic() >= deadline:
                raise RuntimeError("移動完了待ちがタイムアウトしました")

            time.sleep(POLL_INTERVAL_SEC)

        print("[PASS] move: OK")

    finally:
        try:
            ctrl.stop()
        finally:
            ctrl.close()


if __name__ == "__main__":
    main()
