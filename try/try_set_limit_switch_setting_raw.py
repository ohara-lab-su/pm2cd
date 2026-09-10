from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_limit_switch_setting(MOTOR)
    ctrl.set_limit_switch_setting_raw(MOTOR, original.raw)
    actual = ctrl.get_limit_switch_setting(MOTOR)
    if actual.raw != original.raw:
        raise AssertionError('SETLS read-back不一致')
    print(f"[PASS] {'set_limit_switch_setting_raw'}: {actual}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
