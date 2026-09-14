from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HomeStatus:
    """``SETHP?x`` の ``0XYZ`` 応答を保持する。"""

    raw: str
    found: bool
    found_direction: str
    auto_start_direction: str


def parse_home_status(raw: str) -> Optional[HomeStatus]:
    """``SETHP?x`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if len(text) != 4 or text[0] != '0':
        return None
    if any(value not in ('0', '1') for value in text[1:]):
        return None

    return HomeStatus(
        raw=text,
        found=text[1] == '1',
        found_direction='cw' if text[2] == '0' else 'ccw',
        auto_start_direction='cw' if text[3] == '0' else 'ccw',
    )
