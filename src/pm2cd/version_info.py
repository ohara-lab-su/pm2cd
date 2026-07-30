from .core.errors import ProtocolError


class VersionInfo:
    """PMXC/PM2C系のバージョン応答を保持する。"""

    def __init__(self, raw: str):
        self.raw = raw
        self.model = self._extract_model(raw)

    @property
    def max_motor(self) -> int:
        if self.model.startswith("PM2"):
            return 2
        if self.model.startswith("PM3"):
            return 3
        if self.model.startswith("PM4") or self.model.startswith("PMXC"):
            return 4
        return 2

    @staticmethod
    def _extract_model(raw: str) -> str:
        for part in raw.split():
            if part.startswith(("PMXC", "PM2", "PM3", "PM4", "PMCD")):
                return part
        raise ProtocolError(f"バージョン応答を解析できません: {raw!r}")

    def __repr__(self) -> str:
        return f"VersionInfo(model={self.model!r}, max_motor={self.max_motor}, raw={self.raw!r})"
