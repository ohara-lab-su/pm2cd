from typing import List, Optional


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
    def parse_all(
        cls,
        raw: str,
    ) -> Optional[List["MotorStatus"]]:
        """PM4C-06A互換の4枠 ``STS?`` 応答を解析する。"""
        if not isinstance(
            raw,
            str
        ):
            return None

        text = raw.strip()
        parts = text.split(
            "/"
        )
        if len(parts) != 8:
            return None

        header = parts[0]
        directions = parts[1]
        limits = parts[2]
        mcc = parts[3]
        positions = parts[4:]

        if len(header) != 5 or header[0] not in ("R", "L",):
            return None

        if len(directions) != 4:
            return None

        for value in directions:
            if value not in "PNS":
                return None

        if len(limits) != 4:
            return None

        if len(mcc) != 8:
            return None

        try:
            channels = [
                int(
                    value,
                    16
                )
                for value in header[1:]
            ]
            ls_values = [
                int(
                    value,
                    16
                )
                for value in limits
            ]
            mcc_values = []
            for index in range(
                0,
                8,
                2
            ):
                mcc_values.append(
                    int(
                        mcc[index : index + 2],
                        16
                    )
                )
            position_values = [
                int(
                    value,
                    10
                )
                for value in positions
            ]
        except ValueError:
            return None

        statuses = []
        for index in range(
            4
        ):
            statuses.append(
                cls(
                    motor=index,
                    channel=channels[index],
                    raw=text,
                    remote_local=header[0],
                    direction=directions[index],
                    ls_status=ls_values[index],
                    mcc_status=mcc_values[index],
                    position=position_values[index]
                )
            )

        return statuses

    @property
    def motor_status(
        self,
    ) -> str:
        return f"{self.mcc_status:02X}"

    @property
    def is_busy(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x01
        )

    @property
    def is_driving(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x02
        )

    @property
    def is_accelerating(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x04
        )

    @property
    def is_decelerating(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x08
        )

    @property
    def has_command_error(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x10
        )

    @property
    def limit_stop_received(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x20
        )

    @property
    def slow_stop_received(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x40
        )

    @property
    def emergency_stop_received(
        self,
    ) -> bool:
        return bool(
            self.mcc_status & 0x80
        )

    @property
    def rotation_state(
        self,
    ) -> int:
        if self.direction in ("P", "N",):
            return 1

        return 0

    @property
    def cw_ls(
        self,
    ) -> bool:
        return bool(
            self.ls_status & 0x01
        )

    @property
    def ccw_ls(
        self,
    ) -> bool:
        return bool(
            self.ls_status & 0x02
        )

    @property
    def hp_ls(
        self,
    ) -> bool:
        return bool(
            self.ls_status & 0x04
        )

    @property
    def hold_off(
        self,
    ) -> bool:
        return bool(
            self.ls_status & 0x08
        )

    @property
    def legacy_status_bits(
        self,
    ) -> int:
        status = 0

        if self.cw_ls:
            status |= 0x01 | 0x04

        if self.ccw_ls:
            status |= 0x02 | 0x08

        if self.hp_ls:
            status |= 0x10

        return status

    def __repr__(
        self,
    ) -> str:
        return (
            f"MotorStatus(motor={self.motor!r}, "
            f"channel={self.channel!r}, "
            f"remote_local={self.remote_local!r}, "
            f"direction={self.direction!r}, "
            f"ls_status=0x{self.ls_status:X}, "
            f"mcc_status=0x{self.mcc_status:02X}, "
            f"position={self.position!r})"
        )

def main(
) -> None:
    """MotorStatus の STS? 解析例を実行する。

    Returns:
        None。
    """
    # STS? の4枠応答形式を確認するための解析用サンプル。
    raw = "R0123/PNSN/0000/01020000/100/200/300/400"
    values = MotorStatus.parse_all(
        raw
    )

    if values is None:
        print(f"parse failed: {raw!r}")
        return

    for value in values:
        print(value)
        print(
            f"  motor={value.motor}, "
            f"channel={value.channel}, "
            f"busy={value.is_busy}, "
            f"driving={value.is_driving}, "
            f"direction={value.direction!r}, "
            f"position={value.position}"
        )


if __name__ == "__main__":
    main()
