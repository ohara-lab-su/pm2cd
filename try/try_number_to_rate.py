from pm2cd.pm2cd_ctrl import PM2CD
from x_logger import XLogger

IP_ADDRESS = "10.170.10.62"
PORT = 7777
TIMEOUT_SEC = 3.0
MOTOR = 0

# 加減速

logger = XLogger(log_level="DEBUG")
# ctrl = PM2CD(ip_address=IP_ADDRESS, port=PORT, timeout_sec=TIMEOUT_SEC)
ctrl = PM2CD(
    ip_address=IP_ADDRESS,
    port=PORT,
    timeout_sec=TIMEOUT_SEC,
    logger=logger,
)
try:
    number = ctrl.get_rate_number(MOTOR)
    value = ctrl.number_to_rate(number)
    print(f"[PASS] {'number_to_rate'}: {value}")
finally:
    try:
        ctrl.emergency_stop_all()
    finally:
        ctrl.close()
