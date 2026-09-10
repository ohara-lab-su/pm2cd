class MotorSetting:
    """``SETMT?x`` の ``ABCD`` 応答を保持する。"""

    def __init__(
        self,
        raw: str,
    ):
        self.raw = ""
        self.drive_enabled = False
        self.hold_mode = 0
        self.drive_mode = 0
        self.output_mode = 0
        self.is_valid = False

        if not isinstance(
            raw,
            str
        ):
            return

        text = raw.strip()
        if len(text) != 4:
            return

        if text[0] not in ("0", "1",):
            return

        if text[1] not in ("0", "1", "2", "3",):
            return

        if text[2] != "1":
            return

        if text[3] not in ("0", "1", "2",):
            return

        self.raw = text
        self.drive_enabled = text[0] == "1"
        self.hold_mode = int(
            text[1]
        )
        self.drive_mode = int(
            text[2]
        )
        self.output_mode = int(
            text[3]
        )
        self.is_valid = True

    def __repr__(
        self,
    ) -> str:
        return (
            f"MotorSetting(raw={self.raw!r}, "
            f"is_valid={self.is_valid!r})"
        )

def main(
) -> None:
    """MotorSetting の解析例を実行する。

    Returns:
        None。
    """
    raw = "1110"
    value = MotorSetting(
        raw
    )

    print(f"raw={value.raw!r}")
    print(f"drive_enabled={value.drive_enabled}")
    print(f"hold_mode={value.hold_mode}")
    print(f"drive_mode={value.drive_mode}")
    print(f"output_mode={value.output_mode}")
    print(f"is_valid={value.is_valid}")


if __name__ == "__main__":
    main()
