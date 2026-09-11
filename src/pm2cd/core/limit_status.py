from typing import List, Optional


# HDSTLS? 応答を解析し、ハードウェアリミットとソフトウェアリミットの
# 現在状態を軸ごとに分離して保持する。

class LimitStatus:
    """``HDSTLS?`` 応答中の1軸分のリミット状態を保持する。"""

    def __init__(
        self,
        motor: int,
        channel: int,
        raw: str,
        hard_status: int,
        soft_status: int,
    ):
        self._motor = motor
        self._channel = channel
        self._raw = raw
        self._hard_status = hard_status
        self._soft_status = soft_status

    @property
    def motor(self) -> int:
        """モーター番号を返す。"""
        return self._motor

    @property
    def channel(self) -> int:
        """装置応答中のチャンネル番号を返す。"""
        return self._channel

    @classmethod
    def parse_all(
        cls,
        raw: str,
    ) -> Optional[List["LimitStatus"]]:
        """``HDSTLS?`` の ``abcdHHHHSSSS`` 応答を解析する。"""
        if not isinstance(raw, str):
            return None

        text = raw.strip()
        if len(text) != 12:
            return None

        channel_text = text[0:4]
        hard_text = text[4:8]
        soft_text = text[8:12]

        try:
            channels = [int(value, 16) for value in channel_text]
            hard_values = [int(value, 16) for value in hard_text]
            soft_values = [int(value, 16) for value in soft_text]
        except ValueError:
            return None

        values = []
        for index in range(4):
            # HARD は b0:CW, b1:CCW, b2:HP、SOFT は b0:CW, b1:CCW。
            if hard_values[index] & ~0x07:
                return None
            if soft_values[index] & ~0x03:
                return None

            values.append(
                cls(
                    motor=index,
                    channel=channels[index],
                    raw=text,
                    hard_status=hard_values[index],
                    soft_status=soft_values[index],
                )
            )

        return values

    @property
    def hard_cw(self) -> bool:
        return bool(self._hard_status & 0x01)

    @property
    def hard_ccw(self) -> bool:
        return bool(self._hard_status & 0x02)

    @property
    def hard_hp(self) -> bool:
        return bool(self._hard_status & 0x04)

    @property
    def soft_cw(self) -> bool:
        return bool(self._soft_status & 0x01)

    @property
    def soft_ccw(self) -> bool:
        return bool(self._soft_status & 0x02)

    @property
    def hard(self) -> List[bool]:
        """ハードウェアリミット状態を ``[CW, CCW, HP]`` で返す。"""
        return [self.hard_cw, self.hard_ccw, self.hard_hp]

    @property
    def soft(self) -> List[bool]:
        """ソフトウェアリミット状態を ``[CW, CCW]`` で返す。"""
        return [self.soft_cw, self.soft_ccw]

    def __repr__(self) -> str:
        return (
            f"LimitStatus(motor={self._motor!r}, "
            f"channel={self._channel!r}, "
            f"hard={self.hard!r}, soft={self.soft!r})"
        )
