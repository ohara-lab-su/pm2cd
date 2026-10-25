# pm2cd

[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/ohara-lab-su/pm2cd/blob/main/README.md)
[![ja](https://img.shields.io/badge/lang-ja-yellow.svg)](https://github.com/ohara-lab-su/pm2cd/blob/main/README.ja.md)

[![GitHub](https://img.shields.io/badge/GitHub-ohara--lab--su%2Fpm2cd-181717?logo=github)](https://github.com/ohara-lab-su/pm2cd/)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Documentation-222222?logo=githubpages&logoColor=white)](https://ohara-lab-su.github.io/pm2cd/en/)
[![Ohara Lab](https://img.shields.io/badge/Ohara%20Lab-Home-4B5563?logo=homeassistant&logoColor=white)](https://ohara-lab-su.github.io/index.en.html)

A Python package for controlling PM2CD / PM2C-06A.

This package draws on the design principles and semantics of device operations in the existing C/MADOCA Device handlers.
The Python implementation separates communication, device-specific processing, data parsing, user-facing control,
multi-process execution, and FastAPI communication.

The current version is **v0.1.0**.

This README serves not merely as installation notes, but as a comprehensive manual, design specification, and tutorial
for the Python implementation of PM2CD.

------------------------------------------------------------------------

## 1. Scope

The target devices are PM2CD and PM2C-06A. PM16C-16 is a different device; its specifications must not be assumed to
apply to PM2CD. The C `dev_pm16c16_*` Device handlers nevertheless provide useful design precedents. The Python design
follows these principles: one meaningful device operation per handler; multi-command operations completed inside Device;
communication delegated to a common layer; compound response parsing delegated to core; and no exposure of raw bits,
nibbles, or command strings through Ctrl.

------------------------------------------------------------------------

## 2. Relationship Between the C/MADOCA and Python Implementations

The original C code implements Device handlers in the MADOCA environment. The Python implementation refers to command
generation, send/receive, command sequencing, response conversion, and handler granularity—not the entire MADOCA network
API. Reviewed handlers cover rotate/check_rotate, number/rate conversion, emergency stop, backlash, display, hold,
limit, pause, pulse, rate, speed, speed mode, status/status_all, SETLS, TTL, version, home, ALLREP, remote, stop, and
CRLF I/O. The Python version redistributes these responsibilities. For example, a handler that reads settings, changes
bits, sends a configuration command, and performs an operation remains one operation within `PM2CDDevice`. `set_limit()`
reads `SETLS?x`, parses `LimitSwitchSetting`, enables the software limit if necessary, writes `SETLSx...`, then issues
`FLx...` / `BLx...`. Users need not orchestrate these commands themselves. MADOCA and FastAPI / `ese774_frame` are
distinct frameworks: device logic is independent of network transport, and the Python DeviceClass works locally without
a server.

### 2.1 Role of the C Implementation

### 2.2 The Python Implementation Is Not a One-to-One Translation

``` text
C版/MADOCA
    Device handler
        |
        | 装置操作の意味・処理順序を参照
        v
Python
    PM2CDDevice
        + core parser
        + Communication
        + PM2CDsingle
        + PM2CD
```

``` text
SETLS?x
   |
   v
LimitSwitchSetting
   |
   +-- software limit が無効なら enable
   |
   v
SETLSx...
   |
   v
FLx... / BLx...
```

### 2.3 MADOCA and the Python Server Are Different Layers

``` text
装置制御ロジック
        !=
ネットワーク framework
```

------------------------------------------------------------------------

## 3. Overall Python Architecture

The following diagrams show the v0.1.0 architecture and the flow from raw responses through core parsers and frozen
dataclasses to the control and client layers.

``` text
利用プログラム
    |
    +-- local
    |      |
    |      +--> PM2CDsingle
    |      |
    |      `--> PM2CD
    |
    `-- network
           |
           +--> SyncPM2CDClient / AsyncPM2CDClient
           |
           v
       FastAPI / ese774_frame
           |
           v
         PM2CD
           |
           v
     ProcessExecutor
           |
           +--> PM2CDsingle worker 1
           +--> PM2CDsingle worker 2
           +--> ...
                    |
                    v
                PM2CDDevice
                    |
                    v
          shared Communication proxy
                    |
                    v
             Communication x 1
                    |
                    v
             TCP + CRLF
                    |
                    v
             PM2CD / PM2C-06A
```

``` text
raw response
    |
    v
core parser
    |
    v
frozen dataclass / Python value
    |
    v
PM2CDDevice
    |
    v
PM2CDsingle
    |
    v
PM2CD / client
```

------------------------------------------------------------------------

## 4. Responsibilities of Each Layer

`Communication` manages only TCP connect/disconnect, CRLF termination, send/receive/query, timeouts and socket errors,
and the receive buffer. It does not interpret device commands. `query()` locks the combined send/receive operation so
replies remain associated with requests. `core` parses compound responses into immutable dataclasses such as
`MotorStatus`, `ControllerStatus`, `HomeStatus`, `LimitStatus`, `MotorSetting`, `LimitSwitchSetting`, and `StopMode`.
Parsing and data storage remain separate; an unparseable response generally causes a retrieval API to return `None`.
`PM2CDDevice` implements the device-specific handlers: commands, input validation, communication, multi-command
sequences, parsing, and conversion into Python values. It must not be reduced to a trivial send/query wrapper.
`PM2CDsingle` provides a single-process, user-facing control API, default motor selection, movement context,
`wait_for_complete()`, and backlash-aware completion checks. It accepts an injected `Communication` instance, including
for sharing one physical connection across workers. `PM2CD` is the v0.1.0 multi-process facade, dispatching compatible
operations through `ProcessExecutor.submit()` and `wait()`. Calls appear synchronous to the user although handlers
execute in worker processes.

### 4.1 `Communication`

### 4.2 `core`

``` text
raw response
    |
    v
parse_xxx()
    |
    v
@dataclass(frozen=True)
```

### 4.3 `PM2CDDevice`

### 4.4 `PM2CDsingle`

``` python
ctrl = PM2CDsingle(
    ip_address=IP_ADDRESS,
    communication=communication,
)
```

### 4.5 `PM2CD`

``` text
PM2CD.method(...)
    |
    v
ProcessExecutor.submit(...)
    |
    v
PM2CDsingle.method(...)
    |
    v
ProcessExecutor.wait(...)
    |
    v
return value
```

------------------------------------------------------------------------

## 5. Choosing Between `PM2CDsingle` and `PM2CD`

Use `PM2CDsingle` for direct control in one Python process. Use `PM2CD` for the normal multi-process configuration.
`worker_count` is the number of worker processes managed by `ProcessExecutor`.

### 5.1 `PM2CDsingle`

``` python
from pm2cd.pm2cd_single import PM2CDsingle

ctrl = PM2CDsingle(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
)

try:
    ctrl.remote()
    position = ctrl.get_position(0)
    print(position)
finally:
    ctrl.close()
```

``` text
application
    |
    v
PM2CDsingle
    |
    v
PM2CDDevice
    |
    v
Communication
    |
    v
PM2CD
```

### 5.2 `PM2CD`

``` python
from pm2cd.pm2cd_ctrl import PM2CD

ctrl = PM2CD(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
    worker_count=2,
)

try:
    ctrl.remote()
    position = ctrl.get_position(0)
    print(position)
finally:
    ctrl.close()
```

------------------------------------------------------------------------

## 6. Why There Is Only One Communication Instance with Multiple Workers

If every worker constructs its own `PM2CDsingle` and `Communication`, its locks are independent and cannot ensure
ordering across the entire device. In v0.1.0, a `BaseManager` owns exactly one `Communication` and supplies proxies to
all workers. There are N worker processes and N `PM2CDsingle` instances, but only one `Communication` and one TCP
connection. This sharing is explicitly designed and owned by PM2CD; `ProcessExecutor` does not provide it automatically.

### 6.1 Incorrect Architecture

``` text
worker 1 -> Communication 1 --+
worker 2 -> Communication 2 --+--> same PM2CD
worker 3 -> Communication 3 --+
```

### 6.2 Architecture in v0.1.0

``` text
worker 1 --+
worker 2 --+--> Communication proxy --> Communication x 1 --> PM2CD
worker N --+
```

``` text
worker process      N
PM2CDsingle         N
Communication       1
TCP connection      1
```

------------------------------------------------------------------------

## 7. Relationship with `ProcessExecutor`

`ProcessExecutor` is a general-purpose framework, not a PM2CD-specific one. PM2CD uses worker creation,
`worker_factory(context)`, dispatch, `submit()`, `wait()`, `SharedContext`, manager-backed state, and process-safe
locks. The executor manages processes, jobs, and shared context without understanding the PM2CD protocol. PM2CD creates
worker-local `PM2CDsingle` objects, owns the single shared `Communication`, and places controller state in
`SharedContext`. Each worker receives the common communication proxy and `SharedContext.state`. Because ordinary
instance variables are process-local, the default motor and movement context must be shared.

``` text
ProcessExecutor
    |
    +-- process を管理する
    +-- job を dispatch する
    +-- shared context を提供する
    |
    `-- PM2CD protocol は知らない

PM2CD
    |
    +-- PM2CDsingle を worker として構成する
    +-- Communication を一つだけ所有する
    +-- controller state を SharedContext へ置く
    |
    `-- PM2CD 固有の resource ownership を決める
```

### 7.1 `worker_factory(context)`

### 7.2 Shared State

------------------------------------------------------------------------

## 8. Movement Context and `wait_for_complete()`

`move()` and `move_relative()` store each motor’s last movement conditions for completion checks: target position,
backlash request, whether backlash is enabled, and backlash value. Without backlash, completion normally means reaching
the target while inactive; the active state need not have been observed, because short moves can occur between polls.
With backlash, the motion can pass through a backlash point and return to the target, so the first inactive observation
at the target is not necessarily final completion. `wait_for_complete()` uses the stored movement context to detect the
final return and accommodates active/inactive transitions missed between polls. Because one worker may run `move()` and
another `wait_for_complete()`, v0.1.0 stores movement context in `SharedContext.state` to preserve semantics
independently of scheduling.

### 8.1 Without Backlash

``` text
move
  |
  v
active
  |
  v
target position + inactive
  |
  v
complete
```

### 8.2 With Backlash

``` text
target
  |
  v
backlash point
  |
  v
target
```

### 8.3 Sharing Across Processes

``` text
worker 1: move()
       |
       v
SharedContext.state
       |
       v
worker 2: wait_for_complete()
```

------------------------------------------------------------------------

## 9. The `motor` Property

Both `PM2CDsingle` and `PM2CD` expose a default motor through the `motor` property. An explicitly supplied motor takes
precedence. In multi-process mode the default is shared across workers.

``` python
ctrl.motor = 0
position = ctrl.get_position()
```

``` python
position = ctrl.get_position(1)
```

------------------------------------------------------------------------

## 10. FastAPI / `ese774_frame`

PM2CD uses fully automatic dispatch in `ese774_frame`, with `FastApiServer`, `api_spec=None`, and `object_name="pm2cd"`.
Public methods and type annotations generate the API without manually listing Pydantic models or `ApiSpec` objects.
Status APIs return frozen dataclasses (`MotorStatus`, `ControllerStatus`, `HomeStatus`, `LimitStatus`, `MotorSetting`,
`LimitSwitchSetting`, and `StopMode`). **`ese774_frame >= 0.6.0`** is required to serialize these as JSON and
reconstruct the original types on the client. Both `SyncPM2CDClient` and `AsyncPM2CDClient` use the matching object
name.

``` text
FastApiServer
api_spec=None
object_name="pm2cd"
```

### 10.1 Transferring Dataclasses

### 10.2 Clients

``` text
SyncPM2CDClient
AsyncPM2CDClient
```

------------------------------------------------------------------------

## 11. Starting the Server

The server module accepts a worker count, passed from `run()` through `create_server()` and
`FastApiServer(device_kwargs)` into `PM2CD(worker_count=...)`. The number of server processes is distinct from the
number of internal `ProcessExecutor` workers. The startup example specifies the worker count directly in code, not
through CLI arguments.

### 11.1 Server Module

``` python
from pm2cd.server import run

run(
    worker_count=2,
)
```

``` text
run(worker_count)
    |
    v
create_server(worker_count)
    |
    v
FastApiServer(device_kwargs)
    |
    v
PM2CD(worker_count=worker_count)
```

### 11.2 Example Server

``` python
from pm2cd.server import run

WORKER_COUNT = 2


def main() -> None:
    run(
        worker_count=WORKER_COUNT,
    )


if __name__ == "__main__":
    main()
```

------------------------------------------------------------------------

## 12. Basic Tutorial

The following examples use `PM2CD`. Connect and close it using `try/finally`; switch to REMOTE with `remote()` and back
to LOCAL with `local()`; read individual or all-axis status; retrieve positions using an explicit or default motor; move
to an absolute position, optionally with backlash; wait for completion; move relatively; and distinguish normal stops
from emergency stops. Because movement context is shared, `move()` and `wait_for_complete()` retain backlash semantics
even when dispatched to different workers.

### 12.1 Connecting and Closing

``` python
from pm2cd.pm2cd_ctrl import PM2CD

ctrl = PM2CD(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
    worker_count=2,
)

try:
    print(ctrl.is_connected())
finally:
    ctrl.close()
```

### 12.2 Switching to REMOTE

``` python
ctrl.remote()
```

``` python
ctrl.local()
```

### 12.3 Reading Status

``` python
status = ctrl.get_status(0)

if status is not None:
    print(status.position)
    print(status.is_busy)
```

``` python
statuses = ctrl.get_status_all()
```

### 12.4 Reading the Current Position

``` python
position = ctrl.get_position(0)
print(position)
```

``` python
ctrl.motor = 0
position = ctrl.get_position()
```

### 12.5 Absolute Movement

``` python
ctrl.move(
    0,
    1000,
    backlash=False,
)

status = ctrl.wait_for_complete(
    0,
    timeout_sec=30.0,
)
```

### 12.6 Positioning with Backlash

``` python
ctrl.move(
    0,
    1000,
    backlash=True,
)

status = ctrl.wait_for_complete(
    0,
    timeout_sec=30.0,
)
```

### 12.7 Relative Movement

``` python
ctrl.move_relative(
    0,
    100,
    backlash=True,
)

ctrl.wait_for_complete(
    0,
    timeout_sec=30.0,
)
```

### 12.8 Normal and Emergency Stops

``` python
ctrl.stop(0)
ctrl.stop_all()
```

``` python
ctrl.emergency_stop(0)
ctrl.emergency_stop_all()
```

------------------------------------------------------------------------

## 13. Speed, Rate, and Backlash

The API supports current speed, speed profiles (LOW / MIDDLE / HIGH), individual speed settings, rate numbers, rate
values, conversions between rate and number, and backlash retrieval and configuration.

### 13.1 Speed

``` python
speed = ctrl.get_speed(0)
ctrl.set_speed(0, 1000)
```

``` python
profile = ctrl.get_speed_profile(0)
```

``` text
get_high_speed / set_high_speed
get_middle_speed / set_middle_speed
get_low_speed / set_low_speed
```

### 13.2 Rate

``` python
number = ctrl.get_rate_number(0)
ctrl.set_rate_number(0, number)
```

``` python
rate = ctrl.get_rate(0)
ctrl.set_rate(0, rate)
```

``` python
rate = ctrl.number_to_rate(number)
number = ctrl.rate_to_number(rate)
```

### 13.3 Backlash

``` python
backlash = ctrl.get_backlash(0)
ctrl.set_backlash(0, backlash)
```

------------------------------------------------------------------------

## 14. Limits

An unqualified `limit` in the Python API means a software limit; hardware limits explicitly use `hard_`. Software limit
positions can be read and set for CW and CCW. Software limit status is ordered `[CW, CCW]`; hardware limit status is
`[CW, CCW, HP]`. Both software/digital and hardware limit enable states are available. Hardware limit
normally-closed/open configuration is provided through typed methods; callers do not manipulate raw `DYYY0yyy` strings.

### 14.1 Software Limit Positions

``` python
cw = ctrl.get_limit(0, "cw")
ccw = ctrl.get_limit(0, "ccw")

ctrl.set_limit(0, "cw", 10000)
ctrl.set_limit(0, "ccw", -10000)
```

### 14.2 Software Limit Status

``` python
status = ctrl.get_limit_status(0)
```

``` text
[CW, CCW]
```

### 14.3 Hardware Limit Status

``` python
status = ctrl.get_hard_limit_status(0)
```

``` text
[CW, CCW, HP]
```

### 14.4 Enable Settings

``` python
enabled = ctrl.get_limit_enabled(0)
ctrl.set_limit_enabled(0, True)
```

``` python
enabled = ctrl.get_hard_limit_enabled(0)
ctrl.set_hard_limit_enabled(0, True)
```

### 14.5 Normally Closed / Open

``` python
setting = ctrl.get_hard_limit_normally_closed(0)

ctrl.set_hard_limit_normally_closed(
    0,
    "cw",
    True,
)
```

------------------------------------------------------------------------

## 15. HOME / HOLD / PAUSE

The following public methods cover home operations, presets, jog pulses, HOLD settings, and PAUSE operations.

``` text
home
find_home
scan_home
get_home_status
set_home_status
get_home_position
set_home_position
get_home_offset
set_home_offset
```

``` text
get_preset_position
set_preset_position
get_jog_pulse
set_jog_pulse
```

``` text
get_hold
set_hold
get_hold_on_time
set_hold_on_time
get_hold_off_time
set_hold_off_time
```

``` text
pause
resume
get_pause_status
```

------------------------------------------------------------------------

## 16. Motor / Stop Settings

Motor settings and stop modes are accessed through the methods below. Retrieved settings are represented as dataclasses.

``` text
get_motor_setting
set_motor_setting
```

``` text
get_stop_mode
set_stop_mode
```

------------------------------------------------------------------------

## 17. Main Public APIs

The following lists summarize the main public API, grouped by purpose.

``` text
motor
is_connected
connect
disconnect
remote
local
close
```

``` text
version
get_version
get_hardware_version
get_controller_status
controller_status
```

``` text
move
move_relative
scan
constant_speed_scan
jog
scan_home
home
find_home
stop
stop_all
emergency_stop
emergency_stop_all
get_rotate
is_busy
wait_for_complete
```

``` text
get_status
get_status_all
status_all
get_position
set_position
zero_position
```

``` text
get_speed
set_speed
get_speed_profile
set_speed_profile
get_high_speed
set_high_speed
get_middle_speed
set_middle_speed
get_low_speed
set_low_speed
get_speed_mode
set_speed_mode
get_rate_number
set_rate_number
get_rate
set_rate
number_to_rate
rate_to_number
get_backlash
set_backlash
```

``` text
get_limit
set_limit
get_limit_status
get_limit_status_all
get_hard_limit_status
get_hard_limit_status_all
get_limit_enabled
set_limit_enabled
get_hard_limit_enabled
set_hard_limit_enabled
get_hard_limit_normally_closed
set_hard_limit_normally_closed
get_limit_switch_setting
```

``` text
pause
resume
get_pause_status
get_hold
set_hold
get_hold_on_time
set_hold_on_time
get_hold_off_time
set_hold_off_time
```

``` text
get_home_status
set_home_status
get_home_position
set_home_position
get_home_offset
set_home_offset
get_preset_position
set_preset_position
get_jog_pulse
set_jog_pulse
```

``` text
get_motor_setting
set_motor_setting
get_stop_mode
set_stop_mode
```

------------------------------------------------------------------------

## 18. Return Value Conventions

Operations generally return `bool` for success/failure; retrieval methods return a value on success and `None` on
failure. Some retrieval methods are annotated `Optional[...]`. Status and settings are frozen dataclasses and should not
be mutated after retrieval.

``` text
操作成功/失敗    bool
値取得成功       値
値取得失敗       None
```

------------------------------------------------------------------------

## 19. Errors and Input Validation

`PM2CDDevice` validates inputs wherever possible to avoid sending invalid values to the device. Communication errors
belong to the communication layer; response parsing failures belong to parser/Device. Ctrl does not expose raw protocol
error representations as its primary public interface.

------------------------------------------------------------------------

## 20. Server/Client Architecture

Network access uses synchronous or asynchronous clients, HTTP/FastAPI, `ese774_frame` `FastApiServer`, `PM2CD`,
`ProcessExecutor`, worker-local `PM2CDsingle`, and the shared `Communication`. Increasing the worker count must not
create additional TCP connections to the device.

``` text
client application
      |
      v
SyncPM2CDClient
or AsyncPM2CDClient
      |
      v
HTTP / FastAPI
      |
      v
ese774_frame FastApiServer
      |
      v
PM2CD
      |
      v
ProcessExecutor
      |
      v
PM2CDsingle worker x N
      |
      v
shared Communication
      |
      v
PM2CD
```

------------------------------------------------------------------------

## 21. Purpose of the Examples

Examples are organized for incremental verification. Single local mode tests `PM2CDsingle`, the device protocol, Device,
and Ctrl without a framework. Multi local mode tests `PM2CD` with `ProcessExecutor`, real worker control, and a single
Communication even with two or more workers. FastAPI examples test fully automatic `ese774_frame` dispatch, dataclass
transfer, and the same public API over the network. The server example specifies `WORKER_COUNT` as a constant; it does
not accept a CLI worker-count option.

### 21.1 Single-Process Local

### 21.2 Multi-Process Local

### 21.3 FastAPI Server/Client

### 21.4 Server Startup Example

``` python
WORKER_COUNT = 2
```

------------------------------------------------------------------------

## 22. Recommended Verification Sequence

Test in the order shown below, adding one layer at a time: `Communication`, `PM2CDDevice`, local `PM2CDsingle`, local
multi-process `PM2CD`, FastAPI server, and sync/async clients. This avoids conflating multi-process failures with
network framework failures. Validate each new motion method at a small scale before moving upward.

``` text
1. Communication
       |
2. PM2CDDevice
       |
3. PM2CDsingle local
       |
4. PM2CD multi local
       |
5. FastAPI server
       |
6. Sync/Async client
```

------------------------------------------------------------------------

## 23. `close()` and Resource Ownership

In multi-process mode, all workers share one `Communication` resource. No individual worker should call
`PM2CDsingle.close()`. `PM2CD.close()` first closes `ProcessExecutor`, then the shared `Communication`, then shuts down
`CommunicationManager`. The creator and owner of a physical resource closes it exactly once, after its users have
stopped.

``` text
ProcessExecutor.close()
        |
        v
shared Communication.close()
        |
        v
CommunicationManager.shutdown()
```

------------------------------------------------------------------------

## 24. Important Design Principles

Keep Ctrl and Device separate: device-specific command strings belong in Device, not Ctrl. Do not make Device so thin
that meaningful multi-command operations escape into Ctrl. Core dataclasses represent data; parser functions perform
parsing. Keep device-specific sockets and protocols out of the general-purpose `ProcessExecutor`; PM2CD decides how
communication is shared. Do not expose implementation-specific methods such as `get_shared_xxx()` in the public API:
shared state is internal.

### 24.1 Keep Ctrl and Device Separate

### 24.2 Do Not Make Device Too Thin

### 24.3 Keep Processing Out of Core Dataclasses

### 24.4 Keep Device-Specific Logic Out of ProcessExecutor

### 24.5 Do Not Expose Shared State as a Public API

------------------------------------------------------------------------

## 25. Dependencies

Fully automatic FastAPI dispatch requires `ese774_frame >= 0.6.0`. Multi-process PM2CD uses `worker_factory`,
`SharedContext`, `shared_context`, `submit`, and `wait` from `ProcessExecutor`. The executor remains free of
PM2CD-specific code.

``` text
ese774_frame >= 0.6.0
```

``` text
worker_factory
SharedContext
shared_context
submit
wait
```

------------------------------------------------------------------------

## 26. Role of v0.1.0

The v0.0.x series established C Device handler semantics, separation of Communication/core/Device/Ctrl, expanded
`PM2CDsingle` APIs, backlash-aware `wait_for_complete()`, frozen dataclasses and parsers, and fully automatic FastAPI
dispatch. Version 0.1.0 builds a practical multi-process `PM2CD` facade without breaking single-process logic. Its key
structure is N `PM2CDsingle` workers, one `SharedContext`, one `Communication`, and one TCP connection. Single-process
control, multi-process control, and FastAPI server/client therefore share the same Device/Ctrl architecture.

``` text
PM2CDsingle worker x N
        +
SharedContext
        +
Communication x 1
        +
TCP connection x 1
```

------------------------------------------------------------------------

