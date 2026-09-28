"""PM2CDsingle の move() -> wait_for_complete() を確認する。"""

from pm2cd.pm2cd_single import PM2CDsingle

IP_ADDRESS = "10.170.10.62"
MOTOR = 0
TARGET = 100


def main() -> None:
    ctrl = PM2CDsingle(IP_ADDRESS)
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
