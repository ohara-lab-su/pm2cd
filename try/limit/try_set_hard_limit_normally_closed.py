from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0


SIDE = "cw"
NORMALLY_CLOSED = True


def main():
    logger = XLogger(log_level="DEBUG")
    ctrl = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )
    try:
        value = ctrl.set_hard_limit_normally_closed(
            0,
            "cw",
            True,
        )
        motor1 = ctrl.get_hard_limit_normally_closed(0)
        motor2 = ctrl.get_hard_limit_normally_closed(1)
        logger.info(f"motor1: {motor1}")
        logger.info(f"motor2: {motor2}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
