# Manual Reference

<a href="https://ohara-lab-su.github.io/pm2cd/en/manual/reference.html">English</a> | <a href="https://ohara-lab-su.github.io/pm2cd/ja/manual/reference.html">日本語</a>

## Public control classes

| Class | Role |
|---|---|
| `pm2cd.pm2cd_single.PM2CDsingle` | Single-process controller |
| `pm2cd.pm2cd_ctrl.PM2CD` | Multiprocess controller |
| `pm2cd.pm2cd_device.PM2CDDevice` | Device command layer |
| `pm2cd.core.communication_tcp.Communication` | TCP transport |

## Common operations

| API | Purpose |
|---|---|
| `get_position(motor)` | Read current position |
| `move(target, motor, backlash, relative)` | Absolute or relative motion |
| `move_relative(target, motor, backlash)` | Relative motion |
| `wait_for_complete(motor, timeout_sec, interval_sec, target_position, show_position)` | Wait for motion completion |
| `stop(motor)` / `emergency_stop(motor)` | Controlled / emergency stop |
| `get_status(motor)` / `get_status_all()` | Read motor status |
| `set_speed(motor, ...)` / `get_speed(motor)` | Set / read speed (see generated API for exact arguments) |
| `get_limit(motor, ...)` / `set_limit(motor, ...)` | Software limits (see generated API for exact arguments) |

Boolean results generally indicate success or failure. Read operations may return `None` on failure. Invalid arguments can raise exceptions.

## Motion signatures

```python
move(target: int, motor: Optional[int] = None, backlash: Union[str, bool, None] = True, relative: bool = False) -> bool
move_relative(target: int, motor: Optional[int] = None, backlash: Union[str, bool, None] = True) -> bool
```

## Implementation-defined limits

`PM2CDDevice` defines position limits of `-8388608` to `8388607`, speed limits of `5` to `100000` pps, backlash limits of `-9999` to `9999`, and hold times of `50` to `3000` ms. Refer to the implementation for method-specific validation.


> Before moving hardware, verify wiring, limit switches, travel direction, and permissible travel. The examples have not been run against a physical controller.
