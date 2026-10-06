from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0


ENABLED = True


def main():
    logger = XLogger(log_level="DEBUG")
    ctrl = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )
    try:
        ctrl.set_hard_limit_enabled(0, False)
        ctrl.set_hard_limit_enabled(1, False)
        motor1 = ctrl.get_hard_limit_enabled(0)
        motor2 = ctrl.get_hard_limit_enabled(1)
        logger.info(f"motor1: {motor1}")
        logger.info(f"motor2: {motor2}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
