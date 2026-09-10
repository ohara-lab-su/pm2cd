from .errors import ProtocolError


class ControllerStatus:
    """``STQ?`` の REMOTE/LOCAL と停止可能数を保持する。"""

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")

        text = raw.strip().upper()
        if len(text) != 2 or text[0] not in ("R", "L") or not text[1].isdigit():
            raise ProtocolError("STQ?応答を解釈できません: {!r}".format(raw))

        stopped_motor_count = int(text[1])
        if stopped_motor_count < 0 or stopped_motor_count > 4:
            raise ProtocolError("STQ?応答のモーター数が範囲外です: {!r}".format(raw))

        self.raw = text
        self.remote_local = text[0]
        self.stopped_motor_count = stopped_motor_count

    @property
    def is_remote(self) -> bool:
        return self.remote_local == "R"

    @property
    def can_start(self) -> bool:
        return self.stopped_motor_count > 0

    def __repr__(self) -> str:
        return "ControllerStatus(raw={!r}, stopped_motor_count={!r})".format(
            self.raw,
            self.stopped_motor_count,
        )
