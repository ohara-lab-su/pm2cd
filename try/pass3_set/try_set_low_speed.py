from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0

ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_low_speed(MOTOR)
    ctrl.set_low_speed(MOTOR, original)
    actual = ctrl.get_low_speed(MOTOR)

    if actual != original:
        raise AssertionError("LSPD read-back不一致")
    print(f"[PASS] {'set_low_speed'}: {actual}")

finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
