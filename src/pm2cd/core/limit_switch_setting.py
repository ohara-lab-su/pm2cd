from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LimitSwitchSetting:
    """``SETLS?x`` の ``DYYY0yyy`` 応答を保持する。

    PM□C-06 シリーズでは、書き込み時の HP LS enable は常に 1 であり、
    CCW LS の enable / 接点仕様が CW LS にも適用される。
    読み出し応答そのものはマニュアル記載どおり ``DYYY0yyy`` として保持する。
    """

    raw: str
    digital_limit_enabled: bool
    raw_hp_enabled: bool
    raw_ccw_enabled: bool
    raw_cw_enabled: bool
    hp_nc: bool
    raw_ccw_nc: bool
    raw_cw_nc: bool

    @property
    def hp_enabled(self) -> bool:
        """PM□C-06 で実効的に常時有効な HP LS enable を返す。"""
        return True

    @property
    def ccw_enabled(self) -> bool:
        """PM□C-06 の実効 CCW LS enable を返す。"""
        return self.raw_ccw_enabled

    @property
    def cw_enabled(self) -> bool:
        """PM□C-06 では CCW 設定が適用される CW LS enable を返す。"""
        return self.raw_ccw_enabled

    @property
    def ccw_nc(self) -> bool:
        """PM□C-06 の実効 CCW LS 接点仕様を返す。"""
        return self.raw_ccw_nc

    @property
    def cw_nc(self) -> bool:
        """PM□C-06 では CCW 設定が適用される CW LS 接点仕様を返す。"""
        return self.raw_ccw_nc

    def to_write_raw(self) -> str:
        """PM□C-06 用 ``D1YY0yyy`` 書き込み値を生成する。

        ``SETLS?x`` の読み出し値をそのまま再送せず、装置仕様に従って
        HP LS enable を 1 に固定し、CCW の enable / 接点仕様を CW にも
        適用した canonical な書き込み値を返す。
        """
        digital = '1' if self.digital_limit_enabled else '0'
        hard = '1' if self.raw_ccw_enabled else '0'
        hp_nc = '1' if self.hp_nc else '0'
        hard_nc = '1' if self.raw_ccw_nc else '0'
        return digital + '1' + hard + hard + '0' + hp_nc + hard_nc + hard_nc


def parse_limit_switch_setting(raw: str) -> Optional[LimitSwitchSetting]:
    """``SETLS?x`` の ``DYYY0yyy`` 応答を解析する。

    8文字の位置は順に、
    ``D, HP-enable, CCW-enable, CW-enable, 0,
    HP-contact, CCW-contact, CW-contact``。

    読み出しでは ``DYYY0yyy`` をそのまま解析し、PM□C-06 固有の
    実効値への解釈は ``LimitSwitchSetting`` の property が担当する。
    """
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
        raw_hp_enabled=text[1] == '1',
        raw_ccw_enabled=text[2] == '1',
        raw_cw_enabled=text[3] == '1',
        hp_nc=text[5] == '1',
        raw_ccw_nc=text[6] == '1',
        raw_cw_nc=text[7] == '1',
    )


def set_digital_limit(setting: LimitSwitchSetting, enabled: bool) -> Optional[str]:
    """digital limit enable を変更した PM□C-06 書き込み値を返す。"""
    if not isinstance(enabled, bool):
        return None

    value = LimitSwitchSetting(
        raw=setting.raw,
        digital_limit_enabled=enabled,
        raw_hp_enabled=setting.raw_hp_enabled,
        raw_ccw_enabled=setting.raw_ccw_enabled,
        raw_cw_enabled=setting.raw_cw_enabled,
        hp_nc=setting.hp_nc,
        raw_ccw_nc=setting.raw_ccw_nc,
        raw_cw_nc=setting.raw_cw_nc,
    )
    return value.to_write_raw()


def set_hardware_limit(setting: LimitSwitchSetting, enabled: bool) -> Optional[str]:
    """CW/CCW hardware LS enable を同時変更した書き込み値を返す。"""
    if not isinstance(enabled, bool):
        return None

    value = LimitSwitchSetting(
        raw=setting.raw,
        digital_limit_enabled=setting.digital_limit_enabled,
        raw_hp_enabled=True,
        raw_ccw_enabled=enabled,
        raw_cw_enabled=enabled,
        hp_nc=setting.hp_nc,
        raw_ccw_nc=setting.raw_ccw_nc,
        raw_cw_nc=setting.raw_ccw_nc,
    )
    return value.to_write_raw()


def set_hardware_limit_normally_closed(
    setting: LimitSwitchSetting,
    side: str,
    normally_closed: bool,
) -> Optional[str]:
    """hardware LS の接点仕様を変更した PM□C-06 書き込み値を返す。

    HP は独立して変更する。CW または CCW を指定した場合は、
    PM□C-06 の仕様に従い CCW/CW を同じ接点仕様へ変更する。
    """
    if not isinstance(side, str) or not isinstance(normally_closed, bool):
        return None

    normalized = side.strip().lower()
    if normalized not in ('hp', 'cw', 'ccw'):
        return None

    hp_nc = setting.hp_nc
    hard_nc = setting.raw_ccw_nc
    if normalized == 'hp':
        hp_nc = normally_closed
    else:
        hard_nc = normally_closed

    value = LimitSwitchSetting(
        raw=setting.raw,
        digital_limit_enabled=setting.digital_limit_enabled,
        raw_hp_enabled=True,
        raw_ccw_enabled=setting.raw_ccw_enabled,
        raw_cw_enabled=setting.raw_ccw_enabled,
        hp_nc=hp_nc,
        raw_ccw_nc=hard_nc,
        raw_cw_nc=hard_nc,
    )
    return value.to_write_raw()
