import logging
from typing import List, Optional, Union

from .core.communication_tcp import Communication
from .core.controller_status import ControllerStatus
from .core.data import RATE_TABLE
from .core.home_status import HomeStatus
from .core.limit_switch_setting import LimitSwitchSetting
from .core.motor_setting import MotorSetting
from .core.motor_status import MotorStatus
from .core.stop_mode import StopMode
from .core.version_info import VersionInfo


class PM2CDDevice:
    """PM2CD / PM2C-06A 固有のコマンド生成・応答処理を担当する。"""

    CHANNEL_COUNT = 2
    POSITION_MIN = -8_388_608
    POSITION_MAX = 8_388_607
    SPEED_MIN = 5
    SPEED_MAX = 100_000
    BACKLASH_MIN = -9_999
    BACKLASH_MAX = 9_999
    RATE_MIN = 0
    RATE_MAX = 25
    JOG_PULSE_MIN = 0
    JOG_PULSE_MAX = 9_999
    HOME_OFFSET_MIN = 0
    HOME_OFFSET_MAX = 9_999
    HOLD_TIME_MIN = 50
    HOLD_TIME_MAX = 3_000
    HOLD_TIME_STEP = 10

    def __init__(
        self,
        communication: Communication,
        channel_count: int = 2,
        logger=None,
        log_level: str = "INFO",
    ):
        """インスタンスを初期化する。

        Args:
            communication: PM2CD と接続する Communication インスタンス。
            channel_count: 制御対象チャンネル数。PM2CD では 2 固定。
            logger: 使用する logger。None の場合はこのモジュールで生成する。
            log_level: logger を生成する場合のログレベル。

        Raises:
            ValueError: PM2CD 固有の固定条件に反する設定が指定された場合。
        """
        if not logger:
            logging.basicConfig(level=(log_level or "INFO").upper())
            logger = logging.getLogger(__name__)

        self._logger = logger
        self._communication = communication
        if channel_count != self.CHANNEL_COUNT:
            raise ValueError(f"PM2CDのchannel_countは2です: {channel_count}")

        self._version_info = None  # type: Optional[VersionInfo]

    def remote(
        self,
    ) -> bool:
        """装置をリモート操作モードへ切り替える。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== remote()")
        return self._communication.send("REM")

    def local(
        self,
    ) -> bool:
        """装置をローカル操作モードへ切り替える。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== local()")
        return self._communication.send("LOC")

    def version(
        self,
    ) -> Optional[VersionInfo]:
        """装置のソフトウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== version()")

        raw = self._communication.query("VER?")
        if raw is None:
            return None

        value = VersionInfo(raw)
        if not value.is_valid:
            self._logger.error(f"VER?応答を解釈できません: {raw!r}")
            return None

        self._version_info = value
        return value

    def hardware_version(
        self,
    ) -> Optional[str]:
        """装置のハードウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== hardware_version()")

        raw = self._query_text("VERH?")
        if raw is None:
            return None

        if not raw.startswith("HD-VER"):
            self._logger.error(f"VERH?応答を解釈できません: {raw!r}")
            return None

        return raw

    def controller_status(
        self,
    ) -> Optional[ControllerStatus]:
        """コントローラー全体の状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== controller_status()")

        raw = self._communication.query("STQ?")
        if raw is None:
            return None

        value = ControllerStatus(raw)
        if not value.is_valid:
            self._logger.error(f"STQ?応答を解釈できません: {raw!r}")
            return None

        return value

    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> bool:
        """指定モーターを絶対位置へ移動する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== move()")

        if not self._check_motor(motor):
            return False

        if not self._check_position(pulse, "pulse"):
            return False

        suffix = self._backlash_suffix(backlash)
        if suffix is None:
            return False

        command = f"ABS{self._motor_text(motor)}" f"{suffix}{pulse:d}"
        return self._communication.send(command)

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> bool:
        """指定モーターを現在位置から相対移動する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== move_relative()")

        if not self._check_motor(motor):
            return False

        if not self._check_position(pulse, "pulse"):
            return False

        suffix = self._backlash_suffix(backlash)
        if suffix is None:
            return False

        command = f"REL{self._motor_text(motor)}" f"{suffix}{pulse:d}"
        return self._communication.send(command)

    def scan(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ連続スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== scan()")

        normalized = self._normalize_direction(direction)
        if normalized is None:
            return False

        command = "SCANN"
        if normalized == "cw":
            command = "SCANP"

        return self._send_motor_command(command, motor)

    def constant_speed_scan(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ定速スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== constant_speed_scan()")

        normalized = self._normalize_direction(direction)
        if normalized is None:
            return False

        command = "CSCANN"
        if normalized == "cw":
            command = "CSCANP"

        return self._send_motor_command(command, motor)

    def jog(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ JOG 動作する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== jog()")

        normalized = self._normalize_direction(direction)
        if normalized is None:
            return False

        command = "JOGN"
        if normalized == "cw":
            command = "JOGP"

        return self._send_motor_command(command, motor)

    def scan_home(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ原点探索スキャンを開始する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== scan_home()")

        normalized = self._normalize_direction(direction)
        if normalized is None:
            return False

        command = "SCANHN"
        if normalized == "cw":
            command = "SCANHP"

        return self._send_motor_command(command, motor)

    def home(
        self,
        motor: int,
    ) -> bool:
        """記録済み原点位置へ移動する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== home()")
        return self._send_motor_command("GTHP", motor)

    def find_home(
        self,
        motor: int,
    ) -> bool:
        """原点検出動作を開始する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== find_home()")
        return self._send_motor_command("FDHP", motor)

    def stop(
        self,
        motor: int,
    ) -> bool:
        """指定モーターを停止する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== stop()")
        return self._send_motor_command("SSTP", motor)

    def stop_all(
        self,
    ) -> bool:
        """全モーターを停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== stop_all()")
        return self._communication.send("ASSTP")

    def emergency_stop(
        self,
        motor: int,
    ) -> bool:
        """指定モーターを非常停止する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== emergency_stop()")
        return self._send_motor_command("ESTP", motor)

    def emergency_stop_all(
        self,
    ) -> bool:
        """全モーターを非常停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== emergency_stop_all()")
        return self._communication.send("AESTP")

    def status(
        self,
        motor: int,
    ) -> Optional[MotorStatus]:
        """指定モーターの状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== status()")

        if not self._check_motor(motor):
            return None

        # STS? は全モーター分をまとめて返すため、一度だけ取得して対象 motor を選ぶ。
        values = self.status_all()
        if values is None:
            return None

        return values[motor]

    def status_all(
        self,
    ) -> Optional[List[MotorStatus]]:
        """全モーターの状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== status_all()")

        raw = self._communication.query("STS?")
        if raw is None:
            return None

        values = MotorStatus.parse_all(raw)
        if values is None:
            self._logger.error(f"STS?応答を解釈できません: {raw!r}")
            return None

        return values[: self.CHANNEL_COUNT]

    def check_rotate(
        self,
        motor: int,
    ) -> Optional[bool]:
        """指定モーターが回転中か確認する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== check_rotate()")

        status = self.status(motor)
        if status is None:
            return None

        return status.rotation_state == 1

    def position(
        self,
        motor: int,
    ) -> Optional[int]:
        """指定モーターの現在位置を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== position()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        return self._query_int(f"PS?{motor_text}", "PS?")

    def set_position(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """指定モーターの現在位置カウンタを設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_position()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_position(pulse, "pulse"):
            return False

        return self._communication.send(f"PS{motor_text}{pulse:d}")

    def set_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """高速値を基準に低速・中速・高速を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_speed()")

        if not self._check_motor(motor):
            return False

        if not self._check_speed(speed):
            return False

        # PM16 系既存実装と同じ比率で、中速を高速の 1/3 から求める。
        middle = speed // 3
        if middle < self.SPEED_MIN:
            middle = self.SPEED_MIN

        # 低速は高速の 1/10 とし、装置仕様の最低速度を下回らせない。
        low = speed // 10
        if low < self.SPEED_MIN:
            low = self.SPEED_MIN

        if not self.set_high_speed(motor, speed):
            return False

        if not self.set_middle_speed(motor, middle):
            return False

        return self.set_low_speed(motor, low)

    def set_speed_profile(
        self,
        motor: int,
        low_speed: int,
        middle_speed: int,
        high_speed: int,
    ) -> bool:
        """低速・中速・高速を個別に設定する。

        Args:
            motor: モーター番号。0 または 1。
            low_speed: 低速値。
            middle_speed: 中速値。
            high_speed: 高速値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_speed_profile()")

        if not self._check_motor(motor):
            return False

        if not self._check_speed(low_speed):
            return False

        if not self._check_speed(middle_speed):
            return False

        if not self._check_speed(high_speed):
            return False

        if not self.set_low_speed(motor, low_speed):
            return False

        if not self.set_middle_speed(motor, middle_speed):
            return False

        return self.set_high_speed(motor, high_speed)

    def high_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== high_speed()")
        return self._query_motor_int("SPDH?", motor)

    def set_high_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """高速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_high_speed()")
        return self._set_speed_value("SPDH", motor, speed)

    def middle_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """中速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== middle_speed()")
        return self._query_motor_int("SPDM?", motor)

    def set_middle_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """中速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_middle_speed()")
        return self._set_speed_value("SPDM", motor, speed)

    def low_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """低速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== low_speed()")
        return self._query_motor_int("SPDL?", motor)

    def set_low_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """低速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_low_speed()")
        return self._set_speed_value("SPDL", motor, speed)

    def speed_mode(
        self,
        motor: int,
    ) -> Optional[str]:
        """現在の速度モードを取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== speed_mode()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        raw = self._query_text(f"SPD?{motor_text}")
        if raw is None:
            return None

        if raw not in (
            "HSPD",
            "MSPD",
            "LSPD",
        ):
            self._logger.error(f"SPD?応答を解釈できません: {raw!r}")
            return None

        return raw

    def set_speed_mode(
        self,
        motor: int,
        mode: Union[int, str],
    ) -> bool:
        """速度モードを設定する。

        Args:
            motor: モーター番号。0 または 1。
            mode: 速度モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_speed_mode()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        normalized = self._normalize_speed_mode(mode)
        if normalized is None:
            return False

        return self._communication.send(f"SPD{normalized}{motor_text}")

    def rate_number(
        self,
        motor: int,
    ) -> Optional[int]:
        """加減速レート番号を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== rate_number()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        value = self._query_int(f"RTE?{motor_text}", "RTE?")
        if value is None:
            return None

        if value < self.RATE_MIN or value > self.RATE_MAX:
            self._logger.error(f"RTE?応答が範囲外です: {value}")
            return None

        return value

    def set_rate_number(
        self,
        motor: int,
        number: int,
    ) -> bool:
        """加減速レート番号を設定する。

        Args:
            motor: モーター番号。0 または 1。
            number: レート番号。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_rate_number()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_int(number, "number"):
            return False

        if number < self.RATE_MIN or number > self.RATE_MAX:
            self._logger.error(f"numberは0から25の範囲で指定してください")
            return False

        return self._communication.send(f"RTE{motor_text}{number:03d}")

    def backlash(
        self,
        motor: int,
    ) -> Optional[int]:
        """バックラッシュ補正量を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== backlash()")
        return self._query_motor_int("B?", motor)

    def set_backlash(
        self,
        motor: int,
        backlash: int,
    ) -> bool:
        """バックラッシュ補正量を設定する。

        Args:
            motor: モーター番号。0 または 1。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_backlash()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_int(backlash, "backlash"):
            return False

        if backlash < self.BACKLASH_MIN or backlash > self.BACKLASH_MAX:
            self._logger.error(f"backlashは-9999から9999の範囲で指定してください")
            return False

        return self._communication.send(f"B{motor_text}{backlash:d}")

    def limit(
        self,
        motor: int,
        side: str,
    ) -> Optional[int]:
        """指定側のソフトウェアリミット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。
            side: リミット側。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== limit()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        normalized = self._normalize_side(side)
        if normalized is None:
            return None

        command = "BL?"
        if normalized == "cw":
            command = "FL?"

        return self._query_int(f"{command}{motor_text}", command)

    def set_limit(
        self,
        motor: int,
        side: str,
        pulse: int,
    ) -> bool:
        """指定側のソフトウェアリミット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。
            side: リミット側。cw または ccw。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_limit()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_position(pulse, "pulse"):
            return False

        normalized = self._normalize_side(side)
        if normalized is None:
            return False

        # ソフトウェアリミットを設定する前に SETLS を読み、デジタルリミットが
        # 無効なら既存設定を保持したまま有効化する。
        setting = self.limit_switch_setting(motor)
        if setting is None:
            return False

        if not setting.digital_limit_enabled:
            changed = setting.with_digital_limit(True)
            if changed is None:
                return False

            if not self.set_limit_switch_setting_raw(motor, changed):
                return False

        command = "BL"
        if normalized == "cw":
            command = "FL"

        return self._communication.send(f"{command}{motor_text}{pulse:d}")

    def pause(
        self,
    ) -> bool:
        """動作を一時停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== pause()")
        return self._communication.send("PAUSE ON")

    def resume(
        self,
    ) -> bool:
        """一時停止を解除する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== resume()")
        return self._communication.send("PAUSE OFF")

    def pause_status(
        self,
    ) -> Optional[str]:
        """一時停止状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== pause_status()")
        return self._query_on_off("PAUSE?")

    def hold(
        self,
        motor: int,
    ) -> Optional[str]:
        """指定モーターの HOLD 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== hold()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        return self._query_on_off(f"HOLD?{motor_text}")

    def set_hold(
        self,
        motor: int,
        enabled: bool,
    ) -> bool:
        """指定モーターの HOLD 状態を設定する。

        Args:
            motor: モーター番号。0 または 1。
            enabled: 有効にする場合は True、無効にする場合は False。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_hold()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not isinstance(enabled, bool):
            self._logger.error(f"enabledはboolで指定してください")
            return False

        mode = "OFF"
        if enabled:
            mode = "ON"

        return self._communication.send(f"HOLD{motor_text}{mode}")

    def hold_on_time(
        self,
        motor: int,
    ) -> Optional[int]:
        """HOLD ON 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== hold_on_time()")
        return self._query_motor_msec("H_ONTM?", motor)

    def set_hold_on_time(
        self,
        motor: int,
        msec: int,
    ) -> bool:
        """HOLD ON 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_hold_on_time()")
        return self._set_hold_time("H_ONTM", motor, msec)

    def hold_off_time(
        self,
        motor: int,
    ) -> Optional[int]:
        """HOLD OFF 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== hold_off_time()")
        return self._query_motor_msec("H_OFTM?", motor)

    def set_hold_off_time(
        self,
        motor: int,
        msec: int,
    ) -> bool:
        """HOLD OFF 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_hold_off_time()")
        return self._set_hold_time("H_OFTM", motor, msec)

    def home_status(
        self,
        motor: int,
    ) -> Optional[HomeStatus]:
        """原点検出設定状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== home_status()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        raw = self._communication.query(f"SETHP?{motor_text}")
        if raw is None:
            return None

        value = HomeStatus(raw)
        if not value.is_valid:
            self._logger.error(f"SETHP?応答を解釈できません: {raw!r}")
            return None

        return value

    def set_home_status(
        self,
        motor: int,
        found: bool,
        found_direction: str,
        auto_start_direction: str,
    ) -> bool:
        """原点検出設定状態を設定する。

        Args:
            motor: モーター番号。0 または 1。
            found: 原点検出済み状態。
            found_direction: 原点検出方向。
            auto_start_direction: 自動原点検出開始方向。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_home_status()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        found_value = self._bool_digit(found, "found")
        if found_value is None:
            return False

        found_dir = self._direction_digit(found_direction)
        if found_dir is None:
            return False

        auto_dir = self._direction_digit(auto_start_direction)
        if auto_dir is None:
            return False

        command = f"SETHP{motor_text}0" f"{found_value}{found_dir}{auto_dir}"
        return self._communication.send(command)

    def home_position(
        self,
        motor: int,
    ) -> Optional[int]:
        """記録済み原点位置を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== home_position()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        raw = self._query_text(f"SHP?{motor_text}")
        if raw is None:
            return None

        if raw == "NO H.P":
            return None

        return self._parse_int(raw, "SHP?")

    def set_home_position(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """原点位置を設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_home_position()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_position(pulse, "pulse"):
            return False

        return self._communication.send(f"SHP{motor_text}{pulse:d}")

    def home_offset(
        self,
        motor: int,
    ) -> Optional[int]:
        """原点オフセットを取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== home_offset()")
        return self._query_motor_int("SHPF?", motor)

    def set_home_offset(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """原点オフセットを設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_home_offset()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_int(pulse, "pulse"):
            return False

        if pulse < self.HOME_OFFSET_MIN or pulse > self.HOME_OFFSET_MAX:
            self._logger.error(f"pulseは0から9999の範囲で指定してください")
            return False

        return self._communication.send(f"SHPF{motor_text}{pulse:d}")

    def preset_position(
        self,
        motor: int,
    ) -> Optional[int]:
        """プリセット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== preset_position()")
        return self._query_motor_int("SPRS?", motor)

    def set_preset_position(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """プリセット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_preset_position()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_position(pulse, "pulse"):
            return False

        return self._communication.send(f"SPRS{motor_text}{pulse:d}")

    def jog_pulse(
        self,
        motor: int,
    ) -> Optional[int]:
        """JOG パルス数を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== jog_pulse()")
        return self._query_motor_int("SETJG?", motor)

    def set_jog_pulse(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """JOG パルス数を設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_jog_pulse()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_int(pulse, "pulse"):
            return False

        if pulse < self.JOG_PULSE_MIN or pulse > self.JOG_PULSE_MAX:
            self._logger.error(f"pulseは0から9999の範囲で指定してください")
            return False

        return self._communication.send(f"SETJG{motor_text}{pulse:04d}")

    def limit_switch_setting(
        self,
        motor: int,
    ) -> Optional[LimitSwitchSetting]:
        """リミットスイッチ設定を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== limit_switch_setting()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        raw = self._communication.query(f"SETLS?{motor_text}")
        if raw is None:
            return None

        value = LimitSwitchSetting(raw)
        if not value.is_valid:
            self._logger.error(f"SETLS?応答を解釈できません: {raw!r}")
            return None

        return value

    def set_limit_switch_setting_raw(
        self,
        motor: int,
        setting: str,
    ) -> bool:
        """リミットスイッチ設定を生の設定文字列で書き込む。

        Args:
            motor: モーター番号。0 または 1。
            setting: 装置へ設定する生の設定文字列。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_limit_switch_setting_raw()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        parsed = LimitSwitchSetting(setting)
        if not parsed.is_valid:
            self._logger.error(f"SETLS設定値を解釈できません: {setting!r}")
            return False

        return self._communication.send(f"SETLS{motor_text}{parsed.raw}")

    def motor_setting(
        self,
        motor: int,
    ) -> Optional[MotorSetting]:
        """モーター設定を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== motor_setting()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        raw = self._communication.query(f"SETMT?{motor_text}")
        if raw is None:
            return None

        value = MotorSetting(raw)
        if not value.is_valid:
            self._logger.error(f"SETMT?応答を解釈できません: {raw!r}")
            return None

        return value

    def set_motor_setting(
        self,
        motor: int,
        drive_enabled: bool,
        hold_mode: int,
        output_mode: int,
    ) -> bool:
        """モーター設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。
            drive_enabled: モータードライブを有効にする場合は True。
            hold_mode: ホールドモード。
            output_mode: 出力モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_motor_setting()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        drive = self._bool_digit(drive_enabled, "drive_enabled")
        if drive is None:
            return False

        if not self._check_int(hold_mode, "hold_mode"):
            return False

        if not self._check_int(output_mode, "output_mode"):
            return False

        if hold_mode < 0 or hold_mode > 3:
            self._logger.error(f"hold_modeは0から3の範囲で指定してください")
            return False

        if output_mode < 0 or output_mode > 2:
            self._logger.error(f"output_modeは0から2の範囲で指定してください")
            return False

        return self._communication.send(
            f"SETMT{motor_text}{drive}{hold_mode}1{output_mode}"
        )

    def stop_mode(
        self,
        motor: int,
    ) -> Optional[StopMode]:
        """停止モード設定を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        self._logger.info(f"== stop_mode()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        raw = self._communication.query(f"STOPMD?{motor_text}")
        if raw is None:
            return None

        value = StopMode(raw)
        if not value.is_valid:
            self._logger.error(f"STOPMD?応答を解釈できません: {raw!r}")
            return None

        return value

    def set_stop_mode(
        self,
        motor: int,
        panel_fast: bool,
        limit_fast: bool,
    ) -> bool:
        """停止モード設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。
            panel_fast: パネル停止を高速停止にする場合は True。
            limit_fast: リミット停止を高速停止にする場合は True。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        self._logger.info(f"== set_stop_mode()")

        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        panel = self._bool_digit(panel_fast, "panel_fast")
        if panel is None:
            return False

        limit_value = self._bool_digit(limit_fast, "limit_fast")
        if limit_value is None:
            return False

        return self._communication.send(f"STOPMD{motor_text}{panel}{limit_value}")

    @staticmethod
    def number_to_rate(
        index: int,
    ) -> float:
        """レート番号を RATE_TABLE のレート値へ変換する。

        Args:
            index: RATE_TABLE のインデックス。

        Returns:
            float 型の結果。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 変換可能な範囲外の場合。
        """
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("indexはintで指定してください")

        if index < 0 or index >= len(RATE_TABLE):
            raise ValueError("レート番号は0から25の範囲で指定してください")

        return RATE_TABLE[index]

    @staticmethod
    def rate_to_number(
        rate: float,
    ) -> int:
        """レート値を対応する RATE_TABLE の番号へ変換する。

        Args:
            rate: 変換するレート値。

        Returns:
            int 型の結果。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 変換可能な範囲外の場合。
        """
        if not isinstance(
            rate,
            (
                int,
                float,
            ),
        ) or isinstance(rate, bool):
            raise TypeError("rateは数値で指定してください")

        target = abs(float(rate))
        for number, table_rate in enumerate(RATE_TABLE):
            if target >= table_rate:
                return number

        raise ValueError("rateがRATE TABLEの範囲外です")

    def _send_motor_command(
        self,
        command: str,
        motor: int,
    ) -> bool:
        """モーター番号を付加した単純コマンドを送信する。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        return self._communication.send(f"{command}{motor_text}")

    def _set_speed_value(
        self,
        command: str,
        motor: int,
        speed: int,
    ) -> bool:
        """速度値を検証して速度設定コマンドを送信する。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_speed(speed):
            return False

        return self._communication.send(f"{command}{motor_text}{speed:d}")

    def _set_hold_time(
        self,
        command: str,
        motor: int,
        msec: int,
    ) -> bool:
        """HOLD 時間を検証して設定コマンドを送信する。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。
            motor: モーター番号。0 または 1。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor_text = self._motor_text(motor)
        if motor_text is None:
            return False

        if not self._check_int(msec, "msec"):
            return False

        if msec < self.HOLD_TIME_MIN or msec > self.HOLD_TIME_MAX:
            self._logger.error(f"msecは50から3000の範囲で指定してください")
            return False

        if msec % self.HOLD_TIME_STEP != 0:
            self._logger.error(f"msecは10刻みで指定してください")
            return False

        return self._communication.send(f"{command}{motor_text}{msec:d}")

    def _query_motor_int(
        self,
        command: str,
        motor: int,
    ) -> Optional[int]:
        """モーター別問い合わせを行い整数応答を返す。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        return self._query_int(f"{command}{motor_text}", command)

    def _query_motor_msec(
        self,
        command: str,
        motor: int,
    ) -> Optional[int]:
        """モーター別問い合わせを行い時間応答を返す。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor_text = self._motor_text(motor)
        if motor_text is None:
            return None

        return self._query_msec(f"{command}{motor_text}")

    def _query_msec(
        self,
        command: str,
    ) -> Optional[int]:
        """時間表記を含む応答を整数の ms 値へ変換する。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        raw = self._query_text(command)
        if raw is None:
            return None

        # 装置応答はファームウェア差で単位表記を含むため、数値化前に単位だけ除去する。
        normalized = raw.lower().replace("msec.", "").replace("ms", "").strip()
        return self._parse_int(normalized, command)

    def _query_int(
        self,
        command: str,
        name: str,
    ) -> Optional[int]:
        """問い合わせ応答を整数へ変換する。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。
            name: ログに表示する値または応答の名称。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        raw = self._query_text(command)
        if raw is None:
            return None

        return self._parse_int(raw, name)

    def _parse_int(
        self,
        raw: str,
        name: str,
    ) -> Optional[int]:
        """応答文字列を整数へ変換する。

        Args:
            raw: 装置から受信した生の応答文字列。
            name: ログに表示する値または応答の名称。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        try:
            return int(raw, 10)
        except (TypeError, ValueError) as exc:
            self._logger.error(f"{name}応答を整数へ変換できません: " f"{raw!r}: {exc}")
            return None

    def _query_text(
        self,
        command: str,
    ) -> Optional[str]:
        """問い合わせを実行し前後空白を除去した応答を返す。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        raw = self._communication.query(command)
        if raw is None:
            return None

        return raw.strip()

    def _query_on_off(
        self,
        command: str,
    ) -> Optional[str]:
        """問い合わせ応答を ON/OFF として検証する。

        Args:
            command: 送信または問い合わせを行う PM2CD コマンド。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        raw = self._query_text(command)
        if raw is None:
            return None

        raw = raw.upper()
        if raw not in (
            "ON",
            "OFF",
        ):
            self._logger.error(f"{command}応答を解釈できません: {raw!r}")
            return None

        return raw

    def _motor_text(
        self,
        motor: int,
    ) -> Optional[str]:
        """モーター番号をコマンド用 16 進文字列へ変換する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        if not self._check_motor(motor):
            return None

        return f"{motor:X}"

    def _check_motor(
        self,
        motor: int,
    ) -> bool:
        """モーター番号が PM2CD の範囲内か検証する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if not self._check_int(motor, "motor"):
            return False

        if motor < 0 or motor >= self.CHANNEL_COUNT:
            self._logger.error(f"motorは0または1で指定してください")
            return False

        return True

    def _check_position(
        self,
        value: int,
        name: str,
    ) -> bool:
        """位置値が装置仕様の範囲内か検証する。

        Args:
            value: 検証する値。
            name: ログに表示する値または応答の名称。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if not self._check_int(value, name):
            return False

        if value < self.POSITION_MIN or value > self.POSITION_MAX:
            self._logger.error(
                f"{name}は{self.POSITION_MIN}から"
                f"{self.POSITION_MAX}の範囲で指定してください"
            )
            return False

        return True

    def _check_speed(
        self,
        speed: int,
    ) -> bool:
        """速度値が装置仕様の範囲内か検証する。

        Args:
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if not self._check_int(speed, "speed"):
            return False

        if speed < self.SPEED_MIN or speed > self.SPEED_MAX:
            self._logger.error(f"speedは5から100000の範囲で指定してください")
            return False

        return True

    def _check_int(
        self,
        value,
        name: str,
    ) -> bool:
        """値が bool ではない int か検証する。

        Args:
            value: 検証する値。
            name: ログに表示する値または応答の名称。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if not isinstance(value, int) or isinstance(value, bool):
            self._logger.error(f"{name}はintで指定してください")
            return False

        return True

    def _normalize_direction(
        self,
        direction: str,
    ) -> Optional[str]:
        """方向指定を cw または ccw に正規化する。

        Args:
            direction: 回転方向。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        if not isinstance(direction, str):
            self._logger.error(f"directionはstrで指定してください")
            return None

        normalized = direction.strip().lower()
        if normalized in (
            "cw",
            "+",
            "p",
            "positive",
        ):
            return "cw"

        if normalized in (
            "ccw",
            "-",
            "n",
            "negative",
        ):
            return "ccw"

        self._logger.error(f"directionはcwまたはccwで指定してください")
        return None

    def _normalize_side(
        self,
        side: str,
    ) -> Optional[str]:
        """リミット側指定を方向表現として正規化する。

        Args:
            side: リミット側。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._normalize_direction(side)

    def _normalize_speed_mode(
        self,
        mode: Union[int, str],
    ) -> Optional[str]:
        """速度モード指定を装置コマンド文字へ正規化する。

        Args:
            mode: 速度モード。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        if isinstance(mode, bool):
            self._logger.error(f"modeはintまたはstrで指定してください")
            return None

        if isinstance(mode, int):
            mapping = {
                1: "L",
                2: "M",
                3: "H",
            }
            if mode not in mapping:
                self._logger.error(f"modeは1, 2, 3またはL/M/Hで指定してください")
                return None

            return mapping[mode]

        if not isinstance(mode, str):
            self._logger.error(f"modeはintまたはstrで指定してください")
            return None

        normalized = mode.strip().upper()
        mapping = {
            "L": "L",
            "LOW": "L",
            "LSPD": "L",
            "M": "M",
            "MIDDLE": "M",
            "MSPD": "M",
            "H": "H",
            "HIGH": "H",
            "HSPD": "H",
        }

        if normalized not in mapping:
            self._logger.error(f"modeはL/M/Hで指定してください")
            return None

        return mapping[normalized]

    def _backlash_suffix(
        self,
        backlash: Union[str, bool, None],
    ) -> Optional[str]:
        """バックラッシュ指定を ABS/REL コマンドの接尾辞へ変換する。

        Args:
            backlash: バックラッシュ補正指定。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        if backlash is True:
            return "B"

        if backlash is False or backlash is None:
            return ""

        if not isinstance(backlash, str):
            self._logger.error(f"backlashはbool, str, Noneで指定してください")
            return None

        normalized = backlash.strip().upper()
        if normalized in (
            "",
            "NONE",
            "OFF",
        ):
            return ""

        if normalized in (
            "B",
            "S",
        ):
            return normalized

        self._logger.error(f"backlashはTrue/FalseまたはB/Sで指定してください")
        return None

    def _direction_digit(
        self,
        direction: str,
    ) -> Optional[str]:
        """方向指定を設定コマンド用の 0/1 へ変換する。

        Args:
            direction: 回転方向。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        normalized = self._normalize_direction(direction)
        if normalized is None:
            return None

        if normalized == "cw":
            return "0"

        return "1"

    def _bool_digit(
        self,
        value: bool,
        name: str,
    ) -> Optional[str]:
        """bool 値を設定コマンド用の 0/1 へ変換する。

        Args:
            value: 検証する値。
            name: ログに表示する値または応答の名称。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        if not isinstance(value, bool):
            self._logger.error(f"{name}はboolで指定してください")
            return None

        if value:
            return "1"

        return "0"
