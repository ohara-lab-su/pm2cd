from .errors import ProtocolError


class LimitSwitchSetting:
    """``SETLS?x`` の ``DYYY0yyy`` 応答を保持する。"""

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")
        text = raw.strip()
        if len(text) != 8:
            raise ProtocolError("SETLS?応答の長さが不正です: {!r}".format(raw))
        if text[4] != "0":
            raise ProtocolError("SETLS?応答の予約ビットが不正です: {!r}".format(raw))
        for value in text:
            if value not in ("0", "1"):
                raise ProtocolError("SETLS?応答が2進表記ではありません: {!r}".format(raw))
        self.raw = text

    @property
    def digital_limit_enabled(self) -> bool:
        return self.raw[0] == "1"

    @property
    def hp_enabled(self) -> bool:
        return self.raw[1] == "1"

    @property
    def ccw_enabled(self) -> bool:
        return self.raw[2] == "1"

    @property
    def cw_enabled(self) -> bool:
        return self.raw[3] == "1"

    @property
    def hp_nc(self) -> bool:
        return self.raw[5] == "1"

    @property
    def ccw_nc(self) -> bool:
        return self.raw[6] == "1"

    @property
    def cw_nc(self) -> bool:
        return self.raw[7] == "1"

    def with_digital_limit(self, enabled: bool) -> str:
        if not isinstance(enabled, bool):
            raise TypeError("enabledはboolで指定してください")
        prefix = "0"
        if enabled:
            prefix = "1"
        return prefix + self.raw[1:]

    def __repr__(self) -> str:
        return "LimitSwitchSetting(raw={!r})".format(self.raw)
