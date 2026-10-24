# CHANGELOG

## v0.1.0 --- 2026-09-14

`PM2CDsingle`, as implemented through v0.0.3, remains the actual controller class for use in a single process. The user-facing `PM2CD` class has been restructured as a multiprocess facade built on `ProcessExecutor`.

The principal change is a revision of the previous multiprocessing implementation, which assumed `worker_count=1`, to **support multiple worker processes while retaining a single physical `Communication` instance and TCP connection**.

### Changed

#### Support multiple workers in `PM2CD`

Added `worker_count` to the `PM2CD` constructor.

```python
ctrl = PM2CD(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
    worker_count=2,
)
```

Removed the fixed `worker_count=1` restriction, allowing two or more worker processes.

`PM2CDsingle` remains the actual controller class instantiated within each worker process. `PM2CD` acts as a facade that dispatches its public API calls to workers.

#### Consolidate physical communication into one instance

If each worker independently creates a `PM2CDsingle`, each worker would otherwise also create a separate `Communication` instance and TCP connection.

Because PM2CD must preserve request/response ordering when communicating with one physical device, this arrangement was not adopted.

In v0.1.0, a single `Communication` instance is created on the `BaseManager` side, and its proxy is injected into the constructor of every `PM2CDsingle` worker.

```text
PM2CD
  |
  +-- ProcessExecutor
  |     |
  |     +-- PM2CDsingle worker 1 --+
  |     +-- PM2CDsingle worker 2 --+--> Communication proxy
  |     +-- PM2CDsingle worker N --+
  |
  +-- CommunicationManager
          |
          +-- Communication x 1
                    |
                    +-- TCP connection x 1
                            |
                            +-- PM2CD / PM2C-06A
```

The resulting architecture has:

- Multiple controller workers.
- One `PM2CDsingle` instance per worker.
- One physical `Communication` instance.
- One TCP connection.

Because the send/receive lock in `Communication.query()` is also consolidated into that single `Communication` instance, requests from multiple workers can be serialized over one physical communication path.

#### Share controller state across workers

Controller state held by `PM2CDsingle` that must persist across worker boundaries was moved to the `SharedContext` provided by `ProcessExecutor`.

This mainly includes:

- The currently selected `motor`.
- Movement context passed from `move()` / `move_relative()` to `wait_for_complete()`:
  - Target position.
  - Backlash specification.
  - Whether backlash compensation is enabled.
  - Backlash value.

`PM2CDsingle` is created through `worker_factory(context)`, and `SharedContext.state` is used as movement context shared between workers.

Consequently, even when worker 1 processes `move()` and worker 2 processes the subsequent `wait_for_complete()`, the preceding movement conditions, including backlash compensation, are preserved.

Shared state is an implementation detail; no separate shared-state API was added for users.

#### Preserve the public API

Rather than introducing a separate user API for multiprocessing, the public API established in `PM2CDsingle` is retained in `PM2CD`.

Existing APIs for the `motor` property, movement, status retrieval, speed, rate, backlash, limits, HOME, HOLD, and stop modes retain their meaning from the caller's perspective.

Internally, `PM2CD` dispatches these calls to worker processes using `ProcessExecutor.submit()` and `wait()`.

#### Change the shutdown order in `close()`

Calling `close()` on the shared `Communication` from one worker would also terminate the communication channel used by the other workers.

Accordingly, `PM2CD.close()` in v0.1.0 does not dispatch a `close` handler to workers. Shutdown now proceeds in this order:

1. Shut down `ProcessExecutor`.
2. Close the shared `Communication` once, on the owner side.
3. Shut down `CommunicationManager`.

### Server

Updated the PM2CD FastAPI server startup module to support `worker_count`.

```python
create_server(worker_count=...)
run(worker_count=...)
```

The worker count is passed through `FastApiServer`'s `device_kwargs` to `PM2CD(worker_count=...)`.

Starting the server process itself and specifying the number of worker processes within PM2CD are treated as separate concerns.

The example server startup script does not use CLI options. Instead, it sets a variable in the code:

```python
WORKER_COUNT = 2
```

and starts the server with:

```python
run(worker_count=WORKER_COUNT)
```

### Architecture

The main responsibilities in the Python PM2CD implementation as of v0.1.0 are separated as follows:

