# STOPMD?x 応答を解析し、パネル停止とリミット停止の停止モードを保持する。

class StopMode:
    """``STOPMD?x`` の ``AB`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self._raw = ""
        self._panel_fast = False
        self._limit_fast = False
        self._is_valid = False

        if not isinstance(raw, str):
            return

        # AB の2文字をパネル停止・リミット停止のモードとして解釈する。
        text = raw.strip()
        if len(text) != 2:
            return

        for value in text:
            if value not in ('0', '1'):
                return

        self._raw = text
        self._panel_fast = text[0] == "1"
        self._limit_fast = text[1] == "1"
        self._is_valid = True

    @property
    def raw(
        self,
    ):
        """raw を返す。"""
        return self._raw

    @property
    def panel_fast(
        self,
    ):
        """panel_fast を返す。"""
        return self._panel_fast

    @property
    def limit_fast(
        self,
    ):
        """limit_fast を返す。"""
        return self._limit_fast

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
            f'StopMode(raw={self._raw!r}, is_valid={self._is_valid!r})'
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
