from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MotorStatus:
    """``STS?`` 応答中の1軸分の状態を保持する。"""

    motor: int
    channel: int
    raw: str
    remote_local: str
    direction: str
    ls_status: int
    mcc_status: int
    position: int
    motor_status: str
    is_busy: bool
    is_driving: bool
    is_accelerating: bool
    is_decelerating: bool
    has_command_error: bool
    limit_stop_received: bool
    slow_stop_received: bool
    emergency_stop_received: bool
    rotation_state: int
    cw_ls: bool
    ccw_ls: bool
    hp_ls: bool
    hold_off: bool
    legacy_status_bits: int


def parse_motor_status_all(raw: str) -> Optional[List[MotorStatus]]:
    """PM4C-06A互換の ``STS?`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    parts = text.split('/')
    if len(parts) < 5:
        return None

    header = parts[0]
    directions = parts[1]
    limits = parts[2]
    mcc = parts[3]
    positions = parts[4:]

    if len(header) < 2 or header[0] not in ('R', 'L'):
        return None

    motor_count = len(header) - 1
    if len(parts) != 4 + motor_count:
        return None
    if len(directions) != motor_count:
        return None
    if any(value not in 'PNS' for value in directions):
        return None
    if len(limits) != motor_count:
        return None
    if len(mcc) != motor_count * 2:
        return None

    try:
        channels = [int(value, 16) for value in header[1:]]
        ls_values = [int(value, 16) for value in limits]
        mcc_values = [int(mcc[index:index + 2], 16) for index in range(0, len(mcc), 2)]
        position_values = [int(value, 10) for value in positions]
    except ValueError:
        return None

    statuses = []
    for index in range(motor_count):
        ls_status = ls_values[index]
        mcc_status = mcc_values[index]
        direction = directions[index]

        cw_ls = bool(ls_status & 0x01)
        ccw_ls = bool(ls_status & 0x02)
        hp_ls = bool(ls_status & 0x04)
        hold_off = bool(ls_status & 0x08)

        legacy_status_bits = 0
        if cw_ls:
            legacy_status_bits |= 0x01 | 0x04
        if ccw_ls:
            legacy_status_bits |= 0x02 | 0x08
        if hp_ls:
            legacy_status_bits |= 0x10

        statuses.append(
            MotorStatus(
                motor=index,
                channel=channels[index],
                raw=text,
                remote_local=header[0],
                direction=direction,
                ls_status=ls_status,
                mcc_status=mcc_status,
                position=position_values[index],
                motor_status=f"{mcc_status:02X}",
                is_busy=bool(mcc_status & 0x01),
                is_driving=bool(mcc_status & 0x02),
                is_accelerating=bool(mcc_status & 0x04),
                is_decelerating=bool(mcc_status & 0x08),
                has_command_error=bool(mcc_status & 0x10),
                limit_stop_received=bool(mcc_status & 0x20),
                slow_stop_received=bool(mcc_status & 0x40),
                emergency_stop_received=bool(mcc_status & 0x80),
                rotation_state=1 if direction in ('P', 'N') else 0,
                cw_ls=cw_ls,
                ccw_ls=ccw_ls,
                hp_ls=hp_ls,
                hold_off=hold_off,
                legacy_status_bits=legacy_status_bits,
            )
        )

    return statuses
