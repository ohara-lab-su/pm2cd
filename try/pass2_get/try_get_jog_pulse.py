from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0

ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    value = ctrl.get_jog_pulse(MOTOR)
    print(f"[PASS] {'get_jog_pulse'}: {value}")

finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
