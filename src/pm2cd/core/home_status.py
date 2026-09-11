# SETHP?x 応答を解析し、原点検出状態と検索方向を保持する。

class HomeStatus:
    """``SETHP?x`` の ``0XYZ`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self._raw = ""
        self._is_valid = False

        if not isinstance(raw, str):
            return

        # 0XYZ の4文字固定形式として応答を検証する。
        text = raw.strip()
        if len(text) != 4 or text[0] != '0':
            return

        # X/Y/Z はそれぞれ0または1のみを許可する。
        for value in text[1:]:
            if value not in ('0', '1'):
                return

        self._raw = text
        self._is_valid = True

    @property
    def raw(
        self,
    ):
        """raw を返す。"""
        return self._raw

    @property
    def is_valid(
        self,
    ):
        """is_valid を返す。"""
        return self._is_valid

    def found(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[1] != '1':
            return False
        return True

    @property
    def found_direction(
        self,
    ) -> str:
        if not self._is_valid:
            return ""

        if self._raw[2] == '0':
            return "cw"

        return "ccw"

    @property
    def auto_start_direction(
        self,
    ) -> str:
        if not self._is_valid:
            return ""

        if self._raw[3] == '0':
            return "cw"

        return "ccw"

    def __repr__(
        self,
    ) -> str:
        return f"HomeStatus(raw={self._raw!r}, is_valid={self._is_valid!r})"

def main() -> None:
    """HomeStatus の解析例を実行する。

    Returns:
        None。
    """
    raw = "0101"
    value = HomeStatus(raw)

    print(f'raw={value.raw!r}')
    print(f'found={value.found}')
    print(f'found_direction={value.found_direction!r}')
    print(f'auto_start_direction={value.auto_start_direction!r}')
    print(f'is_valid={value.is_valid}')


if __name__ == '__main__':
    main()
