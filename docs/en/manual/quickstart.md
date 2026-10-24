# Quick Start

[English](../../en/manual/quickstart.html) | [日本語](../../ja/manual/quickstart.html)

`PM2CDsingle` provides a single-process interface; `PM2CD` uses `ProcessExecutor` with multiple worker processes. The device is fixed at two channels, numbered `0` and `1`. The default TCP port is `7777`, and the default timeout is `3.0` seconds.

The following example only connects and reads state. The `PM2CDsingle` constructor calls `connect()` internally.
```python
from pm2cd.pm2cd_single import PM2CDsingle

IP_ADDRESS: str = "192.0.2.10"  # Replace with the controller's address.

controller = PM2CDsingle(ip_address=IP_ADDRESS)
try:
    print(controller.get_version())
    print(controller.get_position(motor=0))
    print(controller.get_status(motor=0))
finally:
    controller.close()
```


> Before moving hardware, verify wiring, limit switches, travel direction, and permissible travel. The examples have not been run against a physical controller.
