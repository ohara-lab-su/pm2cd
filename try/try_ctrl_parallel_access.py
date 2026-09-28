"""ctrl の wait 中に別呼び出しから状態取得できることを確認する。"""

import threading
import time

from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
MOTOR = 0
TARGET = 1000


def main() -> None:
    ctrl = PM2CD(IP_ADDRESS, worker_count=2)
    wait_result = {}

    def wait_motion() -> None:
        wait_result["status"] = ctrl.wait_for_complete(show_position=False)

    try:
        ctrl.remote()
        ctrl.motor = MOTOR
        print("move:", ctrl.move(TARGET, backlash=True))

        thread = threading.Thread(target=wait_motion)
        thread.start()

        while thread.is_alive():
            print("position while waiting:", ctrl.get_position())
            time.sleep(0.1)

        thread.join()
        print("complete:", wait_result.get("status"))
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
