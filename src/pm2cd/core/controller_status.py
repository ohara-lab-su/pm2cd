from typing import Optional


class ControllerStatus:
    """``STQ?`` の REMOTE/LOCAL と停止可能数を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self.raw = ""
        self.remote_local = ""
        self.stopped_motor_count = 0
        self.is_valid = False

        if not isinstance(raw, str):
            return

        text = raw.strip().upper()
        if len(text) != 2 or text[0] not in ('R', 'L') or (not text[1].isdigit()):
            return

        count = int(text[1])
        if count < 0 or count > 4:
            return

        self.raw = text
        self.remote_local = text[0]
        self.stopped_motor_count = count
        self.is_valid = True

    @property
    def is_remote(
        self,
    ) -> bool:
        return self.is_valid and self.remote_local == "R"

    @property
    def can_start(
        self,
    ) -> bool:
        return self.is_valid and self.stopped_motor_count > 0

    def __repr__(
        self,
    ) -> str:
        return (
            f"ControllerStatus(raw={self.raw!r}, "
            f"stopped_motor_count={self.stopped_motor_count!r}, "
            f"is_valid={self.is_valid!r})"
        )

def main() -> None:
    """ControllerStatus の解析例を実行する。

    Returns:
        None。
    """
    raw = "R2"
    value = ControllerStatus(raw)

    print(f'raw={value.raw!r}')
    print(f'remote_local={value.remote_local!r}')
    print(f'stopped_motor_count={value.stopped_motor_count}')
    print(f'is_remote={value.is_remote}')
    print(f'can_start={value.can_start}')
    print(f'is_valid={value.is_valid}')


if __name__ == '__main__':
    main()
