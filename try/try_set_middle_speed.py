from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_middle_speed(MOTOR)
    ctrl.set_middle_speed(MOTOR, original)
    actual = ctrl.get_middle_speed(MOTOR)
    if actual != original:
        raise AssertionError('MSPD read-back不一致')
    print(f"[PASS] {'set_middle_speed'}: {actual}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
