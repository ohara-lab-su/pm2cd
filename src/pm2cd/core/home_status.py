from .errors import ProtocolError


class HomeStatus:
    """``SETHP?x`` の ``0XYZ`` 応答を保持する。"""

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")
        text = raw.strip()
        if len(text) != 4 or text[0] != "0":
            raise ProtocolError("SETHP?応答を解釈できません: {!r}".format(raw))
        for value in text[1:]:
            if value not in ("0", "1"):
                raise ProtocolError("SETHP?応答を解釈できません: {!r}".format(raw))
        self.raw = text

    @property
    def found(self) -> bool:
        return self.raw[1] == "1"

    @property
    def found_direction(self) -> str:
        if self.raw[2] == "0":
            return "cw"
        return "ccw"

    @property
    def auto_start_direction(self) -> str:
        if self.raw[3] == "0":
            return "cw"
        return "ccw"

    def __repr__(self) -> str:
        return "HomeStatus(raw={!r})".format(self.raw)
