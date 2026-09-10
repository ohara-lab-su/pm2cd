from typing import List, Optional, Union

from .core.communication_tcp import Communication
from .core.controller_status import ControllerStatus
from .core.data import RATE_TABLE
from .core.errors import ProtocolError
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
        if channel_count != self.CHANNEL_COUNT:
            raise ValueError(
                "PM2CDのchannel_countは2です",
            )

        if not logger:
            import logging

            logging.basicConfig(
                level=(log_level or "INFO").upper(),
            )
            logger = logging.getLogger(
                __name__,
            )

        self._logger = logger
        self._communication = communication
        # self._version_info = None  # type: Optional[VersionInfo]
        self._version_info: Optional[VersionInfo] = None

    def remote(
        self,
    ) -> None:
        self._logger.info(
            f"== remote()",
        )
        self._communication.send(
            "REM",
        )

    def local(
        self,
    ) -> None:
        self._logger.info(
            f"== local()",
        )
        self._communication.send(
            "LOC",
        )

    def version(
        self,
    ) -> Optional[VersionInfo]:
        self._logger.info(
            f"== version()",
        )
        self._version_info = VersionInfo(
            self._communication.query(
                "VER?",
            ),
        )
        return self._version_info

    def hardware_version(
        self,
    ) -> str:
        self._logger.info(
            f"== hardware_version()",
        )
        raw = self._communication.query(
            "VERH?",
        ).strip()
        if not raw.startswith(
            "HD-VER",
        ):
            raise ProtocolError(
                f"VERH?応答を解釈できません: {raw!r}",
            )
        return raw

    def controller_status(
        self,
    ) -> ControllerStatus:
        self._logger.info(
            f"== controller_status()",
        )
        return ControllerStatus(
            self._communication.query(
                "STQ?",
            ),
        )

    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self._logger.info(
            f"== move()",
        )
        self._check_motor(
            motor,
        )
        self._check_position(
            pulse,
            "pulse",
        )
        suffix = self._backlash_suffix(
            backlash,
        )
        command = f"ABS{self._motor_text(motor,)}{suffix}{pulse:d}"
        self._communication.send(
            command,
        )

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self._logger.info(
            f"== move_relative()",
        )
        self._check_motor(
            motor,
        )
        self._check_position(
            pulse,
            "pulse",
        )
        suffix = self._backlash_suffix(
            backlash,
        )
        command = f"REL{self._motor_text(motor,)}{suffix}{pulse:d}"
        self._communication.send(
            command,
        )

    def scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._logger.info(
            f"== scan()",
        )
        normalized = self._normalize_direction(
            direction,
        )
        command = "SCANN"
        if normalized == "cw":
            command = "SCANP"
        self._send_motor_command(
            command,
            motor,
        )

    def constant_speed_scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._logger.info(
            f"== constant_speed_scan()",
        )
        normalized = self._normalize_direction(
            direction,
        )
        command = "CSCANN"
        if normalized == "cw":
            command = "CSCANP"
        self._send_motor_command(
            command,
            motor,
        )

    def jog(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._logger.info(
            f"== jog()",
        )
        normalized = self._normalize_direction(
            direction,
        )
        command = "JOGN"
        if normalized == "cw":
            command = "JOGP"
        self._send_motor_command(
            command,
            motor,
        )

    def scan_home(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._logger.info(
            f"== scan_home()",
        )
        normalized = self._normalize_direction(
            direction,
        )
        command = "SCANHN"
        if normalized == "cw":
            command = "SCANHP"
        self._send_motor_command(
            command,
            motor,
        )

    def home(
        self,
        motor: int,
    ) -> None:
        self._logger.info(
            f"== home()",
        )
        self._send_motor_command(
            "GTHP",
            motor,
        )

    def find_home(
        self,
        motor: int,
    ) -> None:
        self._logger.info(
            f"== find_home()",
        )
        self._send_motor_command(
            "FDHP",
            motor,
        )

    def stop(
        self,
        motor: int,
    ) -> None:
        self._logger.info(
            f"== stop()",
        )
        self._send_motor_command(
            "SSTP",
            motor,
        )

    def stop_all(
        self,
    ) -> None:
        self._logger.info(
            f"== stop_all()",
        )
        self._communication.send(
            "ASSTP",
        )

    def emergency_stop(
        self,
        motor: int,
    ) -> None:
        self._logger.info(
            f"== emergency_stop()",
        )
        self._send_motor_command(
            "ESTP",
            motor,
        )

    def emergency_stop_all(
        self,
    ) -> None:
        self._logger.info(
            f"== emergency_stop_all()",
        )
        self._communication.send(
            "AESTP",
        )

    def status(
        self,
        motor: int,
    ) -> MotorStatus:
        self._logger.info(
            f"== status()",
        )
        self._check_motor(
            motor,
        )
        return self.status_all()[motor]

    def status_all(
        self,
    ) -> List[MotorStatus]:
        self._logger.info(
            f"== status_all()",
        )
        raw = self._communication.query(
            "STS?",
        )
        return MotorStatus.parse_all(
            raw,
        )[: self.CHANNEL_COUNT]

    def check_rotate(
        self,
        motor: int,
    ) -> bool:
        self._logger.info(
            f"== check_rotate()",
        )
        return (
            self.status(
                motor,
            ).rotation_state
            == 1
        )

    def position(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== position()",
        )
        command = f"PS?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "PS?",
        )

    def set_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._logger.info(
            f"== set_position()",
        )
        self._check_motor(
            motor,
        )
        self._check_position(
            pulse,
            "pulse",
        )
        self._communication.send(
            f"PS{self._motor_text(motor,)}{pulse:d}",
        )

    def set_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._logger.info(
            f"== set_speed()",
        )
        self._check_motor(
            motor,
        )
        self._check_speed(
            speed,
        )
        middle = speed // 3
        if middle < self.SPEED_MIN:
            middle = self.SPEED_MIN
        low = speed // 10
        if low < self.SPEED_MIN:
            low = self.SPEED_MIN
        self.set_high_speed(
            motor,
            speed,
        )
        self.set_middle_speed(
            motor,
            middle,
        )
        self.set_low_speed(
            motor,
            low,
        )

    def set_speed_profile(
        self,
        motor: int,
        low_speed: int,
        middle_speed: int,
        high_speed: int,
    ) -> None:
        self._logger.info(
            f"== set_speed_profile()",
        )
        self._check_motor(
            motor,
        )
        self._check_speed(
            low_speed,
        )
        self._check_speed(
            middle_speed,
        )
        self._check_speed(
            high_speed,
        )
        self.set_low_speed(
            motor,
            low_speed,
        )
        self.set_middle_speed(
            motor,
            middle_speed,
        )
        self.set_high_speed(
            motor,
            high_speed,
        )

    def high_speed(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== high_speed()",
        )
        command = f"SPDH?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "SPDH?",
        )

    def set_high_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._logger.info(
            f"== set_high_speed()",
        )
        self._set_speed_value(
            "SPDH",
            motor,
            speed,
        )

    def middle_speed(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== middle_speed()",
        )
        command = f"SPDM?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "SPDM?",
        )

    def set_middle_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._logger.info(
            f"== set_middle_speed()",
        )
        self._set_speed_value(
            "SPDM",
            motor,
            speed,
        )

    def low_speed(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== low_speed()",
        )
        command = f"SPDL?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "SPDL?",
        )

    def set_low_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._logger.info(
            f"== set_low_speed()",
        )
        self._set_speed_value(
            "SPDL",
            motor,
            speed,
        )

    def speed_mode(
        self,
        motor: int,
    ) -> str:
        self._logger.info(
            f"== speed_mode()",
        )
        raw = self._query_text(
            f"SPD?{self._motor_text(motor,)}",
        )
        if raw not in ("HSPD", "MSPD", "LSPD"):
            raise ProtocolError(
                f"SPD?応答を解釈できません: {raw!r}",
            )
        return raw

    def set_speed_mode(
        self,
        motor: int,
        mode: Union[int, str],
    ) -> None:
        self._logger.info(
            f"== set_speed_mode()",
        )
        self._check_motor(
            motor,
        )
        normalized = self._normalize_speed_mode(
            mode,
        )
        self._communication.send(
            f"SPD{normalized}{self._motor_text(motor,)}",
        )

    def rate_number(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== rate_number()",
        )
        command = f"RTE?{self._motor_text(motor,)}"
        value = self._query_int(
            command,
            "RTE?",
        )
        if value < self.RATE_MIN or value > self.RATE_MAX:
            raise ProtocolError(
                f"RTE?応答が範囲外です: {value}",
            )
        return value

    def set_rate_number(
        self,
        motor: int,
        number: int,
    ) -> None:
        self._logger.info(
            f"== set_rate_number()",
        )
        self._check_motor(
            motor,
        )
        self._check_int(
            number,
            "number",
        )
        if number < self.RATE_MIN or number > self.RATE_MAX:
            raise ValueError(
                "numberは0から25の範囲で指定してください",
            )
        command = f"RTE{self._motor_text(motor,)}{number:03d}"
        self._communication.send(
            command,
        )

    def backlash(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== backlash()",
        )
        command = f"B?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "B?",
        )

    def set_backlash(
        self,
        motor: int,
        backlash: int,
    ) -> None:
        self._logger.info(
            f"== set_backlash()",
        )
        self._check_motor(
            motor,
        )
        self._check_int(
            backlash,
            "backlash",
        )
        if backlash < self.BACKLASH_MIN or backlash > self.BACKLASH_MAX:
            raise ValueError(
                "backlashは-9999から9999の範囲で指定してください",
            )
        command = f"B{self._motor_text(motor,)}{backlash:d}"
        self._communication.send(
            command,
        )

    def limit(
        self,
        motor: int,
        side: str,
    ) -> int:
        self._logger.info(
            f"== limit()",
        )
        self._check_motor(
            motor,
        )
        normalized = self._normalize_side(
            side,
        )
        command = "BL?"
        if normalized == "cw":
            command = "FL?"
        query = f"{command}{self._motor_text(motor,)}"
        return self._query_int(
            query,
            command,
        )

    def set_limit(
        self,
        motor: int,
        side: str,
        pulse: int,
    ) -> None:
        self._logger.info(
            f"== set_limit()",
        )
        self._check_motor(
            motor,
        )
        self._check_position(
            pulse,
            "pulse",
        )
        normalized = self._normalize_side(
            side,
        )
        setting = self.limit_switch_setting(
            motor,
        )
        if not setting.digital_limit_enabled:
            self.set_limit_switch_setting_raw(
                motor,
                setting.with_digital_limit(
                    True,
                ),
            )
        command = "BL"
        if normalized == "cw":
            command = "FL"
        message = f"{command}{self._motor_text(motor,)}{pulse:d}"
        self._communication.send(
            message,
        )

    def pause(
        self,
    ) -> None:
        self._logger.info(
            f"== pause()",
        )
        self._communication.send(
            "PAUSE ON",
        )

    def resume(
        self,
    ) -> None:
        self._logger.info(
            f"== resume()",
        )
        self._communication.send(
            "PAUSE OFF",
        )

    def pause_status(
        self,
    ) -> str:
        self._logger.info(
            f"== pause_status()",
        )
        return self._query_on_off(
            "PAUSE?",
        )

    def hold(
        self,
        motor: int,
    ) -> str:
        self._logger.info(
            f"== hold()",
        )
        return self._query_on_off(
            f"HOLD?{self._motor_text(motor,)}",
        )

    def set_hold(
        self,
        motor: int,
        enabled: bool,
    ) -> None:
        self._logger.info(
            f"== set_hold()",
        )
        self._check_motor(
            motor,
        )
        if not isinstance(
            enabled,
            bool,
        ):
            raise TypeError(
                "enabledはboolで指定してください",
            )
        mode = "OFF"
        if enabled:
            mode = "ON"
        self._communication.send(
            f"HOLD{self._motor_text(motor,)}{mode}",
        )

    def hold_on_time(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== hold_on_time()",
        )
        command = f"H_ONTM?{self._motor_text(motor,)}"
        return self._query_msec(
            command,
        )

    def set_hold_on_time(
        self,
        motor: int,
        msec: int,
    ) -> None:
        self._logger.info(
            f"== set_hold_on_time()",
        )
        self._set_hold_time(
            "H_ONTM",
            motor,
            msec,
        )

    def hold_off_time(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== hold_off_time()",
        )
        command = f"H_OFTM?{self._motor_text(motor,)}"
        return self._query_msec(
            command,
        )

    def set_hold_off_time(
        self,
        motor: int,
        msec: int,
    ) -> None:
        self._logger.info(
            f"== set_hold_off_time()",
        )
        self._set_hold_time(
            "H_OFTM",
            motor,
            msec,
        )

    def home_status(
        self,
        motor: int,
    ) -> HomeStatus:
        self._logger.info(
            f"== home_status()",
        )
        raw = self._communication.query(
            f"SETHP?{self._motor_text(motor,)}",
        )
        return HomeStatus(
            raw,
        )

    def set_home_status(
        self,
        motor: int,
        found: bool,
        found_direction: str,
        auto_start_direction: str,
    ) -> None:
        self._logger.info(
            f"== set_home_status()",
        )
        self._check_motor(
            motor,
        )
        found_value = self._bool_digit(
            found,
            "found",
        )
        found_dir = self._direction_digit(
            found_direction,
        )
        auto_dir = self._direction_digit(
            auto_start_direction,
        )
        command = (
            f"SETHP{self._motor_text(motor,)}0" f"{found_value}{found_dir}{auto_dir}"
        )
        self._communication.send(
            command,
        )

    def home_position(
        self,
        motor: int,
    ) -> Optional[int]:
        self._logger.info(
            f"== home_position()",
        )
        raw = self._query_text(
            f"SHP?{self._motor_text(motor,)}",
        )
        if raw == "NO H.P":
            return None
        return self._parse_int(
            raw,
            "SHP?",
        )

    def set_home_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._logger.info(
            f"== set_home_position()",
        )
        self._check_motor(
            motor,
        )
        self._check_position(
            pulse,
            "pulse",
        )
        command = f"SHP{self._motor_text(motor,)}{pulse:d}"
        self._communication.send(
            command,
        )

    def home_offset(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== home_offset()",
        )
        command = f"SHPF?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "SHPF?",
        )

    def set_home_offset(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._logger.info(
            f"== set_home_offset()",
        )
        self._check_motor(
            motor,
        )
        self._check_int(
            pulse,
            "pulse",
        )
        if pulse < self.HOME_OFFSET_MIN or pulse > self.HOME_OFFSET_MAX:
            raise ValueError(
                "pulseは0から9999の範囲で指定してください",
            )
        command = f"SHPF{self._motor_text(motor,)}{pulse:d}"
        self._communication.send(
            command,
        )

    def preset_position(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== preset_position()",
        )
        command = f"SPRS?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "SPRS?",
        )

    def set_preset_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._logger.info(
            f"== set_preset_position()",
        )
        self._check_motor(
            motor,
        )
        self._check_position(
            pulse,
            "pulse",
        )
        command = f"SPRS{self._motor_text(motor,)}{pulse:d}"
        self._communication.send(
            command,
        )

    def jog_pulse(
        self,
        motor: int,
    ) -> int:
        self._logger.info(
            f"== jog_pulse()",
        )
        command = f"SETJG?{self._motor_text(motor,)}"
        return self._query_int(
            command,
            "SETJG?",
        )

    def set_jog_pulse(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._logger.info(
            f"== set_jog_pulse()",
        )
        self._check_motor(
            motor,
        )
        self._check_int(
            pulse,
            "pulse",
        )
        if pulse < self.JOG_PULSE_MIN or pulse > self.JOG_PULSE_MAX:
            raise ValueError(
                "pulseは0から9999の範囲で指定してください",
            )
        command = f"SETJG{self._motor_text(motor,)}{pulse:04d}"
        self._communication.send(
            command,
        )

    def limit_switch_setting(
        self,
        motor: int,
    ) -> LimitSwitchSetting:
        self._logger.info(
            f"== limit_switch_setting()",
        )
        command = f"SETLS?{self._motor_text(motor,)}"
        return LimitSwitchSetting(
            self._communication.query(
                command,
            ),
        )

    def set_limit_switch_setting_raw(
        self,
        motor: int,
        setting: str,
    ) -> None:
        self._logger.info(
            f"== set_limit_switch_setting_raw()",
        )
        self._check_motor(
            motor,
        )
        parsed = LimitSwitchSetting(
            setting,
        )
        command = f"SETLS{self._motor_text(motor,)}{parsed.raw}"
        self._communication.send(
            command,
        )

    def motor_setting(
        self,
        motor: int,
    ) -> MotorSetting:
        self._logger.info(
            f"== motor_setting()",
        )
        command = f"SETMT?{self._motor_text(motor,)}"
        return MotorSetting(
            self._communication.query(
                command,
            ),
        )

    def set_motor_setting(
        self,
        motor: int,
        drive_enabled: bool,
        hold_mode: int,
        output_mode: int,
    ) -> None:
        self._logger.info(
            f"== set_motor_setting()",
        )
        self._check_motor(
            motor,
        )
        drive = self._bool_digit(
            drive_enabled,
            "drive_enabled",
        )
        self._check_int(
            hold_mode,
            "hold_mode",
        )
        self._check_int(
            output_mode,
            "output_mode",
        )
        if hold_mode < 0 or hold_mode > 3:
            raise ValueError(
                "hold_modeは0から3の範囲で指定してください",
            )
        if output_mode < 0 or output_mode > 2:
            raise ValueError(
                "output_modeは0から2の範囲で指定してください",
            )
        command = f"SETMT{self._motor_text(motor,)}" f"{drive}{hold_mode}1{output_mode}"
        self._communication.send(
            command,
        )

    def stop_mode(
        self,
        motor: int,
    ) -> StopMode:
        self._logger.info(
            f"== stop_mode()",
        )
        command = f"STOPMD?{self._motor_text(motor,)}"
        return StopMode(
            self._communication.query(
                command,
            ),
        )

    def set_stop_mode(
        self,
        motor: int,
        panel_fast: bool,
        limit_fast: bool,
    ) -> None:
        self._logger.info(
            f"== set_stop_mode()",
        )
        self._check_motor(
            motor,
        )
        panel = self._bool_digit(
            panel_fast,
            "panel_fast",
        )
        limit_value = self._bool_digit(
            limit_fast,
            "limit_fast",
        )
        command = f"STOPMD{self._motor_text(motor,)}" f"{panel}{limit_value}"
        self._communication.send(
            command,
        )

    @staticmethod
    def number_to_rate(
        index: int,
    ) -> float:
        if not isinstance(
            index,
            int,
        ) or isinstance(
            index,
            bool,
        ):
            raise TypeError(
                "indexはintで指定してください",
            )
        if index < 0 or index >= len(
            RATE_TABLE,
        ):
            raise ValueError(
                "レート番号は0から25の範囲で指定してください",
            )
        return RATE_TABLE[index]

    @staticmethod
    def rate_to_number(
        rate: float,
    ) -> int:
        if not isinstance(
            rate,
            (int, float),
        ) or isinstance(
            rate,
            bool,
        ):
            raise TypeError(
                "rateは数値で指定してください",
            )
        target = abs(
            float(
                rate,
            ),
        )
        for number, table_rate in enumerate(
            RATE_TABLE,
        ):
            if target >= table_rate:
                return number
        raise ValueError(
            "rateがRATE TABLEの範囲外です",
        )

    def _send_motor_command(
        self,
        command: str,
        motor: int,
    ) -> None:
        self._communication.send(
            f"{command}{self._motor_text(motor,)}",
        )

    def _set_speed_value(
        self,
        command: str,
        motor: int,
        speed: int,
    ) -> None:
        self._check_motor(
            motor,
        )
        self._check_speed(
            speed,
        )
        message = f"{command}{self._motor_text(motor,)}{speed:d}"
        self._communication.send(
            message,
        )

    def _set_hold_time(
        self,
        command: str,
        motor: int,
        msec: int,
    ) -> None:
        self._check_motor(
            motor,
        )
        self._check_int(
            msec,
            "msec",
        )
        if msec < self.HOLD_TIME_MIN or msec > self.HOLD_TIME_MAX:
            raise ValueError(
                "msecは50から3000の範囲で指定してください",
            )
        if msec % self.HOLD_TIME_STEP != 0:
            raise ValueError(
                "msecは10刻みで指定してください",
            )
        message = f"{command}{self._motor_text(motor,)}{msec:d}"
        self._communication.send(
            message,
        )

    def _query_msec(
        self,
        command: str,
    ) -> int:
        raw = self._query_text(
            command,
        )
        normalized = (
            raw.lower()
            .replace(
                "msec.",
                "",
            )
            .replace(
                "ms",
                "",
            )
            .strip()
        )
        return self._parse_int(
            normalized,
            command,
        )

    def _query_int(
        self,
        command: str,
        name: str,
    ) -> int:
        raw = self._query_text(
            command,
        )
        return self._parse_int(
            raw,
            name,
        )

    @staticmethod
    def _parse_int(
        raw: str,
        name: str,
    ) -> int:
        try:
            return int(
                raw,
                10,
            )
        except ValueError as exc:
            raise ProtocolError(
                f"{name}応答を整数へ変換できません: {raw!r}",
            ) from exc

    def _query_text(
        self,
        command: str,
    ) -> str:
        return self._communication.query(
            command,
        ).strip()

    def _query_on_off(
        self,
        command: str,
    ) -> str:
        raw = self._query_text(
            command,
        ).upper()
        if raw not in ("ON", "OFF"):
            raise ProtocolError(
                f"{command}応答を解釈できません: {raw!r}",
            )
        return raw

    def _motor_text(
        self,
        motor: int,
    ) -> str:
        self._check_motor(
            motor,
        )
        return f"{motor:X}"

    def _check_motor(
        self,
        motor: int,
    ) -> None:
        self._check_int(
            motor,
            "motor",
        )
        if motor < 0 or motor >= self.CHANNEL_COUNT:
            raise ValueError(
                "motorは0または1で指定してください",
            )

    def _check_position(
        self,
        value: int,
        name: str,
    ) -> None:
        self._check_int(
            value,
            name,
        )
        if value < self.POSITION_MIN or value > self.POSITION_MAX:
            raise ValueError(
                f"{name}は{self.POSITION_MIN}から"
                f"{self.POSITION_MAX}の範囲で指定してください",
            )

    def _check_speed(
        self,
        speed: int,
    ) -> None:
        self._check_int(
            speed,
            "speed",
        )
        if speed < self.SPEED_MIN or speed > self.SPEED_MAX:
            raise ValueError(
                "speedは5から100000の範囲で指定してください",
            )

    @staticmethod
    def _check_int(
        value,
        name: str,
    ) -> None:
        if not isinstance(
            value,
            int,
        ) or isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{name}はintで指定してください",
            )

    @staticmethod
    def _normalize_direction(
        direction: str,
    ) -> str:
        if not isinstance(
            direction,
            str,
        ):
            raise TypeError(
                "directionはstrで指定してください",
            )
        normalized = direction.strip().lower()
        if normalized in ("cw", "+", "p", "positive"):
            return "cw"
        if normalized in ("ccw", "-", "n", "negative"):
            return "ccw"
        raise ValueError(
            "directionはcwまたはccwで指定してください",
        )

    def _normalize_side(
        self,
        side: str,
    ) -> str:
        return self._normalize_direction(
            side,
        )

    @staticmethod
    def _normalize_speed_mode(
        mode: Union[int, str],
    ) -> str:
        if isinstance(
            mode,
            bool,
        ):
            raise TypeError(
                "modeはintまたはstrで指定してください",
            )
        if isinstance(
            mode,
            int,
        ):
            mapping = {1: "L", 2: "M", 3: "H"}
            if mode not in mapping:
                raise ValueError(
                    "modeは1, 2, 3またはL/M/Hで指定してください",
                )
            return mapping[mode]
        if not isinstance(
            mode,
            str,
        ):
            raise TypeError(
                "modeはintまたはstrで指定してください",
            )
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
            raise ValueError(
                "modeはL/M/Hで指定してください",
            )
        return mapping[normalized]

    @staticmethod
    def _backlash_suffix(
        backlash: Union[str, bool, None],
    ) -> str:
        if backlash is True:
            return "B"
        if backlash is False or backlash is None:
            return ""
        if not isinstance(
            backlash,
            str,
        ):
            raise TypeError(
                "backlashはbool, str, Noneで指定してください",
            )
        normalized = backlash.strip().upper()
        if normalized in ("", "NONE", "OFF"):
            return ""
        if normalized in ("B", "S"):
            return normalized
        raise ValueError(
            "backlashはTrue/FalseまたはB/Sで指定してください",
        )

    def _direction_digit(
        self,
        direction: str,
    ) -> str:
        normalized = self._normalize_direction(
            direction,
        )
        if normalized == "cw":
            return "0"
        return "1"

    @staticmethod
    def _bool_digit(
        value: bool,
        name: str,
    ) -> str:
        if not isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{name}はboolで指定してください",
            )
        if value:
            return "1"
        return "0"
