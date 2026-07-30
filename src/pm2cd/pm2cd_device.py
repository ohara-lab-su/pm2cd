from typing import Optional, Union

from .core.communication_tcp import Communication
from .core.data import RATE_TABLE
from .core.errors import ProtocolError
from .core.motor_status import MotorStatus
from .version_info import VersionInfo


class PM2CDDevice:
    """PM2CD/PM2C-06A固有のコマンド生成と応答解析を担当する。"""

    def __init__(self, communication: Communication, channel_count: int = 2):
        if channel_count < 1 or channel_count > 4:
            raise ValueError("channel_countは1から4の範囲で指定してください")
        self.communication = communication
        self.channel_count = channel_count
        self.version_info: Optional[VersionInfo] = None

    def remote(self) -> None:
        self.communication.send("REM")

    def local(self) -> None:
        self.communication.send("LOC")

    def version(self) -> VersionInfo:
        self.version_info = VersionInfo(self.communication.query("VER?"))
        return self.version_info

    def hardware_version(self) -> str:
        return self.communication.query("VERH?")

    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool] = True,
    ) -> None:
        suffix = self._backlash_suffix(backlash)
        self._check_motor(motor)
        self.communication.send(f"ABS{motor:X}{suffix}{pulse:+d}")

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool] = True,
    ) -> None:
        suffix = self._backlash_suffix(backlash)
        self._check_motor(motor)
        self.communication.send(f"REL{motor:X}{suffix}{pulse:+d}")

    def scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        direction = self._normalize_direction(direction)
        if direction == "cw":
            command = "SCANP"
        else:
            command = "SCANN"
        self._send_motor_command(command, motor)

    def constant_speed_scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        direction = self._normalize_direction(direction)
        if direction == "cw":
            command = "CSCANP"
        else:
            command = "CSCANN"
        self._send_motor_command(command, motor)

    def jog(
        self,
        motor: int,
        direction: str,
    ) -> None:
        direction = self._normalize_direction(direction)
        if direction == "cw":
            command = "JOGP"
        else:
            command = "JOGN"
        self._send_motor_command(command, motor)

    def home(
        self,
        motor: int,
    ) -> None:
        self._send_motor_command("GTHP", motor)

    def find_home(
        self,
        motor: int,
    ) -> None:
        self._send_motor_command("FDHP", motor)

    def stop(
        self,
        motor: int,
    ) -> None:
        self._send_motor_command("SSTP", motor)

    def stop_all(self) -> None:
        self.communication.send("ASSTP")

    def emergency_stop(
        self,
        motor: int,
    ) -> None:
        self._send_motor_command("ESTP", motor)

    def emergency_stop_all(self) -> None:
        self.communication.send("AESTP")

    def status(
        self,
        motor: int,
    ) -> MotorStatus:
        self._check_motor(motor)
        raw = self.communication.query("STS?")
        statuses = self._parse_status_all(raw)
        return statuses[motor]

    def status_all(self) -> list[MotorStatus]:
        return self._parse_status_all(self.communication.query("STS?"))

    def position(
        self,
        motor: int,
    ) -> int:
        return int(self._query_motor_command("PS?", motor))

    def set_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._send_motor_value("PS", motor, pulse, signed=True)

    def set_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self.set_high_speed(motor, speed)
        self.set_middle_speed(motor, max(speed // 3, 5))
        self.set_low_speed(motor, max(speed // 10, 5))

    def high_speed(
        self,
        motor: int,
    ) -> int:
        return int(self._query_motor_command("SPDH?", motor))

    def set_high_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._send_motor_value("SPDH", motor, speed)

    def middle_speed(
        self,
        motor: int,
    ) -> int:
        return int(self._query_motor_command("SPDM?", motor))

    def set_middle_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._send_motor_value("SPDM", motor, speed)

    def low_speed(
        self,
        motor: int,
    ) -> int:
        return int(self._query_motor_command("SPDL?", motor))

    def set_low_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._send_motor_value("SPDL", motor, speed)

    def speed_mode(
        self,
        motor: int,
    ) -> str:
        return self._query_motor_command("SPD?", motor)

    def set_speed_mode(
        self,
        motor: int,
        mode: Union[int, str],
    ) -> None:
        self._check_motor(motor)
        if isinstance(mode, int):
            values = {1: "L", 2: "M", 3: "H"}
            if mode not in values:
                raise ValueError("modeは1(L), 2(M), 3(H)で指定してください")
            mode = values[mode]
        mode = str(mode).upper()
        if mode not in ("L", "M", "H"):
            raise ValueError("modeは'L', 'M', 'H'で指定してください")
        self.communication.send(f"SPD{mode}{motor:X}")

    def rate_number(
        self,
        motor: int,
    ) -> int:
        return int(self._query_motor_command("RTE?", motor))

    def set_rate_number(
        self,
        motor: int,
        number: int,
    ) -> None:
        self._send_motor_value("RTE", motor, number)

    def backlash(
        self,
        motor: int,
    ) -> int:
        self._check_motor(motor)
        return int(self.communication.query(f"B?{motor:X}"))

    def set_backlash(
        self,
        motor: int,
        backlash: int,
    ) -> None:
        self._send_motor_value("B", motor, backlash, signed=True)

    def limit(
        self,
        motor: int,
        side: str,
    ) -> int:
        self._check_motor(motor)
        side = self._normalize_side(side)
        if side == "cw":
            command = "FL?"
        else:
            command = "BL?"
        return int(self.communication.query(f"{command}{motor:X}"))

    def set_limit(
        self,
        motor: int,
        side: str,
        pulse: int,
    ) -> None:
        self._check_motor(motor)
        side = self._normalize_side(side)
        if side == "cw":
            command = "FL"
        else:
            command = "BL"
        self.communication.send(f"{command}{motor:X}{pulse:+d}")

    def pause(self) -> None:
        self.communication.send("PAUSE ON")

    def resume(self) -> None:
        self.communication.send("PAUSE OFF")

    def pause_status(self) -> str:
        return self.communication.query("PAUSE?")

    def hold(
        self,
        motor: int,
    ) -> str:
        return self._query_motor_command("HOLD?", motor)

    def set_hold(
        self,
        motor: int,
        enabled: bool,
    ) -> None:
        self._check_motor(motor)
        if enabled:
            mode = "ON"
        else:
            mode = "OFF"
        self.communication.send(f"HOLD{motor:X}{mode}")

    def ttl_output_start(
        self,
        motor: int,
    ) -> None:
        self._send_motor_command("TMGR", motor)

    def ttl_output_stop(
        self,
        motor: int,
    ) -> None:
        self._send_motor_command("TMGC", motor)

    def ttl_status(
        self,
        motor: int,
    ) -> int:
        raw = self._query_motor_command("TMGR?", motor)
        if raw == "YES":
            return 1
        if raw == "NO":
            return 0
        raise ProtocolError(f"TTL状態応答を解釈できません: {raw!r}")

    @staticmethod
    def number_to_rate(index: int) -> float:
        try:
            return RATE_TABLE[index]
        except IndexError as exc:
            raise ValueError("レート番号が範囲外です") from exc

    @staticmethod
    def rate_to_number(rate: float) -> int:
        error = -0.0001
        for number, table_rate in enumerate(RATE_TABLE):
            if abs(rate) - abs(table_rate) >= error:
                return number
        raise ValueError("レートが範囲外です")

    def _parse_status_all(
        self,
        raw: str,
    ) -> list[MotorStatus]:
        parts = raw.split("/")
        if len(parts) < 4 + self.channel_count:
            raise ProtocolError(f"STS?応答が不正です: {raw!r}")
        header = parts[0]
        directions = parts[1]
        limits = parts[2]
        positions = parts[4 : 4 + self.channel_count]
        result = []
        try:
            for motor in range(self.channel_count):
                result.append(
                    MotorStatus(
                        motor=motor,
                        raw=raw,
                        remote_local=header[0],
                        direction=directions[motor],
                        ls_status=int(limits[motor], 16),
                        position=int(positions[motor]),
                    )
                )
        except (IndexError, ValueError) as exc:
            raise ProtocolError(f"STS?応答を解析できません: {raw!r}") from exc
        return result

    def _send_motor_command(
        self,
        command: str,
        motor: int,
    ) -> None:
        self._check_motor(motor)
        self.communication.send(f"{command}{motor:X}")

    def _send_motor_value(
        self,
        command: str,
        motor: int,
        value: int,
        signed: bool = False,
    ) -> None:
        self._check_motor(motor)
        if signed:
            text = f"{value:+d}"
        else:
            text = str(value)
        self.communication.send(f"{command}{motor:X}{text}")

    def _query_motor_command(
        self,
        command: str,
        motor: int,
    ) -> str:
        self._check_motor(motor)
        return self.communication.query(f"{command}{motor:X}")

    def _check_motor(
        self,
        motor: int,
    ) -> None:
        if motor < 0 or motor >= self.channel_count:
            raise ValueError(
                f"motorは0から{self.channel_count - 1}の範囲で指定してください"
            )

    @staticmethod
    def _normalize_direction(direction: str) -> str:
        direction = direction.lower()
        aliases = {
            "+": "cw",
            "p": "cw",
            "cw": "cw",
            "-": "ccw",
            "n": "ccw",
            "ccw": "ccw",
        }
        if direction not in aliases:
            raise ValueError("directionは'cw'または'ccw'で指定してください")
        return aliases[direction]

    @staticmethod
    def _normalize_side(side: str) -> str:
        return PM2CDDevice._normalize_direction(side)

    @staticmethod
    def _backlash_suffix(backlash: Union[str, bool]) -> str:
        if backlash is True:
            return "B"
        if backlash is False or backlash is None:
            return ""
        value = str(backlash).upper()
        if value not in ("B", "S", ""):
            raise ValueError("backlashはTrue, False, 'B', 'S'で指定してください")
        return value
