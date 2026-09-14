from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ControllerStatus:
    """``STQ?`` の REMOTE/LOCAL と停止可能数を保持する。"""

    raw: str
    remote_local: str
    stopped_motor_count: int
    is_remote: bool
    can_start: bool


def parse_controller_status(raw: str) -> Optional[ControllerStatus]:
    """``STQ?`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip().upper()
    if len(text) != 2 or text[0] not in ('R', 'L') or not text[1].isdigit():
        return None

    count = int(text[1])
    if count < 0 or count > 4:
        return None

    return ControllerStatus(
        raw=text,
        remote_local=text[0],
        stopped_motor_count=count,
        is_remote=text[0] == 'R',
        can_start=count > 0,
    )