```text
PM2CD
    Public interface / multiprocess facade
        |
        v
ProcessExecutor
    Worker dispatch / SharedContext
        |
        +--> PM2CDsingle worker x N
                 |
                 v
             PM2CDDevice
                 |
                 v
       Shared Communication proxy
                 |
                 v
          Communication x 1
                 |
                 v
        TCP + CRLF / PM2C-06A
```

`ProcessExecutor` is unaware of the PM2CD protocol or TCP communication. Ownership and injection of the single `Communication` instance are implemented as PM2CD responsibilities.

### Compatibility

- `PM2CDsingle` remains available as the actual controller class for direct use in a single process.
- The responsibilities of `PM2CDDevice` for device-command construction and response parsing are unchanged.
- The semantics and processing granularity of device handlers derived from the C implementation/MADOCA are preserved.
- Frozen dataclasses and the separation of parsers introduced in v0.0.3 are retained.
- Fully automatic FastAPI dispatch continues to require `ese774_frame v0.6.0` or later.
- Multiprocess execution uses `process_executor` with `worker_factory`, `SharedContext`, and `shared_context` support.

### Validation

The following were checked during implementation:

- Python syntax of `pm2cd_ctrl.py`.
- Consistency of the public APIs of `PM2CDsingle` and `PM2CD`.
- Propagation of the constructor's `worker_count` to `ProcessExecutor`, rather than use of a fixed value.
- Injection of the same `Communication` proxy into all workers.
- Use of `SharedContext.state` by `_move_context`.
- Use of shared state by `motor`.
- Confirmation that `close()` does not close the shared `Communication` from a worker.
- Propagation of `worker_count` from the server startup module to `PM2CD`.
- Absence of CLI options in the example server.

## v0.0.3 - 2026-09-14

Since v0.0.2, the entire PM2CD control implementation has been reviewed and reorganized from a simple device-command wrapper into separate layers for high-level control, device-specific operations, and communication.

This release particularly revises the classes that return state and configuration values. Their design now supports direct transfer between server and client through the fully automatic dispatch mechanism of `ese774_frame v0.6.0`.

### Framework dependency

**ese774_frame v0.6.0 or later is required** when using fully automatic FastAPI dispatch.

PM2CD uses fully automatic dispatch with `api_spec=None`. Because state and configuration return values use dataclasses, the framework must obtain type information from return annotations, serialize dataclasses to JSON, and reconstruct the original types on the client side.

This capability was added in `ese774_frame v0.6.0`.

With earlier framework versions, returning a custom class such as `MotorStatus` produced:

`Object of type MotorStatus is not JSON serializable`

Consequently, state objects could not be transferred through fully automatic dispatch.

`ese774_frame v0.6.0` removes this limitation and automatically transfers and reconstructs return types such as `Optional[MotorStatus]` and `Optional[List[MotorStatus]]` based on method annotations.

Multiple PM2CD APIs have been tested with fully automatic dispatch using `ese774_frame v0.6.0`.

### Changed

#### Separation of control-layer responsibilities

PM2CD control is organized primarily into the following layers:

- `PM2CDsingle`
    - High-level control interface exposed to users.
    - Manages the default motor, waiting, state decisions, and other higher-level control operations.
- `PM2CDDevice`
    - Generates PM2CD / PMXC-06A-specific commands, retrieves responses, and validates values.
- `Communication`
    - Handles TCP connections, transmission, and reception.
- `core`
    - Contains data types for device state and settings, and response-parsing logic.

This separates device communication, device-specific protocol handling, and the public control interface.

#### Public interface cleanup

`PM2CDsingle` is organized as the public control interface.

- Added a `motor` property and APIs that allow the motor number to be omitted.
- Organized `connect()` / `disconnect()` / `close()` / `is_connected()`.
- Added context-manager support (`__enter__` / `__exit__`).
- Organized read/write APIs around `get_xxx()` / `set_xxx()`.
- Explicitly validates `channel_count=2` at the public layer as a PM2CD-specific constraint.

#### Return values and error handling

In v0.0.2, many operations issued device commands directly and either raised exceptions on failure or returned no value.

The device-control API now generally follows these return-value conventions:

- Operation succeeds/fails: `bool`
- Value retrieval succeeds: the retrieved value
- Value retrieval fails: `None`

Many retrieval APIs therefore use `Optional[...]` return annotations.

Input values are also validated by `PM2CDDevice` so invalid values are not sent to the device.

### Added

#### State retrieval and state evaluation

State-related functionality was substantially expanded:

