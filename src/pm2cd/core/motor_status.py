from typing import List, Optional


# STS? 応答を4枠へ分解し、各モータの位置・方向・LS・MCC状態を保持する。
# MCC と LS のビット解釈は property に分離し、呼び出し側で生値を解読させない。

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
        self._motor = motor
        self._channel = channel
        self._raw = raw
        self._remote_local = remote_local
        self._direction = direction
        self._ls_status = ls_status
        self._mcc_status = mcc_status
        self._position = position

    @property
    def motor(
        self,
    ):
        """motor を返す。"""
        return self._motor

    @property
    def channel(
        self,
    ):
        """channel を返す。"""
        return self._channel

    @property
    def raw(
        self,
    ):
        """raw を返す。"""
        return self._raw

    @property
    def remote_local(
        self,
    ):
        """remote_local を返す。"""
        return self._remote_local

    @property
    def direction(
        self,
    ):
        """direction を返す。"""
        return self._direction

    @property
    def ls_status(
        self,
    ):
        """ls_status を返す。"""
        return self._ls_status

    @property
    def mcc_status(
        self,
    ):
        """mcc_status を返す。"""
        return self._mcc_status

    @property
    def position(
        self,
    ):
        """position を返す。"""
        return self._position

    @classmethod
    def parse_all(
        cls,
        raw: str,
    ) -> Optional[List["MotorStatus"]]:
        """PM4C-06A互換の ``STS?`` 応答を解析する。"""
        if not isinstance(raw, str):
            return None

        text = raw.strip()
        # STS? 応答は "/" 区切りでヘッダ、方向、LS、MCC、各位置を返す。
        parts = text.split('/')
        if len(parts) < 5:
            return None

        header = parts[0]
        directions = parts[1]
        limits = parts[2]
        mcc = parts[3]
        positions = parts[4:]

        if len(header) < 2 or header[0] not in ('R', 'L'):
            return None

        motor_count = len(header) - 1

        if len(parts) != 4 + motor_count:
            return None

        if len(directions) != motor_count:
            return None

        for value in directions:
            if value not in 'PNS':
                return None

        if len(limits) != motor_count:
            return None

        if len(mcc) != motor_count * 2:
            return None

        # 16進表現のチャンネル・LS・MCCと、10進表現の位置を数値化する。
        try:
            channels = []
            for value in header[1:]:
                channels.append(int(value, 16))

            ls_values = []
            for value in limits:
                ls_values.append(int(value, 16))

            mcc_values = []
            for index in range(0, len(mcc), 2):
                mcc_values.append(int(mcc[index:index + 2], 16))

            position_values = []
            for value in positions:
                position_values.append(int(value, 10))
        except ValueError:
            return None

        # 応答ヘッダに含まれるチャンネル数だけ解析する。
        statuses = []
        for index in range(motor_count):
            status = cls(
                motor=index,
                channel=channels[index],
                raw=text,
                remote_local=header[0],
                direction=directions[index],
                ls_status=ls_values[index],
                mcc_status=mcc_values[index],
                position=position_values[index]
            )
            statuses.append(status)

        return statuses

    @property
    def motor_status(
        self,
    ) -> str:
        return f"{self._mcc_status:02X}"

    @property
    def is_busy(
        self,
    ) -> bool:
        return bool(self._mcc_status & 1)

    @property
    def is_driving(
        self,
    ) -> bool:
        return bool(self._mcc_status & 2)

    @property
    def is_accelerating(
        self,
    ) -> bool:
        return bool(self._mcc_status & 4)

    @property
    def is_decelerating(
        self,
    ) -> bool:
        return bool(self._mcc_status & 8)

    @property
    def has_command_error(
        self,
    ) -> bool:
        return bool(self._mcc_status & 16)

    @property
    def limit_stop_received(
        self,
    ) -> bool:
        return bool(self._mcc_status & 32)

    @property
    def slow_stop_received(
        self,
    ) -> bool:
        return bool(self._mcc_status & 64)

    @property
    def emergency_stop_received(
        self,
    ) -> bool:
        return bool(self._mcc_status & 128)

    @property
    def rotation_state(
        self,
    ) -> int:
        if self._direction in ('P', 'N'):
            return 1

        return 0

    @property
    def cw_ls(
        self,
    ) -> bool:
        return bool(self._ls_status & 1)

    @property
    def ccw_ls(
        self,
    ) -> bool:
        return bool(self._ls_status & 2)

    @property
    def hp_ls(
        self,
    ) -> bool:
        return bool(self._ls_status & 4)

    @property
    def hold_off(
        self,
    ) -> bool:
        return bool(self._ls_status & 8)

    @property
    def legacy_status_bits(
        self,
    ) -> int:
        # 現行LSビットを旧API互換のSVOC形式へ詰め直す。
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
            f"MotorStatus(motor={self._motor!r}, "
            f"channel={self._channel!r}, "
            f"remote_local={self._remote_local!r}, "
            f"direction={self._direction!r}, "
            f"ls_status=0x{self._ls_status:X}, "
            f"mcc_status=0x{self._mcc_status:02X}, "
            f"position={self._position!r})"
        )

def main() -> None:
    """MotorStatus の STS? 解析例を実行する。

    Returns:
        None。
    """
    # STS? の4枠応答形式を確認するための解析用サンプル。
    raw = "R0123/PNSN/0000/01020000/100/200/300/400"
    values = MotorStatus.parse_all(raw)

    if values is None:
        print(f'parse failed: {raw!r}')
        return

    for value in values:
        print(value)
        print(f"  motor={value.motor}")
        print(f"  channel={value.channel}")
        print(f"  busy={value.is_busy}")
        print(f"  driving={value.is_driving}")
        print(f"  direction={value.direction!r}")
        print(f"  position={value.position}")


if __name__ == '__main__':
    main()
