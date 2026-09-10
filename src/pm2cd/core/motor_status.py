from typing import List

from .errors import ProtocolError


class MotorStatus:
    """``STS?`` 応答中の1軸分の状態を保持する。"""

    def __init__(
        self,
        motor: int,
        channel: int,
        raw: str,
        remote_local: str,
        direction: str,
        ls_status: int,
        mcc_status: int,
        position: int,
    ):
        self.motor = motor
        self.channel = channel
        self.raw = raw
        self.remote_local = remote_local
        self.direction = direction
        self.ls_status = ls_status
        self.mcc_status = mcc_status
        self.position = position

    @classmethod
    def parse_all(cls, raw: str) -> List["MotorStatus"]:
        """PM4C-06A互換の4枠 ``STS?`` 応答を解析する。"""
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")

        text = raw.strip()
        parts = text.split("/")
        if len(parts) != 8:
            raise ProtocolError("STS?応答の区切り数が不正です: {!r}".format(raw))

        header = parts[0]
        directions = parts[1]
        limits = parts[2]
        mcc = parts[3]
        positions = parts[4:]

        if len(header) != 5 or header[0] not in ("R", "L"):
            raise ProtocolError("STS?応答のREM/LOC・CH部が不正です: {!r}".format(raw))
        if len(directions) != 4:
            raise ProtocolError("STS?応答の方向部が不正です: {!r}".format(raw))
        for value in directions:
            if value not in "PNS":
                raise ProtocolError("STS?応答の方向部が不正です: {!r}".format(raw))
        if len(limits) != 4:
            raise ProtocolError("STS?応答のLS状態部が不正です: {!r}".format(raw))
        if len(mcc) != 8:
            raise ProtocolError("STS?応答のMCC状態部が不正です: {!r}".format(raw))

        try:
            channels = [int(value, 16) for value in header[1:]]
            ls_values = [int(value, 16) for value in limits]
            mcc_values = []
            for index in range(0, 8, 2):
                mcc_values.append(int(mcc[index : index + 2], 16))
            position_values = [int(value, 10) for value in positions]
        except ValueError as exc:
            raise ProtocolError("STS?応答を数値へ変換できません: {!r}".format(raw)) from exc

        statuses = []
        for index in range(4):
            statuses.append(
                cls(
                    motor=index,
                    channel=channels[index],
                    raw=text,
                    remote_local=header[0],
                    direction=directions[index],
                    ls_status=ls_values[index],
                    mcc_status=mcc_values[index],
                    position=position_values[index],
                )
            )
        return statuses

    @property
    def motor_status(self) -> str:
        return "{:02X}".format(self.mcc_status)

    @property
    def is_busy(self) -> bool:
        return bool(self.mcc_status & 0x01)

    @property
    def is_driving(self) -> bool:
        return bool(self.mcc_status & 0x02)

    @property
    def is_accelerating(self) -> bool:
        return bool(self.mcc_status & 0x04)

    @property
    def is_decelerating(self) -> bool:
        return bool(self.mcc_status & 0x08)

    @property
    def has_command_error(self) -> bool:
        return bool(self.mcc_status & 0x10)

    @property
    def limit_stop_received(self) -> bool:
        return bool(self.mcc_status & 0x20)

    @property
    def slow_stop_received(self) -> bool:
        return bool(self.mcc_status & 0x40)

    @property
    def emergency_stop_received(self) -> bool:
        return bool(self.mcc_status & 0x80)

    @property
    def rotation_state(self) -> int:
        if self.direction in ("P", "N"):
            return 1
        return 0

    @property
    def cw_ls(self) -> bool:
        return bool(self.ls_status & 0x01)

    @property
    def ccw_ls(self) -> bool:
        return bool(self.ls_status & 0x02)

    @property
    def hp_ls(self) -> bool:
        return bool(self.ls_status & 0x04)

    @property
    def hold_off(self) -> bool:
        return bool(self.ls_status & 0x08)

    @property
    def legacy_status_bits(self) -> int:
        status = 0
        if self.cw_ls:
            status |= 0x01 | 0x04
        if self.ccw_ls:
            status |= 0x02 | 0x08
        if self.hp_ls:
            status |= 0x10
        return status

    def __repr__(self) -> str:
        return (
            "MotorStatus(motor={!r}, channel={!r}, remote_local={!r}, "
            "direction={!r}, ls_status=0x{:X}, mcc_status=0x{:02X}, position={!r})"
        ).format(
            self.motor,
            self.channel,
            self.remote_local,
            self.direction,
            self.ls_status,
            self.mcc_status,
            self.position,
        )