- Controller state retrieval
- Motor state retrieval
- All-motor state retrieval
- Rotation state retrieval
- BUSY detection
- Waiting for motion completion
- Limit state retrieval
- HOME state retrieval
- PAUSE state retrieval
- HOLD state retrieval

Added `wait_for_complete()`, which determines whether motion is ongoing using DRIVE state and rotation direction in addition to the BUSY bit.

For positioning, the most recent motion parameters are retained so that intermediate stops and final stops can be distinguished even during moves with backlash compensation.

#### Motion control

Organized and extended the control APIs beyond basic moves:

- Absolute positioning
- Relative positioning
- SCAN
- Constant-speed SCAN
- JOG
- HOME
- FIND HOME
- HOME-direction scan
- STOP / STOP ALL
- EMERGENCY STOP / EMERGENCY STOP ALL

#### Position, speed, and rate settings

Organized or added retrieval and configuration APIs for:

- Current position
- Overwriting the current position
- Setting the zero position
- HIGH / MIDDLE / LOW speed
- Speed profile
- Speed mode
- Rate number
- Conversion between rate values and rate numbers
- Backlash

LOW / MIDDLE / HIGH speeds can now be handled individually or together, rather than only through `set_speed()`.

#### Limits

Extended limit-related retrieval and configuration:

- Software limits
- Hardware limit status
- Digital limit enable
- Hardware limit enable
- Hardware limit normally-open / normally-closed settings
- Limit switch settings

#### HOME

Extended HOME-related retrieval and configuration:

- HOME detection state
- HOME detection direction
- HOME automatic start direction
- HOME position
- HOME offset
- Preset position
- JOG pulses

#### Motor and stop-mode settings

Added retrieval and configuration of the following device settings:

- Motor settings
- Drive enable
- Hold mode
- Output mode
- Stop mode
- Panel stop mode
- Limit stop mode
- HOLD ON time
- HOLD OFF time

### Core data model redesign

The responsibilities of classes representing state and configuration values were comprehensively revised.

Previously, ordinary classes combined several responsibilities:

- Holding raw device responses
- Parsing responses
- Storing values
- Computing derived state through properties

The new design separates data from parsing.

The following state and configuration types are now declared with `@dataclass(frozen=True)`:

- `MotorStatus`
- `ControllerStatus`
- `HomeStatus`
- `LimitStatus`
- `MotorSetting`
- `LimitSwitchSetting`
- `StopMode`

Dataclasses serve as pure data objects holding device state and settings.

Response parsing is delegated to independent parser functions such as:

- `parse_motor_status_all()`
- `parse_controller_status()`
- `parse_home_status()`
- `parse_limit_status_all()`
- `parse_motor_setting()`
- `parse_limit_switch_setting()`
- `parse_stop_mode()`

For responses that cannot be parsed, the policy is to return `None` rather than create objects containing invalid state.

#### MotorStatus extensions

In addition to the previous position, direction, and limit information, `MotorStatus` now parses the MCC status contained in PM2CD's `STS?` response.

Principal fields and state information:

- motor
- channel
- remote/local
- direction
- limit status
- MCC status
- position
- BUSY
- DRIVE
- accelerating
- decelerating
- command error
- limit stop received
- slow stop received
- emergency stop received
- CW / CCW / HP limit
- hold off
- rotation state

Higher-level control code therefore no longer needs to reparse the raw `STS?` response.

### FastAPI / complete auto dispatch

Added and organized a FastAPI server and synchronous/asynchronous clients for PM2CD.

The server uses:

- `FastApiServer`
- `api_spec=None`
- `object_name="pm2cd"`

to expose the public `PM2CD` API through fully automatic dispatch.

The clients are:

- `SyncPM2CDClient`
- `AsyncPM2CDClient`

They use `SyncDeviceClient` / `AsyncDeviceClient`.

The `object_name` setting left over from another device in the initial implementation was corrected; both server and clients consistently use `pm2cd`.

Fully automatic dispatch allows public methods to be invoked over the network without defining a separate `ApiSpec` or Pydantic model on the PM2CD side.

### Compatibility / design notes

In this core dataclass conversion, `PM2CDDevice` absorbs the differences between parsers and dataclasses, so the device-control API visible through the usual `PM2CDsingle` entry point has been preserved as far as possible.

However, code that directly instantiates core classes or calls older methods such as `parse_all()` must migrate to the new parser functions.

Values representing state itself, such as `ControllerStatus.is_remote` and `HomeStatus.found`, are dataclass fields rather than methods.

Dataclasses use `frozen=True` so retrieved device state cannot be modified afterward.

