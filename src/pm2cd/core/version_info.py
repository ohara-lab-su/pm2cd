import re


class VersionInfo:
    """``VER?`` 応答を解析して保持する。"""

    _VERSION_PATTERN = re.compile('^\\d+(?:\\.\\d+)+$')
    _DATE_PATTERN = re.compile('^\\d{2,4}[-/]\\d{1,2}[-/]\\d{1,2}$')

    def __init__(
        self,
        raw: str,
    ):
        self._raw = ""
        self._version = ""
        self._date = ""
        self._model = ""
        self._is_valid = False

        if not isinstance(raw, str):
            return

        normalized = ' '.join(raw.strip().split())
        if not normalized:
            return

        parts = normalized.split(' ')
        if not self._VERSION_PATTERN.fullmatch(parts[0]):
            return

        self._raw = normalized
        self._version = parts[0]

        if len(parts) >= 2 and self._DATE_PATTERN.fullmatch(parts[1]):
            self._date = parts[1]
            self._model = ' '.join(parts[2:])
        else:
            self._model = ' '.join(parts[1:])

        self._is_valid = True

    @property
    @property
    def raw(
        self,
    ):
        """raw を返す。"""
        return self._raw

    @property
    def version(
        self,
    ):
        """version を返す。"""
        return self._version

    @property
    def date(
        self,
    ):
        """date を返す。"""
        return self._date

    @property
    def model(
        self,
    ):
        """model を返す。"""
        return self._model

    @property
    def is_valid(
        self,
    ):
        """is_valid を返す。"""
        return self._is_valid

    def normalized_model(
        self,
    ) -> str:
        return re.sub('[^A-Z0-9]', '', self._model.upper())

    @property
    def is_pm2cd(
        self,
    ) -> bool:
        return (
            self._is_valid and self.normalized_model in {'PMXC06A', 'PM2C06A', 'PM2CD'}
        )

    def __str__(
        self,
    ) -> str:
        return self._raw

    def __repr__(
        self,
    ) -> str:
        return (
            f"VersionInfo(version={self._version!r}, "
            f"date={self._date!r}, model={self._model!r}, "
            f"is_valid={self._is_valid!r})"
        )

def main() -> None:
    """VersionInfo の解析例を実行する。

    Returns:
        None。
    """
    raw = "2.00 19-02-14 PMXC-06A"
    value = VersionInfo(raw)

    print(f'raw={value.raw!r}')
    print(f'version={value.version!r}')
    print(f'date={value.date!r}')
    print(f'model={value.model!r}')
    print(f'normalized_model={value.normalized_model!r}')
    print(f'is_pm2cd={value.is_pm2cd}')
    print(f'is_valid={value.is_valid}')


if __name__ == '__main__':
    main()
