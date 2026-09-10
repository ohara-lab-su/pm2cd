import re

from .errors import ProtocolError


class VersionInfo:
    """``VER?`` 応答を解析して保持する。"""

    _VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)+$")
    _DATE_PATTERN = re.compile(r"^\d{2,4}[-/]\d{1,2}[-/]\d{1,2}$")

    def __init__(self, raw: str):
        if not isinstance(raw, str):
            raise TypeError("rawはstrで指定してください")

        normalized = " ".join(raw.strip().split())
        if not normalized:
            raise ProtocolError("VER?応答が空です")

        parts = normalized.split(" ")
        if not self._VERSION_PATTERN.fullmatch(parts[0]):
            raise ProtocolError("VER?応答のバージョン形式が不正です: {!r}".format(raw))

        self.raw = normalized
        self.version = parts[0]
        self.date = ""
        self.model = ""

        if len(parts) >= 2 and self._DATE_PATTERN.fullmatch(parts[1]):
            self.date = parts[1]
            self.model = " ".join(parts[2:])
        else:
            self.model = " ".join(parts[1:])

    @property
    def normalized_model(self) -> str:
        return re.sub(r"[^A-Z0-9]", "", self.model.upper())

    @property
    def is_pm2cd(self) -> bool:
        return self.normalized_model in {"PMXC06A", "PM2C06A", "PM2CD"}

    def __str__(self) -> str:
        return self.raw

    def __repr__(self) -> str:
        return "VersionInfo(version={!r}, date={!r}, model={!r})".format(
            self.version,
            self.date,
            self.model,
        )
