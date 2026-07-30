# from __future__ import annotations

from .errors import ProtocolError


class MotorStatus:
    """1軸分の状態を保持し、状態判定も担当する。"""

    def __init__(
        self,
        motor: int,
        raw: str = "",
        remote_local: str = "",
        direction: str = "S",
        ls_status: int = 0,
        motor_status: str = "",
        position: int = 0,
    ):
        self.motor = motor
        self.raw = raw
        self.remote_local = remote_local
        self.direction = direction
        self.ls_status = ls_status
        self.motor_status = motor_status
        self.position = position

    @classmethod
    def from_single_response(
        cls,
        requested_motor: int,
        raw: str,
    ) -> "MotorStatus":
        if len(raw) < 7:
            raise ProtocolError(f"STS応答が不正です: {raw!r}")

        try:
            motor = int(raw[1], 16)
            ls_status = int(raw[3], 16)
            position = int(raw[6:])
        except ValueError as exc:
            raise ProtocolError(f"STS応答を解析できません: {raw!r}") from exc

        if motor != requested_motor:
            requested_motor = motor

        return cls(
            motor=requested_motor,
            raw=raw,
            remote_local=raw[0],
            direction=raw[2],
            ls_status=ls_status,
            motor_status=raw[4:6],
            position=position,
        )

    @property
    def is_busy(self) -> bool:
        return self.direction in ("P", "N")

    @property
    def rotation_state(self) -> int:
        return 1 if self.is_busy else 0

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
            f"MotorStatus(motor={self.motor}, direction={self.direction!r}, "
            f"position={self.position}, ls_status={self.ls_status:#x})"
        )
