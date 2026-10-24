# Device Protocol

[English](../../en/manual/protocol.html) | [日本語](../../ja/manual/protocol.html)

## Scope and primary source

The primary device source is Tsujicon, *PM4C-06A Series Operating Manual*, Revision 4 (2022-04-15), covering the PM2C-06A among other models. The PM16C-16 is not assumed to be an identical device.

## Communication

The manufacturer specifies a common command set for LAN, RS-232C, and GP-IB, with CR+LF as a fixed delimiter. The Python `Communication` implementation uses TCP, ASCII encoding, and CR+LF framing.

## Representative commands

| Command | Function |
|---|---|
| `REM` / `LOC` | Remote / local mode |
| `VER?` | Firmware version |
| `PS?x` / `PSx±ddddddd` | Position query / preset |
| `ABSx±ddddddd` / `RELx±ddddddd` | Absolute / relative move |
| `SSTPx` / `ESTPx` | Slow / fast stop |
| `STS?` | Read aggregate status |
| `SETLS?x` / `SETLSx...` | Limit switch configuration |
| `FL?x` / `BL?x` | Read software limits |

The manufacturer's series-wide notation allows `x` from 0 to 3; **this PM2CD Python implementation accepts only channels 0 and 1**. See pages 2–4 of the manufacturer manual for command tables and the later command-description section for details.

## Python API versus raw commands

`set_limit()` reads `SETLS?x`, enables digital limits if necessary, and issues the configuration and `FLx` / `BLx` commands. Users need not reconstruct that multi-command sequence manually.


> Before moving hardware, verify wiring, limit switches, travel direction, and permissible travel. The examples have not been run against a physical controller.
