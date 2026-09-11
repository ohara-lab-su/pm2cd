from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0

ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    cw = ctrl.get_limit(MOTOR, "cw")
    ccw = ctrl.get_limit(MOTOR, "ccw")

    ctrl.set_limit(MOTOR, "cw", cw)
    ctrl.set_limit(MOTOR, "ccw", ccw)
    if ctrl.get_limit(MOTOR, "cw") != cw or ctrl.get_limit(MOTOR, "ccw") != ccw:
        raise AssertionError("digital limit read-back不一致")
    print(f"[PASS] {'set_limit'}: {(cw, ccw)}")

finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
