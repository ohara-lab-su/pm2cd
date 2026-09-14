from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LimitSwitchSetting:
    """``SETLS?x`` のリミットスイッチ設定を保持する。"""

    raw: str
    digital_limit_enabled: bool
    hp_enabled: bool
    ccw_enabled: bool
    cw_enabled: bool
    hp_nc: bool
    ccw_nc: bool
    cw_nc: bool


def parse_limit_switch_setting(raw: str) -> Optional[LimitSwitchSetting]:
    """``SETLS?x`` の ``DYYY0yyy`` 応答を解析する。"""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if len(text) != 8 or text[4] != '0':
        return None
    if any(value not in ('0', '1') for value in text):
        return None

    return LimitSwitchSetting(
        raw=text,
        digital_limit_enabled=text[0] == '1',
        hp_enabled=text[1] == '1',
        ccw_enabled=text[2] == '1',
        cw_enabled=text[3] == '1',
        hp_nc=text[5] == '1',
        ccw_nc=text[6] == '1',
        cw_nc=text[7] == '1',
    )


def set_digital_limit(setting: LimitSwitchSetting, enabled: bool) -> Optional[str]:
    """デジタルリミット設定だけを書き換えた設定文字列を返す。"""
    if not isinstance(enabled, bool):
        return None
    return ('1' if enabled else '0') + setting.raw[1:]


def set_hardware_limit(setting: LimitSwitchSetting, enabled: bool) -> Optional[str]:
    """CW/CCW ハードウェアリミット設定を書き換えた文字列を返す。"""
    if not isinstance(enabled, bool):
        return None
    value = '1' if enabled else '0'
    return setting.raw[:2] + value + value + setting.raw[4:]


def set_hardware_limit_normally_closed(
    setting: LimitSwitchSetting,
    side: str,
    normally_closed: bool,
) -> Optional[str]:
    """ハードウェアLSの接点仕様を書き換えた設定文字列を返す。"""
    if not isinstance(side, str) or not isinstance(normally_closed, bool):
        return None

    normalized = side.strip().lower()
    if normalized not in ('hp', 'cw', 'ccw'):
        return None

    value = '1' if normally_closed else '0'
    chars = list(setting.raw)
    if normalized == 'hp':
        chars[5] = value
    else:
        chars[6] = value
        chars[7] = value
    return ''.join(chars)
