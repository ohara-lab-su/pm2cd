from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0


def create_ctrl():
    logger = XLogger(log_level="DEBUG")
    return PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )


SIDE = "cw"
NORMALLY_CLOSED = True


def main():
    ctrl = create_ctrl()
    try:
        value = ctrl.set_hard_limit_normally_closed(
            MOTOR,
            SIDE,
            NORMALLY_CLOSED,
        )
        print(f"[PASS] set_hard_limit_normally_closed: {value}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
