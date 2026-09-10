from .errors import ProtocolError


class MotorSetting:
    """``SETMT?x`` の ``ABCD`` 応答を保持する。"""

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")
        text = raw.strip()
        if len(text) != 4:
            raise ProtocolError("SETMT?応答を解釈できません: {!r}".format(raw))
        if text[0] not in ("0", "1"):
            raise ProtocolError("SETMT?応答のdrive設定が不正です: {!r}".format(raw))
        if text[1] not in ("0", "1", "2", "3"):
            raise ProtocolError("SETMT?応答のhold設定が不正です: {!r}".format(raw))
        if text[2] != "1":
            raise ProtocolError("SETMT?応答のdrive形式が不正です: {!r}".format(raw))
        if text[3] not in ("0", "1", "2"):
            raise ProtocolError("SETMT?応答の出力方式が不正です: {!r}".format(raw))
        self.raw = text
        self.drive_enabled = text[0] == "1"
        self.hold_mode = int(text[1])
        self.drive_mode = int(text[2])
        self.output_mode = int(text[3])

    def __repr__(self) -> str:
        return "MotorSetting(raw={!r})".format(self.raw)
