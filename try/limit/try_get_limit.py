from pm2cd.pm2cd_ctrl import PM2CD
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
        value = ctrl.get_limit(0, "cw")
        print(f"[motor = 0, cw] get_limit: {value}")
        value = ctrl.get_limit(0, "ccw")
        print(f"[motor = 0, ccw] get_limit: {value}")
        value = ctrl.get_limit(1, "cw")
        print(f"[motor = 1, cw] get_limit: {value}")
        value = ctrl.get_limit(1, "ccw")
        print(f"[motor = 1, ccw] get_limit: {value}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
