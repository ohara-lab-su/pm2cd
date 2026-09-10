from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_home_position(MOTOR)
    if original is None:
        raise AssertionError('home_positionを取得できません')
    ctrl.set_home_position(MOTOR, original)
    actual = ctrl.get_home_position(MOTOR)
    if actual != original:
        raise AssertionError('home_position read-back不一致')
    print(f"[PASS] {'set_home_position'}: {actual}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