### Tested

- Confirmed TCP communication with physical PM2CD hardware.
- Confirmed basic control through `PM2CDsingle` / `PM2CDDevice`.
- Confirmed local control including state retrieval.
- Confirmed FastAPI server/client connectivity.
- Confirmed multiple PM2CD APIs using fully automatic dispatch in `ese774_frame v0.6.0`.
- APIs returning dataclasses depend on typed automatic transfer in `ese774_frame v0.6.0`.

### Important

**Use ese774_frame v0.6.0 or later** when using fully automatic FastAPI dispatch with the current PM2CD version.

Framework v0.5.1 and earlier do not support fully automatic transfer of dataclasses returned by PM2CD.

## 2026.09.13, v0.0.2, nakada

**PM2CD Ctrl API expansion and cleanup, and improved positioning-completion detection**

- `PM2CDsingle`
    - Added a `motor` property to retain the default motor number.
        - When a method explicitly receives `motor`, that argument takes precedence.
        - When `motor` is omitted, the value of the `motor` property is used.
        - Calls that explicitly specify the motor number remain supported.
    - Updated motor-dependent APIs to allow `motor` to be omitted.
        - Includes motion, stopping, status retrieval, position, speed, acceleration/deceleration, backlash, limits, HOLD, HOME, presets, JOG, motor settings, and stop settings.
    - Updated `move()` / `move_relative()` to retain the motion parameters needed for positioning-completion detection separately for each motor:
        - Target position
        - Whether backlash compensation is enabled
        - Backlash compensation amount
        - For `move_relative()`, the absolute target is calculated from the position before motion.
    - Reorganized positioning completion waiting as `wait_for_complete()`.
        - Evaluates active/inactive state using DRIVE, direction, and current position as well as the BUSY indication from `STS?`.
        - Short moves may finish between polling intervals without an observed active state; observing active state is therefore not mandatory for completion.
        - Without backlash compensation, confirms that the motor is inactive at the target position.
        - With backlash compensation, accounts for the sequence "target position -> backlash point -> target position".
        - Handles both long backlash movements whose intermediate active/inactive states can be observed and short ones whose transitions may occur between polls.
        - Does not immediately treat the first "target position + inactive" observation as completion of backlash compensation; checks the final target position after compensation.
        - Without a positioning context, waits for repeated inactive observations as a simple stop-wait operation.
    - Clearly separated `stop()` / `stop_all()` from `emergency_stop()` / `emergency_stop_all()` as normal and emergency stopping operations.
        - Normal stops use slow stop.
        - Emergency stops use emergency stop.
        - On successful stopping, clears the motion context for the affected motor.
    - Updated state retrieval APIs such as `get_status()` and `is_busy()` to use the default `motor`.
    - Preserved existing information-retrieval APIs such as `version()` / `get_version()`, `controller_status()` / `get_controller_status()`, and `status_all()` / `get_status_all()`.

- Speed and acceleration/deceleration APIs
    - Added and organized a speed-profile API for handling low, middle, and high speeds together.
    - Added and organized individual get/set APIs for high, middle, and low speeds.
    - Separated `get_rate_number()` / `set_rate_number()` from `get_rate()` / `set_rate()`.
        - Rate numbers and actual rate values are handled by distinct APIs.
        - `set_rate()` selects the rate number closest to the requested value from the RATE table.
        - Device-layer `rate_to_number()` / `number_to_rate()` remain available for device and legacy C API conversions.

- Backlash APIs
    - Organized `get_backlash()` / `set_backlash()` as Ctrl APIs.
    - Propagated backlash options and configured compensation amounts from `move()` / `move_relative()` to completion detection.

- Limit APIs
    - Organized Ctrl-layer APIs around semantic values rather than directly exposing raw bits.
    - Retrieves software-limit states as `[CW, CCW]`.
    - Retrieves hardware-limit states as `[CW, CCW, HP]`.
    - Added get/set APIs for enabling software limits.
    - Added get/set APIs for enabling hardware limits.
    - Added APIs for hardware-limit contacts using normally closed / normally open boolean values.
    - Preserved access to Device-layer configuration through `get_limit_switch_setting()`.

- Other
    - Supports external injection of a `Communication` instance, retaining delegation between the communication, Ctrl, and Device layers.
    - Applied Google-style docstrings and type annotations to public APIs.

## v0.0.1 — 2026-09-11

Changes from v0.0.0.

### Added

