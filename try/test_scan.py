import time
from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
SCAN_TIME_SEC = 0.2
MOTION_TIMEOUT_SEC = 30.0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
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
    ctrl.scan(MOTOR, 'cw')
    time.sleep(SCAN_TIME_SEC)
    ctrl.stop(MOTOR)
    ctrl.wait_stop(MOTOR, timeout_sec=MOTION_TIMEOUT_SEC)
    print(f"[PASS] {'scan'}: {'OK'}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
