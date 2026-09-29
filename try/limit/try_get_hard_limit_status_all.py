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
        value = ctrl.get_hard_limit_status_all()
        print(f"[PASS] get_hard_limit_status_all [[CW, CCW, HP], ...]: {value}")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