#### `PM2CD.version`

Added `version` as a property that calls `get_version()`.

```python
version = ctrl.version
```

The existing `get_version()` method remains available.

#### Rate-value interface

The existing interfaces that directly specify a rate number remain unchanged:

- `get_rate_number(motor)`
- `set_rate_number(motor, number)`

Added interfaces that work directly with rate values:

- `get_rate(motor)`
- `set_rate(motor, rate)`

`get_rate()` converts the rate number retrieved from the device into a rate value using the existing `number_to_rate()` function.

`set_rate()` selects the available rate number closest to the requested rate and configures it using the existing `set_rate_number()` method.

Added the following private Ctrl helper to find that nearest rate number:

- `_nearest_rate_number(rate)`

The existing functions remain unchanged:

- `number_to_rate(index)`
- `rate_to_number(rate)`

### Changed

- Changed version retrieval in `main()` from `ctrl.version()` to the `ctrl.version` property.
- Applied Black code formatting.

### Device

`pm2cd_device.py` is unchanged from v0.0.0.

## v0.0.0 — 2026-09-11

Rather than serving simply as a release history, this version is a reference document that establishes the current understanding of the structure, responsibilities, relationship to the C implementation, and APIs for continued design and maintenance of the PM2CD / PM2C-06A Python control code.

### 1. Scope and assumptions

The target device is PM2CD / PM2C-06A. Do not reuse PM16C-16 specifications as if they were PM2CD device specifications.

However, the actual handler implementations in the existing C version, `dev_pm16c16_*`, are used as prior implementations to understand the implementation granularity, processing order, and responsibilities of the Python Device layer.

The examination of the C version covered the actual processing performed inside Device handlers to construct commands, send and receive data, and convert responses, rather than the entire public interface. The examined scope includes rotate/check_rotate, number/rate conversion, emergency stop, backlash, display, hold, limit, pause, pulse, rate, speed, speed mode, status/status_all, SETLS, TTL, version, home, ALLREP, remote, stop, and CRLF transmission/reception.

The Python implementation does not mechanically reproduce each C `.c` file one-to-one. Instead, it preserves the meaning of the actual C handlers while separating the responsibilities of communication, data parsing, Device operations, and the public Ctrl interface.

### 2. Overall architecture

The basic data flow is as follows.

```text
PM2CD (ctrl: public interface)
        ↓ Semantic arguments and return values
PM2CDDevice (device: actual device handlers)
        ↓ command / raw response
Communication (transport)
        ↕ TCP + CRLF
PM2C-06A

Received raw response
        ↓
core data class / parser
        ↓ Meaningful Python values
Device
        ↓
Ctrl
```

The responsibilities are defined as follows.

- `Communication`: Handles only TCP connections and string transmission/reception. It does not interpret PM2CD command semantics.
- `core`: Parses device-specific compound responses and converts bit positions and fixed-format strings into meaningful attributes.
- `PM2CDDevice`: Corresponds to the actual Device handlers in the C implementation. It understands device commands and handles command construction, transmission/reception, sequences of multiple commands where needed, and invocation of core parsers.
- `PM2CD` (`ctrl`): The user-facing public interface. As a rule, it does not expose raw device strings, bit masks, or nibbles; it returns `bool`, `int`, and `List[bool]` values with a defined semantic ordering instead.

Ctrl is not merely a mechanical delegation layer to Device. Its role is to remove device-internal representations from the public API and provide a semantic interface that allows Python users to control the device without knowing the protocol's bit layout.

### 3. Communication layer

The current `Communication` class separates the common transport responsibilities corresponding to `dev_pm16c16_send_crlf()` and `dev_pm16c16_send_crlf_receive()` in the C version into a Python component.

- `send(command)` appends CRLF to the command and transmits it.
- `query(command)` performs sending and receiving within the same lock scope, preserving the correspondence between requests and responses.
- `_receive()` receives data through CRLF and decodes it.
- On a timeout or socket error, the connection state is cleaned up.
- It does not interpret the PM2CD-specific meanings of `FL`, `SETLS`, `STS?`, or other commands.

Do not expand the responsibilities of `Communication` merely to support limit operations.

### 4. Core layer

The core layer is responsible for semantic interpretation of compound device response formats. It is not necessary to turn every single-integer response, such as `FL?` or `BL?`, into a class.

The core classes identified at this point are:

