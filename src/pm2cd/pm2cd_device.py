from typing import Optional, Union

from .core.communication_tcp import Communication
from .core.data import RATE_TABLE
from .core.errors import ProtocolError
from .core.motor_status import MotorStatus
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

    def __init__(
        self,
        communication: Communication,
        channel_count: int = 2,
        logger=None,
        log_level: str = "INFO",
    ):
        if channel_count != self.CHANNEL_COUNT:
            raise ValueError("PM2CDのchannel_countは2です")

        if not logger:
            import logging

            logging.basicConfig(level=(log_level or "INFO").upper())
            logger = logging.getLogger(__name__)

        self._logger = logger
        self._communication = communication
        self._version_info: Optional[VersionInfo] = None

    def remote(self) -> None:
        self._logger.info("== remote()")
        self._communication.send("REM")

    def local(self) -> None:
        self._logger.info("== local()")
        self._communication.send("LOC")

    def version(self) -> VersionInfo:
        self._logger.info("== version()")
        self._version_info = VersionInfo(self._communication.query("VER?"))
        return self._version_info

    def hardware_version(self) -> str:
        self._logger.info("== hardware_version()")
        raw = self._communication.query("VERH?").strip()
        if not raw.startswith("HD-VER"):
            raise ProtocolError(f"VERH?応答を解釈できません: {raw!r}")
        return raw

    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self._check_motor(motor)
        self._check_position(pulse, "pulse")
        suffix = self._backlash_suffix(backlash)
        self._communication.send(f"ABS{motor:X}{suffix}{pulse:+08d}")

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self._check_motor(motor)
        self._check_position(pulse, "pulse")
        suffix = self._backlash_suffix(backlash)
        self._communication.send(f"REL{motor:X}{suffix}{pulse:+08d}")

    def scan(self, motor: int, direction: str) -> None:
        command = "SCANP" if self._normalize_direction(direction) == "cw" else "SCANN"
        self._send_motor_command(command, motor)

    def constant_speed_scan(self, motor: int, direction: str) -> None:
        command = "CSCANP" if self._normalize_direction(direction) == "cw" else "CSCANN"
        self._send_motor_command(command, motor)

    def jog(self, motor: int, direction: str) -> None:
        command = "JOGP" if self._normalize_direction(direction) == "cw" else "JOGN"
        self._send_motor_command(command, motor)

    def home(self, motor: int) -> None:
        self._send_motor_command("GTHP", motor)

    def find_home(self, motor: int) -> None:
        self._send_motor_command("FDHP", motor)

    def stop(self, motor: int) -> None:
        self._send_motor_command("SSTP", motor)

    def stop_all(self) -> None:
        self._communication.send("ASSTP")

    def emergency_stop(self, motor: int) -> None:
        self._send_motor_command("ESTP", motor)

    def emergency_stop_all(self) -> None:
        self._communication.send("AESTP")

    def status(self, motor: int) -> MotorStatus:
        self._check_motor(motor)
        return self.status_all()[motor]

    def status_all(self) -> list[MotorStatus]:
        raw = self._communication.query("STS?")
        return MotorStatus.parse_all(raw)[: self.CHANNEL_COUNT]

    def position(self, motor: int) -> int:
        return self._query_int(f"PS?{self._motor_text(motor)}", "PS?")

    def set_position(self, motor: int, pulse: int) -> None:
        self._check_motor(motor)
        self._check_position(pulse, "pulse")
        self._communication.send(f"PS{motor:X}{pulse:+08d}")

    def set_speed(self, motor: int, speed: int) -> None:
        self._check_speed(speed)
        self.set_high_speed(motor, speed)
        self.set_middle_speed(motor, max(speed // 3, self.SPEED_MIN))
        self.set_low_speed(motor, max(speed // 10, self.SPEED_MIN))

    def set_speed_profile(
        self,
        motor: int,
        low_speed: int,
        middle_speed: int,
        high_speed: int,
    ) -> None:
        self._check_motor(motor)
        self._check_speed(low_speed)
        self._check_speed(middle_speed)
        self._check_speed(high_speed)
        self.set_low_speed(motor, low_speed)
        self.set_middle_speed(motor, middle_speed)
        self.set_high_speed(motor, high_speed)

    def high_speed(self, motor: int) -> int:
        return self._query_int(f"SPDH?{self._motor_text(motor)}", "SPDH?")

    def set_high_speed(self, motor: int, speed: int) -> None:
        self._check_motor(motor)
        self._check_speed(speed)
        self._communication.send(f"SPDH{motor:X}{speed:d}")

    def middle_speed(self, motor: int) -> int:
        return self._query_int(f"SPDM?{self._motor_text(motor)}", "SPDM?")

    def set_middle_speed(self, motor: int, speed: int) -> None:
        self._check_motor(motor)
        self._check_speed(speed)
        self._communication.send(f"SPDM{motor:X}{speed:d}")

    def low_speed(self, motor: int) -> int:
        return self._query_int(f"SPDL?{self._motor_text(motor)}", "SPDL?")

    def set_low_speed(self, motor: int, speed: int) -> None:
        self._check_motor(motor)
        self._check_speed(speed)
        self._communication.send(f"SPDL{motor:X}{speed:d}")

    def speed_mode(self, motor: int) -> str:
        raw = self._query_text(f"SPD?{self._motor_text(motor)}")
        if raw not in ("HSPD", "MSPD", "LSPD"):
            raise ProtocolError(f"SPD?応答を解釈できません: {raw!r}")
        return raw

    def set_speed_mode(self, motor: int, mode: Union[int, str]) -> None:
        self._check_motor(motor)
        normalized = self._normalize_speed_mode(mode)
        self._communication.send(f"SPD{normalized}{motor:X}")

    def rate_number(self, motor: int) -> int:
        value = self._query_int(f"RTE?{self._motor_text(motor)}", "RTE?")
        if value < self.RATE_MIN or value > self.RATE_MAX:
            raise ProtocolError(f"RTE?応答が範囲外です: {value}")
        return value

    def set_rate_number(self, motor: int, number: int) -> None:
        self._check_motor(motor)
        self._check_int(number, "number")
        if number < self.RATE_MIN or number > self.RATE_MAX:
            raise ValueError("numberは0から25の範囲で指定してください")
        self._communication.send(f"RTE{motor:X}{number:03d}")

    def backlash(self, motor: int) -> int:
        return self._query_int(f"B?{self._motor_text(motor)}", "B?")

    def set_backlash(self, motor: int, backlash: int) -> None:
        self._check_motor(motor)
        self._check_int(backlash, "backlash")
        if backlash < self.BACKLASH_MIN or backlash > self.BACKLASH_MAX:
            raise ValueError("backlashは-9999から9999の範囲で指定してください")
        self._communication.send(f"B{motor:X}{backlash:+05d}")

    def limit(self, motor: int, side: str) -> int:
        self._check_motor(motor)
        command = "FL?" if self._normalize_side(side) == "cw" else "BL?"
        return self._query_int(f"{command}{motor:X}", command)

    def set_limit(self, motor: int, side: str, pulse: int) -> None:
        self._check_motor(motor)
        self._check_position(pulse, "pulse")
        command = "FL" if self._normalize_side(side) == "cw" else "BL"
        self._communication.send(f"{command}{motor:X}{pulse:+08d}")

    def pause(self) -> None:
        self._communication.send("PAUSE ON")

    def resume(self) -> None:
        self._communication.send("PAUSE OFF")

    def pause_status(self) -> str:
        return self._query_on_off("PAUSE?")

    def hold(self, motor: int) -> str:
        return self._query_on_off(f"HOLD?{self._motor_text(motor)}")

    def set_hold(self, motor: int, enabled: bool) -> None:
        self._check_motor(motor)
        if not isinstance(enabled, bool):
            raise TypeError("enabledはboolで指定してください")
        mode = "ON" if enabled else "OFF"
        self._communication.send(f"HOLD{motor:X}{mode}")

    @staticmethod
    def number_to_rate(index: int) -> float:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("indexはintで指定してください")
        if index < 0 or index >= len(RATE_TABLE):
            raise ValueError("レート番号は0から25の範囲で指定してください")
        return RATE_TABLE[index]

    @staticmethod
    def rate_to_number(rate: float) -> int:
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise TypeError("rateは数値で指定してください")
        target = float(rate)
        for number, table_rate in enumerate(RATE_TABLE):
            if abs(target - table_rate) < 1.0e-12:
                return number
        raise ValueError("RATE TABLEに一致するレートではありません")

    def _send_motor_command(self, command: str, motor: int) -> None:
        self._communication.send(f"{command}{self._motor_text(motor)}")

    def _motor_text(self, motor: int) -> str:
        self._check_motor(motor)
        return f"{motor:X}"

    def _check_motor(self, motor: int) -> None:
        self._check_int(motor, "motor")
        if motor < 0 or motor >= self.CHANNEL_COUNT:
            raise ValueError("motorは0または1で指定してください")

    def _check_position(self, value: int, name: str) -> None:
        self._check_int(value, name)
        if value < self.POSITION_MIN or value > self.POSITION_MAX:
            raise ValueError(
                f"{name}は{self.POSITION_MIN}から{self.POSITION_MAX}の範囲で指定してください"
            )

    def _check_speed(self, speed: int) -> None:
        self._check_int(speed, "speed")
        if speed < self.SPEED_MIN or speed > self.SPEED_MAX:
            raise ValueError("speedは5から100000 ppsの範囲で指定してください")

    @staticmethod
    def _check_int(value: int, name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name}はintで指定してください")

    @staticmethod
    def _normalize_direction(direction: str) -> str:
        if not isinstance(direction, str):
            raise TypeError("directionはstrで指定してください")
        value = direction.lower()
        aliases = {
            "+": "cw",
            "p": "cw",
            "cw": "cw",
            "-": "ccw",
            "n": "ccw",
            "ccw": "ccw",
        }
        if value not in aliases:
            raise ValueError("directionは'cw'または'ccw'で指定してください")
        return aliases[value]

    @staticmethod
    def _normalize_side(side: str) -> str:
        return PM2CDDevice._normalize_direction(side)

    @staticmethod
    def _normalize_speed_mode(mode: Union[int, str]) -> str:
        if isinstance(mode, int) and not isinstance(mode, bool):
            values = {1: "L", 2: "M", 3: "H"}
            if mode not in values:
                raise ValueError("modeは1(L), 2(M), 3(H)で指定してください")
            return values[mode]

        value = str(mode).upper()
        aliases = {
            "L": "L",
            "LSPD": "L",
            "M": "M",
            "MSPD": "M",
            "H": "H",
            "HSPD": "H",
        }
        if value not in aliases:
            raise ValueError("modeは'L', 'M', 'H', 'LSPD', 'MSPD', 'HSPD'で指定してください")
        return aliases[value]

    @staticmethod
    def _backlash_suffix(backlash: Union[str, bool, None]) -> str:
        if backlash is True:
            return "B"
        if backlash is False or backlash is None:
            return ""
        if not isinstance(backlash, str):
            raise TypeError("backlashはbool、str、Noneで指定してください")
        value = backlash.upper()
        if value not in ("", "B", "S"):
            raise ValueError("backlashはTrue, False, None, 'B', 'S'で指定してください")
        return value

    def _query_text(self, command: str) -> str:
        raw = self._communication.query(command)
        if not isinstance(raw, str):
            raise ProtocolError(f"{command}応答がstrではありません: {raw!r}")
        value = raw.strip()
        if not value:
            raise ProtocolError(f"{command}応答が空です")
        return value

    def _query_int(self, command: str, response_name: str) -> int:
        raw = self._query_text(command)
        try:
            return int(raw, 10)
        except ValueError as exc:
            raise ProtocolError(f"{response_name}応答を整数へ変換できません: {raw!r}") from exc

    def _query_on_off(self, command: str) -> str:
        raw = self._query_text(command)
        if raw not in ("ON", "OFF"):
            raise ProtocolError(f"{command}応答を解釈できません: {raw!r}")
        return raw
