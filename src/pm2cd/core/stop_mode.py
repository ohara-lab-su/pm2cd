from .errors import ProtocolError


class StopMode:
    """``STOPMD?x`` の ``AB`` 応答を保持する。"""

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")
        text = raw.strip()
        if len(text) != 2:
            raise ProtocolError("STOPMD?応答を解釈できません: {!r}".format(raw))
        for value in text:
            if value not in ("0", "1"):
                raise ProtocolError("STOPMD?応答を解釈できません: {!r}".format(raw))
        self.raw = text
        self.panel_fast = text[0] == "1"
        self.limit_fast = text[1] == "1"

    def __repr__(self) -> str:
        return "StopMode(raw={!r})".format(self.raw)
