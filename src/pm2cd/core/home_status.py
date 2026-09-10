class HomeStatus:
    """``SETHP?x`` の ``0XYZ`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self.raw = ""
        self.is_valid = False

        if not isinstance(raw, str):
            return

        text = raw.strip()
        if len(text) != 4 or text[0] != '0':
            return

        for value in text[1:]:
            if value not in ('0', '1'):
                return

        self.raw = text
        self.is_valid = True

    @property
    def found(
        self,
    ) -> bool:
        return self.is_valid and self.raw[1] == "1"

    @property
    def found_direction(
        self,
    ) -> str:
        if not self.is_valid:
            return ""

        if self.raw[2] == '0':
            return "cw"

        return "ccw"

    @property
    def auto_start_direction(
        self,
    ) -> str:
        if not self.is_valid:
            return ""

        if self.raw[3] == '0':
            return "cw"

        return "ccw"

    def __repr__(
        self,
    ) -> str:
        return f"HomeStatus(raw={self.raw!r}, is_valid={self.is_valid!r})"

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
