from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StopMode:
    """``STOPMD?x`` の停止モード設定を保持する。"""

    raw: str
    panel_fast: bool
    limit_fast: bool


def parse_stop_mode(raw: str) -> Optional[StopMode]:
    """``STOPMD?x`` の ``AB`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if len(text) != 2 or any(value not in ('0', '1') for value in text):
        return None

    return StopMode(
        raw=text,
        panel_fast=text[0] == '1',
        limit_fast=text[1] == '1',
    )
