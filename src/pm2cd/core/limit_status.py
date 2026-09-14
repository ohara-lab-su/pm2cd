from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class LimitStatus:
    """``HDSTLS?`` 応答中の1軸分のリミット状態を保持する。"""

    motor: int
    channel: int
    raw: str
    hard_status: int
    soft_status: int
    hard_cw: bool
    hard_ccw: bool
    hard_hp: bool
    soft_cw: bool
    soft_ccw: bool


def parse_limit_status_all(raw: str) -> Optional[List[LimitStatus]]:
    """``HDSTLS?`` の ``abcdHHHHSSSS`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if len(text) != 12:
        return None

    try:
        channels = [int(value, 16) for value in text[0:4]]
        hard_values = [int(value, 16) for value in text[4:8]]
        soft_values = [int(value, 16) for value in text[8:12]]
    except ValueError:
        return None

    values = []
    for index in range(4):
        hard_status = hard_values[index]
        soft_status = soft_values[index]
        if hard_status & ~0x07:
            return None
        if soft_status & ~0x03:
            return None

        values.append(
            LimitStatus(
                motor=index,
                channel=channels[index],
                raw=text,
                hard_status=hard_status,
                soft_status=soft_status,
                hard_cw=bool(hard_status & 0x01),
                hard_ccw=bool(hard_status & 0x02),
                hard_hp=bool(hard_status & 0x04),
                soft_cw=bool(soft_status & 0x01),
                soft_ccw=bool(soft_status & 0x02),
            )
        )

    return values
