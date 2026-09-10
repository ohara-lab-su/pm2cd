from typing import Optional


# SETLS?x 応答を解析し、各リミットスイッチの有効/無効と接点種別を保持する。

class LimitSwitchSetting:
    """``SETLS?x`` の ``DYYY0yyy`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self._raw = ""
        self._is_valid = False

        if not isinstance(raw, str):
            return

        # DYYY0yyy の8文字固定形式として応答を検証する。
        text = raw.strip()
        if len(text) != 8:
            return

        # 5文字目は仕様上の固定値0であることを確認する。
        if text[4] != '0':
            return

        for value in text:
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

    def digital_limit_enabled(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[0] != '1':
            return False
        return True

    @property
    def hp_enabled(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[1] != '1':
            return False
        return True

    @property
    def ccw_enabled(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[2] != '1':
            return False
        return True

    @property
    def cw_enabled(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[3] != '1':
            return False
        return True

    @property
    def hp_nc(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[5] != '1':
            return False
        return True

    @property
    def ccw_nc(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[6] != '1':
            return False
        return True

    @property
    def cw_nc(
        self,
    ) -> bool:
        if not self._is_valid:
            return False
        if self._raw[7] != '1':
            return False
        return True

    def with_digital_limit(
        self,
        enabled: bool,
    ) -> Optional[str]:
        if not isinstance(enabled, bool):
            return None

        if not self._is_valid:
            return None

        # 先頭ビットだけを書き換え、残りのLS設定は元の応答値を保持する。
        prefix = "0"
        if enabled:
            prefix = "1"

        return prefix + self._raw[1:]

    def __repr__(
        self,
    ) -> str:
        return (
            f'LimitSwitchSetting(raw={self._raw!r}, is_valid={self._is_valid!r})'
        )

def main() -> None:
    """LimitSwitchSetting の解析例を実行する。

    Returns:
        None。
    """
    raw = "11110111"
    value = LimitSwitchSetting(raw)

    print(f'raw={value.raw!r}')
    print(f'digital_limit_enabled={value.digital_limit_enabled}')
    print(f'hp_enabled={value.hp_enabled}')
    print(f'ccw_enabled={value.ccw_enabled}')
    print(f'cw_enabled={value.cw_enabled}')
    print(f'hp_nc={value.hp_nc}')
    print(f'ccw_nc={value.ccw_nc}')
    print(f'cw_nc={value.cw_nc}')
    print(f'is_valid={value.is_valid}')


if __name__ == '__main__':
    main()
