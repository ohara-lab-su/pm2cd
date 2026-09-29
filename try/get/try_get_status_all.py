from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0


def main():
    logger = XLogger(log_level="DEBUG")
    # ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
    ctrl = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )
    try:
        values = ctrl.get_status_all()
        if len(values) != 2:
            raise AssertionError("status_allの軸数が2ではありません")
        print(f"[PASS] {'get_status_all'}: {values}")
    finally:
        try:
            # ctrl.emergency_stop_all()
            ctrl.stop()
        finally:
            ctrl.close()


if __name__ == "__main__":
    main()
