# from pm2cd.pm2cd_ctrl import PM2CD
from pm2cd.pm2cd_single import PM2CDsingle as PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0


def main():
    logger = XLogger(log_level="DEBUG")
    ctrl = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )
    try:
        value = ctrl.get_hard_limit_enabled()
        print(f"[motor = {ctrl.motor}] get_hard_limit_enabled [CW, CCW]: {value}")
        ctrl.motor = 1
        value = ctrl.get_hard_limit_enabled()
        print(f"[motor = 1] get_hard_limit_enabled [CW, CCW]: {value}")

        ctrl.motor = 0

        value = ctrl.get_hard_limit_enabled(0)
        print(f"[motor = 0] get_hard_limit_enabled [CW, CCW]: {value}")

        value = ctrl.get_hard_limit_enabled(1)
        print(f"[motor = 1] get_hard_limit_enabled [CW, CCW]: {value}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
