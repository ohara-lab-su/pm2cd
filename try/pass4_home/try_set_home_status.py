from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_home_status(MOTOR)
    ctrl.set_home_status(MOTOR, original.found, original.found_direction, original.auto_start_direction)
    actual = ctrl.get_home_status(MOTOR)
    print(f"[PASS] {'set_home_status'}: {actual}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
