"""final 判定を使わず、公開状態 API を利用側から観測する。"""

import time

from pm2cd.pm2cd_single import PM2CDsingle

IP_ADDRESS = "10.170.10.62"
MOTOR = 0
TARGET = 100
INTERVAL_SEC = 0.1
POLL_COUNT = 50


def main() -> None:
    ctrl = PM2CDsingle(IP_ADDRESS)
    try:
        ctrl.remote()
        ctrl.motor = MOTOR
        print("move:", ctrl.move(TARGET, backlash=False))

        for _ in range(POLL_COUNT):
            status = ctrl.get_status()
            position = ctrl.get_position()
            busy = ctrl.is_busy()
            print("status=", status, "position=", position, "busy=", busy)
            time.sleep(INTERVAL_SEC)
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
