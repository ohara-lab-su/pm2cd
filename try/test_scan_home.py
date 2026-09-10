import time
from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
MOTION_TIMEOUT_SEC = 30.0
ENABLE_HOME_TESTS = False
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    if not ENABLE_HOME_TESTS:
        print(f"[PASS] {'scan_home'}: {'SKIP'}")
    else:
        ctrl.emergency_stop_all()
        time.sleep(0.05)
        ctrl.remote()
        status = ctrl.get_status(MOTOR)
        if status is None:
            raise AssertionError('STS?応答を取得できません')
        if status.remote_local != 'R':
            raise AssertionError(f'REMOTEへ移行していません: {status.raw!r}')
        if status.is_busy:
            raise AssertionError(f'motor {MOTOR} が停止していません')
        ctrl.scan_home(MOTOR, 'cw')
        ctrl.wait_stop(MOTOR, timeout_sec=MOTION_TIMEOUT_SEC)
        print(f"[PASS] {'scan_home'}: {'OK'}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
