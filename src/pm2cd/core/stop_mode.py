class StopMode:
    """``STOPMD?x`` の ``AB`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self.raw = ""
        self.panel_fast = False
        self.limit_fast = False
        self.is_valid = False

        if not isinstance(raw, str):
            return

        text = raw.strip()
        if len(text) != 2:
            return

        for value in text:
            if value not in ('0', '1'):
                return

        self.raw = text
        self.panel_fast = text[0] == "1"
        self.limit_fast = text[1] == "1"
        self.is_valid = True

    def __repr__(
        self,
    ) -> str:
        return (
            f'StopMode(raw={self.raw!r}, is_valid={self.is_valid!r})'
        )

def main() -> None:
    """StopMode の解析例を実行する。

    Returns:
        None。
    """
    raw = "10"
    value = StopMode(raw)

    print(f'raw={value.raw!r}')
    print(f'panel_fast={value.panel_fast}')
    print(f'limit_fast={value.limit_fast}')
    print(f'is_valid={value.is_valid}')


if __name__ == '__main__':
    main()