- `ControllerStatus`: Parses controller status responses.
- `MotorStatus`: Parses axis status from `STS?`.
- `HomeStatus`: Parses compound home-related status.
- `MotorSetting`: Parses motor-setting responses.
- `StopMode`: Represents stop-mode semantics.
- `LimitSwitchSetting`: Parses the `DYYY0yyy` setting returned by `SETLS?x`.
- `LimitStatus`: Separately parses the current hardware/software limit states returned by `HDSTLS?`.

#### 4.1 LimitSwitchSetting

`SETLS?x` reports limit-function configuration, not whether a limit is currently active. This distinction is essential.

The `DYYY0yyy` representation is retained and exposes the following semantic attributes:

```text
digital_limit_enabled : software/digital limit enable
hp_enabled            : HP hardware LS enable
ccw_enabled           : CCW hardware LS enable
cw_enabled            : CW hardware LS enable
hp_nc                  : HP contact is normally closed
ccw_nc                 : CCW contact is normally closed
cw_nc                  : CW contact is normally closed
```

`digital_limit_enabled` is a `@property`. An inconsistency in which it had previously been defined as a method but accessed as a property by Device was corrected.

The following read-modify-write helpers are provided:

```python
with_digital_limit(enabled: bool) -> Optional[str]
with_hardware_limit(enabled: bool) -> Optional[str]
with_hardware_limit_normally_closed(
    side: str,
normally_closed: bool,
) -> Optional[str]
```

For PM2C-06A, CW and CCW hardware-limit enable/contact specifications are linked, so CW and CCW are updated to the same value. HP is retained and updated independently.

#### 4.2 LimitStatus

`LimitStatus` represents current state rather than configuration. It parses `abcdHHHHSSSS` from `HDSTLS?` and separates hardware and software limit states for each axis.

The semantic attributes are:

```text
hard_cw
hard_ccw
hard_hp
soft_cw
soft_ccw
```

It also provides semantic lists suitable for passing to Ctrl:

```python
hard -> [CW, CCW, HP]
soft -> [CW, CCW]
```

Raw nibbles and bit masks are not exposed through the public Ctrl API.

#### 4.3 Relationship between MotorStatus and limits

`MotorStatus` parses the ordinary operating status returned by `STS?`. Its LS nibble includes CW, CCW, HP, and HOLD OFF, but is not treated as an explicit separation of hardware and software limit states.

The existing `legacy_status_bits` reconstructs a representation compatible with the older C API; it must not be used as the actual separate hardware/software limit state. Public interfaces requiring that distinction use `HDSTLS?` → `LimitStatus`.

### 5. Device layer

The Device layer retains the responsibilities of the concrete handlers in the C implementation. Do not reduce Device to a thin wrapper around `send()` and `query()`.

In the C implementation, each concrete handler handled command construction, transmission and reception, multiple commands where necessary, and return-value conversion. In Python, part of the raw-response parsing is delegated to core, but multi-command sequences that constitute one operation remain in Device.

Representative mappings are shown below.

```text
C concrete handler                  Python Device
------------------------------------------------------------
get/put pulse                    position / set_position
get/put speed                    speed / set_speed
get/put speed mode               speed_mode / set_speed_mode
get/put rate                     rate_number / set_rate_number
get/put backlash                 backlash / set_backlash
get/put limit                    limit / set_limit
get status / status_all          status / status_all
get/put HLD                      hold / set_hold
home                             home
stop / stop_all                  stop / stop_all
emstop / emstop_all              emergency_stop / emergency_stop_all
check_rotate / rotate            check_rotate / move family
number/rate conversion           number_to_rate / rate_to_number
send_crlf(_receive)              Communication.send/query
```

These mappings are not necessarily one-to-one. The Python implementation organizes the same device operations into more idiomatic Python APIs.

#### 5.1 Software limit position

Device API:

```python
limit(motor: int, side: str) -> Optional[int]
set_limit(motor: int, side: str, pulse: int) -> bool
```

Corresponding commands:

```text
CW  : FL?x / FLx±ddddddd
CCW : BL?x / BLx±ddddddd
```

An unqualified `limit` refers to a software limit. Do not use the bare name `limit` for a hardware limit.

`set_limit()` is not merely a send operation for `FL` or `BL`. It is a compound concrete handler with the same semantics as the C implementation’s `put_limit`.

```text
SETLS?x
  ↓
LimitSwitchSetting
  ↓ software/digital limit is disabled, update D=1
SETLSx...
  ↓
FLx±pulse or BLx±pulse
```

