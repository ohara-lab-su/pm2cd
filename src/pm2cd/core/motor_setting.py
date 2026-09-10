class MotorSetting:
    """``SETMT?x`` の ``ABCD`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self._raw = ""
        self._drive_enabled = False
        self._hold_mode = 0
        self._drive_mode = 0
        self._output_mode = 0
        self._is_valid = False

        if not isinstance(raw, str):
            return

        text = raw.strip()
        if len(text) != 4:
            return

        if text[0] not in ('0', '1'):
            return

        if text[1] not in ('0', '1', '2', '3'):
            return

        if text[2] != '1':
            return

        if text[3] not in ('0', '1', '2'):
            return

        self._raw = text
        self._drive_enabled = text[0] == "1"
        self._hold_mode = int(text[1])
        self._drive_mode = int(text[2])
        self._output_mode = int(text[3])
        self._is_valid = True

    @property
    def raw(
        self,
    ):
        """raw を返す。"""
        return self._raw

    @property
    def drive_enabled(
        self,
    ):
        """drive_enabled を返す。"""
        return self._drive_enabled

    @property
    def hold_mode(
        self,
    ):
        """hold_mode を返す。"""
        return self._hold_mode

    @property
    def drive_mode(
        self,
    ):
        """drive_mode を返す。"""
        return self._drive_mode

    @property
    def output_mode(
        self,
    ):
        """output_mode を返す。"""
        return self._output_mode

    @property
    def is_valid(
        self,
    ):
        """is_valid を返す。"""
        return self._is_valid

    def __repr__(
        self,
    ) -> str:
        return (
            f'MotorSetting(raw={self._raw!r}, is_valid={self._is_valid!r})'
        )

def main() -> None:
    """MotorSetting の解析例を実行する。

    Returns:
        None。
    """
    raw = "1110"
    value = MotorSetting(raw)

    print(f'raw={value.raw!r}')
    print(f'drive_enabled={value.drive_enabled}')
    print(f'hold_mode={value.hold_mode}')
    print(f'drive_mode={value.drive_mode}')
    print(f'output_mode={value.output_mode}')
    print(f'is_valid={value.is_valid}')


if __name__ == '__main__':
    main()
