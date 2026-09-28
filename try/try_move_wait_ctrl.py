"""ProcessExecutor を使用する PM2CD(ctrl) で final 完了待ちを確認する。"""

from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
MOTOR = 0
TARGET = 100


def main() -> None:
    ctrl = PM2CD(IP_ADDRESS, worker_count=2)
    try:
        ctrl.remote()
        ctrl.motor = MOTOR
        print("before:", ctrl.get_position())
        print("move:", ctrl.move(TARGET, backlash=True))
        status = ctrl.wait_for_complete(show_position=True)
        print("complete:", status)
        print("after:", ctrl.get_position())
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
