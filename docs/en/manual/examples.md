# Examples

[English](../../en/manual/examples.html) | [日本語](../../ja/manual/examples.html)

## Read-only status query

`PM2CDsingle` attempts a connection during construction. Call `close()` to release resources.

## Motion and completion

Use the following example **only after validating the hardware and permissible travel range**. Provide an independent emergency-stop mechanism.
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
```python
from pm2cd.pm2cd_single import PM2CDsingle

IP_ADDRESS: str = "192.0.2.10"  # Replace with the controller's address.
TARGET_PULSES: int = 100

controller = PM2CDsingle(ip_address=IP_ADDRESS)
try:
    if controller.move(target=TARGET_PULSES, motor=0):
        status = controller.wait_for_complete(motor=0, timeout_sec=30.0)
        print(status)
finally:
    controller.close()
```


> Before moving hardware, verify wiring, limit switches, travel direction, and permissible travel. The examples have not been run against a physical controller.