Thus, Device ensures the prerequisite configuration required for the operation of setting a software-limit position.

Signed position commands use `+d`, explicitly including `+` for positive values.

#### 5.2 Limit settings

Device API:

```python
limit_switch_setting(motor: int) -> Optional[LimitSwitchSetting]
limit_switch_setting_raw(motor: int) -> Optional[str]
set_limit_switch_setting_raw(motor: int, setting: str) -> bool
set_digital_limit_enabled(motor: int, enabled: bool) -> bool
set_hard_limit_enabled(motor: int, enabled: bool) -> bool
set_hard_limit_normally_closed(
    motor: int,
side: str,
normally_closed: bool,
) -> bool
```

`limit_switch_setting_raw` and `set_limit_switch_setting_raw` may exist as internal Device handlers, but the public Ctrl API must not expose the raw `DYYY0yyy` representation.

Semantic changes use a `SETLS?` → `LimitSwitchSetting` → `with_*()` → `SETLS` read-modify-write sequence, preserving unrelated configuration bits.

#### 5.3 Current limit status

Device API:

```python
limit_status(motor: int) -> Optional[LimitStatus]
limit_status_all() -> Optional[List[LimitStatus]]
```

`limit_status_all()` queries `HDSTLS?` and passes the response to `LimitStatus.parse_all()`. `limit_status(motor)` selects the requested axis.

Do not use `SETLS?` to retrieve the current limit state.

### 6. Ctrl layer

Ctrl provides the user-facing API. It converts raw Device/core representations into meaningful values.

Design principles:

- Do not require raw command strings.
- Do not return raw response strings.
- Do not return bit masks or nibbles.
- When a Boolean could have several meanings, make its meaning explicit in the API name.
- Return multiple limit-input states as a Python `List[bool]` with a defined order.
- An unqualified `limit` denotes a software limit.
- Explicitly use `hard_` for hardware limits.
- Avoid ambiguous abbreviations such as `NC` in public names; use descriptive terms such as `normally_closed`.

#### 6.1 Ctrl limit API

```python
get_limit(motor: int, side: str) -> Optional[int]
set_limit(motor: int, side: str, pulse: int) -> bool
```

Retrieve or set the software-limit position.

```python
get_limit_status(motor: int) -> Optional[List[bool]]
```

Return value:

```text
[CW, CCW]
```

Current software-limit state.

```python
get_limit_status_all() -> Optional[List[List[bool]]]
```

Software-limit states for all axes.

```python
get_hard_limit_status(motor: int) -> Optional[List[bool]]
```

Return value:

```text
[CW, CCW, HP]
```

Current hardware-limit state.

```python
get_hard_limit_status_all() -> Optional[List[List[bool]]]
```

Hardware-limit states for all axes.

```python
get_limit_enabled(motor: int) -> Optional[bool]
set_limit_enabled(motor: int, enabled: bool) -> bool
```

Retrieve or set the software/digital-limit enable flag.

```python
get_hard_limit_enabled(motor: int) -> Optional[List[bool]]
```

Return value:

```text
[CW, CCW, HP]
```

Return the hardware-limit-switch enable settings as meaningful values.

```python
set_hard_limit_enabled(motor: int, enabled: bool) -> bool
```

Configure CW/CCW hardware-limit enable for PM2C-06A. The current Device implementation updates CW and CCW together according to the PM2C-06A coupled-setting specification, preserving the HP setting.

```python
get_hard_limit_normally_closed(motor: int) -> Optional[List[bool]]
```

Return value:

```text
[CW, CCW, HP]
```

`True` means normally closed; `False` means normally open.

```python
set_hard_limit_normally_closed(
    motor: int,
side: str,
normally_closed: bool,
) -> bool
```

`side` is `hp`, `cw`, or `ccw`. CW and CCW are updated together according to the PM2C-06A specification.

```python
get_limit_switch_setting(motor: int) -> Optional[List[bool]]
```

This semantic interface exists in the current revision and does not return raw `DYYY0yyy`. However, it overlaps with `get_limit_enabled()`, `get_hard_limit_enabled()`, and `get_hard_limit_normally_closed()`. Whether to retain it as a public API remains undecided and requires a future API-wide review.

### 7. Current public Ctrl API

The following public methods were confirmed in the revised `PM2CD` class.

#### Connection and mode

```text
is_connected
connect
disconnect
close
remote
local
```

#### Version and controller state

```text
get_version
get_hardware_version
get_controller_status
```

#### Movement, scanning, and stopping

