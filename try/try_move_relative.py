import time

from pm2cd.pm2cd_ctrl import PM2CD

# from pm2cd.pm2cd_single import PM2CDsingle as PM2CD
from x_logger import XLogger


def check_status(status):
    if status is None:
        raise AssertionError("STS?応答を取得できません")
    if status.remote_local != "R":
        raise AssertionError(f"REMOTEへ移行していません: {status.raw!r}")
    if status.is_busy:
        raise AssertionError(f"motor {MOTOR} が停止していません")


IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
# MOTOR = 0
# TEST_PULSE = 10
MOTION_TIMEOUT_SEC = 30.0


def main():
    # logger = XLogger(log_level="DEBUG")
    logger = XLogger(log_level="INFO")
    # ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
    ctrl = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
        timeout_sec=TIMEOUT_SEC,
        logger=logger,
    )
    try:
        ctrl.emergency_stop_all()
        time.sleep(0.05)
        ctrl.remote()
        print(f"current = motor: {ctrl.motor}")
        status = ctrl.get_status()
        check_status(status)

        before = ctrl.get_position()

        TEST_PULSE = 1000

        ctrl.move_relative(TEST_PULSE, motor=0, backlash=False)
        # ctrl.wait_for_complete(motor=0, timeout_sec=MOTION_TIMEOUT_SEC)
        ctrl.wait_for_complete()
        if ctrl.get_position() != before + TEST_PULSE:
            raise AssertionError("REL移動位置不一致")

        ctrl.move_relative(-TEST_PULSE, backlash=False)
        # ctrl.wait_for_complete(timeout_sec=MOTION_TIMEOUT_SEC)
        ctrl.wait_for_complete()
        print(f"[PASS] {'move_relative'}: {'OK'}")
    finally:
        try:
            # ctrl.emergency_stop_all()
            ctrl.stop()
        finally:
            ctrl.close()


if __name__ == "__main__":
    main()
