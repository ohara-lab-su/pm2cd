import re


class VersionInfo:
    """装置の ``VER?`` 応答を解析して保持する。

    想定形式は ``<version> <date> <model>``。日付の有無やモデル名中の
    空白は許容するが、空応答とバージョン番号を含まない応答は拒否する。
    """

    _VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)+$")
    _DATE_PATTERN = re.compile(r"^\d{2,4}[-/]\d{1,2}[-/]\d{1,2}$")

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")

        normalized = " ".join(raw.strip().split())
        if not normalized:
            raise ValueError("VER?応答が空です")

        parts = normalized.split(" ")
        if not self._VERSION_PATTERN.fullmatch(parts[0]):
            raise ValueError(f"VER?応答のバージョン形式が不正です: {raw!r}")

        self.raw = normalized
        self.version = parts[0]

        if len(parts) >= 2 and self._DATE_PATTERN.fullmatch(parts[1]):
            self.date = parts[1]
            self.model = " ".join(parts[2:])
        else:
            self.date = ""
            self.model = " ".join(parts[1:])

    # @property
    # def normalized_model(self) -> str:
    #     return re.sub(r"[^A-Z0-9]", "", self.model.upper())

    # @property
    # def is_pm16c16(self) -> bool:
    #     return self.normalized_model == "PM16C16"

    # @property
    # def is_pm2cd(self) -> bool:
    #     model = self.normalized_model
    #     return model in {"PM2CD", "PM2C06A", "PMCD06AX"}

    def __str__(self) -> str:
        return self.raw

    def __repr__(self) -> str:
        return (
            f"VersionInfo(version={self.version!r}, date={self.date!r}, "
            f"model={self.model!r})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self.raw == other.raw
