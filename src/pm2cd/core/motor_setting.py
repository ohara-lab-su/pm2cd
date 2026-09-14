from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MotorSetting:
    """``SETMT?x`` のモーター設定を保持する。"""

    raw: str
    drive_enabled: bool
    hold_mode: int
    drive_mode: int
    output_mode: int


def parse_motor_setting(raw: str) -> Optional[MotorSetting]:
    """``SETMT?x`` の ``ABCD`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if len(text) != 4:
        return None
    if text[0] not in ('0', '1'):
        return None
    if text[1] not in ('0', '1', '2', '3'):
        return None
    if text[2] != '1':
        return None
    if text[3] not in ('0', '1', '2'):
        return None

    return MotorSetting(
        raw=text,
        drive_enabled=text[0] == '1',
        hold_mode=int(text[1]),
        drive_mode=int(text[2]),
        output_mode=int(text[3]),
    )
