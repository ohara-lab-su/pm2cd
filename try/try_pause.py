from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    original = ctrl.get_pause_status()
    try:
        ctrl.pause()
        if ctrl.get_pause_status() != 'ON':
            raise AssertionError('PAUSE ONに失敗しました')
        print(f"[PASS] {'pause'}: {'ON'}")
    finally:
        if original == 'OFF':
            ctrl.resume()
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
