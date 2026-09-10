from typing import Optional


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

        text = raw.strip()
        if len(text) != 8:
            return

        if text[4] != '0':
            return

        for value in text:
            if value not in ('0', '1'):
                return

        self._raw = text
        self._is_valid = True

    @property
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
        return self._is_valid and self._raw[0] == "1"

    @property
    def hp_enabled(
        self,
    ) -> bool:
        return self._is_valid and self._raw[1] == "1"

    @property
    def ccw_enabled(
        self,
    ) -> bool:
        return self._is_valid and self._raw[2] == "1"

    @property
    def cw_enabled(
        self,
    ) -> bool:
        return self._is_valid and self._raw[3] == "1"

    @property
    def hp_nc(
        self,
    ) -> bool:
        return self._is_valid and self._raw[5] == "1"

    @property
    def ccw_nc(
        self,
    ) -> bool:
        return self._is_valid and self._raw[6] == "1"

    @property
    def cw_nc(
        self,
    ) -> bool:
        return self._is_valid and self._raw[7] == "1"

    def with_digital_limit(
        self,
        enabled: bool,
    ) -> Optional[str]:
        if not isinstance(enabled, bool):
            return None

        if not self._is_valid:
            return None

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
