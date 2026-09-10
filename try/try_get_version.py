from pm2cd.pm2cd_ctrl import PM2CD
IP_ADDRESS = '10.170.10.62'
PORT = 7777
TIMEOUT_SEC = 3.0
ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
try:
    value = ctrl.get_version()
    if value is None:
        raise AssertionError('VER?応答を取得できません')
    if not value.is_pm2cd:
        raise AssertionError(f'PM2CD系のVER?応答ではありません: {value.raw!r}')
    print(f"[PASS] {'get_version'}: {value.raw}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
