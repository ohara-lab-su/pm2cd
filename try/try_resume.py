from pm2cd.pm2cd_ctrl import PM2CD

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0

ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_pause_status()
    try:
        ctrl.resume()
        if ctrl.get_pause_status() != "OFF":
            raise AssertionError("PAUSE OFFに失敗しました")
        print(f"[PASS] {'resume'}: {'OFF'}")
    finally:
        if original == "ON":
            ctrl.pause()
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
