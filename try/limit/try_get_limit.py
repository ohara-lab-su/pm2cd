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
        cw0 = ctrl.get_limit(0, "cw")
        ccw0 = ctrl.get_limit(0, "ccw")
        cw1 = ctrl.get_limit(1, "cw")
        ccw1 = ctrl.get_limit(1, "ccw")
        logger.info(f"[motor = 0, cw] get_limit: {cw0}")
        logger.info(f"[motor = 0, ccw] get_limit: {ccw0}")
        logger.info(f"[motor = 1, cw] get_limit: {cw1}")
        logger.info(f"[motor = 1, ccw] get_limit: {ccw1}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