```text
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

`AESTP` is an emergency-stop command. Do not use it for ordinary initialization or normal stopping.

#### motor status

```text
get_status
get_status_all
```

#### position

```text
get_position
set_position
zero_position
```

#### speed

```text
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
```

#### rate

```text
get_rate_number
set_rate_number
number_to_rate
rate_to_number
```

#### backlash

```text
get_backlash
set_backlash
```

#### limit

```text
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

#### pause

```text
pause
resume
get_pause_status
```

#### hold

```text
get_hold
set_hold
get_hold_on_time
set_hold_on_time
get_hold_off_time
set_hold_off_time
```

#### home setting/status

```text
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

#### motor / stop setting

```text
get_motor_setting
set_motor_setting
get_stop_mode
set_stop_mode
```

#### context manager

```text
__enter__
__exit__
```

### 8. Current Device API

Device is a concrete-handler layer, not the public user API. The confirmed methods are listed below.

#### Basic operations and status

```text
remote
local
version
hardware_version
controller_status
status
status_all
check_rotate
```

#### motion

```text
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
```

#### position/speed/rate/backlash

```text
position
set_position
speed
set_speed
speed_profile
set_speed_profile
high_speed
set_high_speed
middle_speed
set_middle_speed
low_speed
set_low_speed
speed_mode
set_speed_mode
rate_number
set_rate_number
backlash
set_backlash
```

#### limit

```text
limit
set_limit
limit_status
limit_status_all
set_digital_limit_enabled
set_hard_limit_enabled
set_hard_limit_normally_closed
limit_switch_setting
limit_switch_setting_raw
set_limit_switch_setting_raw
```

#### pause/hold

```text
pause
resume
pause_status
hold
set_hold
hold_on_time
set_hold_on_time
hold_off_time
set_hold_off_time
```

#### home/preset/jog setting

```text
home_status
set_home_status
home_position
set_home_position
home_offset
set_home_offset
preset_position
set_preset_position
jog_pulse
set_jog_pulse
```

#### motor/stop setting

```text
motor_setting
set_motor_setting
stop_mode
set_stop_mode
```

#### conversion/helper

```text
number_to_rate
rate_to_number
_send_motor_command
_set_speed_value
_set_hold_time
_query_motor_int
_query_motor_msec
_query_msec
_query_int
_parse_int
_query_text
_query_on_off
_motor_text
_check_motor
_check_position
_check_speed
_check_int
_normalize_direction
_normalize_side
_normalize_speed_mode
_backlash_suffix
_direction_digit
_bool_digit
```

Underscore-prefixed helpers are internal Device implementation details and are not exposed through the Ctrl API.

### 9. Design principles retained from the C implementation

The key lesson from the C source files is not copying command names, but preserving the granularity of concrete Device handlers.

1. Treat each meaningful device operation as one handler.
2. If an operation requires multiple commands, execute them sequentially within the Device handler.
3. Centralize communication itself.
4. In Python, delegate device-specific interpretation of received data to core classes when appropriate.
5. Ctrl must not expose the device’s internal representations directly.

`set_limit()` is a representative example of this principle. Do not simply split `SETLS?` and `FL/BL` into separate user operations. Device must satisfy the prerequisites for setting a software-limit position.

### 10. Established distinctions among limit concepts

```text
software limit position
    FL? / FL
    BL? / BL

limit function setting
    SETLS?
    software limit enable
    hardware LS enable
    hardware LS contact specification

current limit state
    HDSTLS?
    retrieve hardware and software separately

normal motor/controller status
    STS?
    MotorStatus
```

Do not interpret `SETLS?` as the current limit state.

### 11. Changes in v0.0.0

- Standardized `LimitSwitchSetting.digital_limit_enabled` as a property.
- Added read-modify-write operations for hardware-limit enable/contact settings to `LimitSwitchSetting`.
- Added a core `LimitStatus` parser for `HDSTLS?`.
- Added `limit_status()` and `limit_status_all()` to Device.
- Added semantic software/hardware-limit configuration operations to Device.
- Preserved the C-derived automatic software-limit enable behavior in `set_limit()`.
- Used `+d` for signed limit-position commands, explicitly including `+` for positive values.
- Kept the raw SETLS API private to Device; exposed limit states, enable flags, and contact specifications through semantic `bool` / `List[bool]` interfaces in Ctrl.
- Preserved the naming convention: unqualified `limit` for software limits and explicit `hard_` for hardware limits.
