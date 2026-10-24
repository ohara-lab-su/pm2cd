# Core Concepts

[English](../../en/manual/concepts.html) | [日本語](../../ja/manual/concepts.html)

## Layers and responsibilities

- `Communication`: TCP socket, CR+LF framing, and synchronization. It does not interpret device commands.
- `PM2CDDevice`: device-specific command construction, response parsing, and input validation.
- `PM2CDsingle`: single-process public interface, including motor selection and motion completion detection.
- `PM2CD`: multiprocess public interface built on `ProcessExecutor`, using a shared `Communication` instance and `SharedContext`.

## Important distinctions

The `motor` property selects the channel used when a method omits its `motor` argument. `move(..., relative=False)` specifies an absolute position, while `relative=True` specifies a relative displacement. `wait_for_complete()` uses the most recent motion context to distinguish an intermediate stop during backlash compensation from final completion.

The multiprocess implementation does **not** create a separate TCP connection for every worker; it shares and serializes communication.


> Before moving hardware, verify wiring, limit switches, travel direction, and permissible travel. The examples have not been run against a physical controller.
