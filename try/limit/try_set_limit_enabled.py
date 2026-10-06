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
        value = ctrl.set_limit_enabled(0, False)
        print(f"[PASS] set_limit_enabled: {value}")

        value = ctrl.set_limit_enabled(MOTOR, False)
        print(f"[PASS] set_limit_enabled: {value}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
