from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_backlash(MOTOR)
    ctrl.set_backlash(MOTOR, original)
    actual = ctrl.get_backlash(MOTOR)
    if actual != original:
        raise AssertionError('backlash read-back不一致')
    print(f"[PASS] {'set_backlash'}: {actual}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
