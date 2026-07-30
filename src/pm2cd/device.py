from typing import Optional

from pm2cd.communication import PM2CDCommunication
from pm2cd.data import RATE_TABLE
from pm2cd.errors import PM2CDProtocolError
from pm2cd.motor_status import MotorStatus
from pm2cd.version_info import VersionInfo


class PM2CDDevice:
    """PM2CD固有のコマンド生成、応答解析、装置状態を担当するドライバ層。"""

    def __init__(self, communication: PM2CDCommunication, channel_count: int = 2):
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

    def move(self, motor: int, pulse: int, backlash: str | bool = True) -> None:
        self._check_motor(motor)
        suffix = self._backlash_suffix(backlash)
        self.communication.send(f"ABS{motor:X}{suffix}{pulse:+d}")

    def move_relative(self, motor: int, pulse: int, backlash: str | bool = True) -> None:
        self._check_motor(motor)
        suffix = self._backlash_suffix(backlash)
        self.communication.send(f"REL{motor:X}{suffix}{pulse:+d}")

    def scan(self, motor: int, direction: str) -> None:
        self._check_motor(motor)
        self.communication.send(f"SCAN{self._direction(direction)}{motor:X}")

    def constant_speed_scan(self, motor: int, direction: str) -> None:
        self._check_motor(motor)
        self.communication.send(f"CSCAN{self._direction(direction)}{motor:X}")

    def scan_until_home(self, motor: int, direction: str) -> None:
        self._check_motor(motor)
        self.communication.send(f"SCANH{self._direction(direction)}{motor:X}")

    def jog(self, motor: int, direction: str) -> None:
        self._check_motor(motor)
        self.communication.send(f"JOG{self._direction(direction)}{motor:X}")

    def home(self, motor: int) -> None:
        self._send_motor_command("GTHP", motor)

    def find_home(self, motor: int) -> None:
        self._send_motor_command("FDHP", motor)

    def stop(self, motor: int) -> None:
        self._send_motor_command("SSTP", motor)

    def stop_all(self) -> None:
        self.communication.send("ASSTP")

    def emergency_stop(self, motor: int) -> None:
        self._send_motor_command("ESTP", motor)

    def emergency_stop_all(self) -> None:
        self.communication.send("AESTP")

    def status(self, motor: int) -> MotorStatus:
        self._check_motor(motor)
        return MotorStatus.from_single_response(motor, self.communication.query(f"STS{motor:X}?"))

    def status_bits(self, motor: int) -> int:
        return self.status(motor).legacy_status_bits

    def status_all(self) -> list[MotorStatus]:
        return [self.status(motor) for motor in range(self.channel_count)]

    def position(self, motor: int) -> int:
        return int(self._query_motor_command("PS?", motor))

    def set_position(self, motor: int, pulse: int) -> None:
        self._send_motor_value("PS", motor, pulse)

    def speed_mode(self, motor: int) -> str:
        return self._query_motor_command("SPD?", motor)

    def set_speed_mode(self, motor: int, mode: int | str) -> None:
        self._check_motor(motor)
        if isinstance(mode, int):
            speed = "L" if mode == 1 else "M" if mode == 2 else "H"
        else:
            speed = mode.upper()[0]
            if speed not in ("L", "M", "H"):
                raise ValueError("modeは1/2/3または'L'/'M'/'H'で指定してください")
        self.communication.send(f"SPD{speed}{motor:X}")

    def high_speed(self, motor: int) -> int:
        return int(self._query_motor_command("SPDH?", motor))

    def set_high_speed(self, motor: int, speed: int) -> None:
        self._send_motor_value("SPDH", motor, speed)

    def middle_speed(self, motor: int) -> int:
        return int(self._query_motor_command("SPDM?", motor))

    def set_middle_speed(self, motor: int, speed: int) -> None:
        self._send_motor_value("SPDM", motor, speed)

    def low_speed(self, motor: int) -> int:
        return int(self._query_motor_command("SPDL?", motor))

    def set_low_speed(self, motor: int, speed: int) -> None:
        self._send_motor_value("SPDL", motor, speed)

    def set_speed(self, motor: int, speed: int) -> None:
        self.set_high_speed(motor, speed)
        self.set_middle_speed(motor, speed // 3)
        self.set_low_speed(motor, max(speed // 10, 5))

    def rate_number(self, motor: int) -> int:
        return int(self._query_motor_command("RTE?", motor))

    def set_rate_number(self, motor: int, number: int) -> None:
        self._send_motor_value("RTE", motor, number)

    def backlash(self, motor: int) -> int:
        self._check_motor(motor)
        return int(self.communication.query(f"B?{motor:X}"))

    def set_backlash(self, motor: int, backlash: int) -> None:
        self._send_motor_value("B", motor, backlash)

    def limit(self, motor: int, side: str) -> int:
        self._check_motor(motor)
        side = self._normalize_side(side)
        command = "FL?" if side == "cw" else "BL?"
        return int(self.communication.query(f"{command}{motor:X}"))

    def set_limit(self, motor: int, side: str, pulse: int) -> None:
        self._check_motor(motor)
        side = self._normalize_side(side)
        current = self.communication.query(f"SETLS?{motor:X}")
        if not current:
            raise PM2CDProtocolError("SETLS応答が空です")
        self.communication.send(f"SETLS{motor:X}1{current[1:]}")
        command = "FL" if side == "cw" else "BL"
        self.communication.send(f"{command}{motor:X}{pulse}")

    def limit_status_bits(self, motor: int) -> int:
        self._check_motor(motor)
        raw = self.communication.query(f"SETLS?{motor:X}")
        if any(character not in "01" for character in raw):
            raise PM2CDProtocolError(f"SETLS応答が2進文字列ではありません: {raw!r}")
        status = (int(raw, 2) >> 4) & 0x7
        status <<= 2
        if raw[0] == "1":
            status |= 0x03
        return status

    def pause(self) -> None:
        self.communication.send("PAUSE ON")

    def resume(self) -> None:
        self.communication.send("PAUSE OFF")

    def pause_status(self) -> str:
        return self.communication.query("PAUSE?")

    def all_reply(self, enabled: bool) -> None:
        self.communication.send("ALL_REP EN" if enabled else "ALL_REP DS")

    def all_reply_status(self) -> str:
        return self.communication.query("ALL_REP?")

    def hold(self, motor: int) -> str:
        return self._query_motor_command("HOLD?", motor)

    def set_hold(self, motor: int, enabled: bool) -> None:
        self._check_motor(motor)
        self.communication.send(f"HOLD{motor:X}{'ON' if enabled else 'OFF'}")

    def hold_on_time(self, motor: int) -> int:
        return int(self._query_motor_command("HOLDTM?", motor))

    def set_hold_on_time(self, motor: int, msec: int) -> None:
        self._send_motor_value("HOLDTM", motor, msec)

    def hold_off_time(self, motor: int) -> int:
        return int(self._query_motor_command("H_OFTM?", motor))

    def set_hold_off_time(self, motor: int, msec: int) -> None:
        self._send_motor_value("H_OFTM", motor, msec)

    def display(self) -> str:
        return self.communication.query("SETCH?")

    def set_display(self, display: str) -> None:
        if not display:
            raise ValueError("表示チャンネル文字列は空にできません")
        self.communication.send(f"SETCH{display}")

    def ttl_mode(self, motor: int) -> int:
        return int(self._query_motor_command("TMGM?", motor))

    def set_ttl_mode(self, motor: int, mode: int) -> None:
        self._send_motor_value("TMGM", motor, mode)

    def ttl_start_pulse(self, motor: int) -> int:
        return int(self._query_motor_command("TMGS?", motor))

    def set_ttl_start_pulse(self, motor: int, pulse: int) -> None:
        self._send_motor_value("TMGS", motor, pulse)

    def ttl_end_pulse(self, motor: int) -> int:
        return int(self._query_motor_command("TMGE?", motor))

    def set_ttl_end_pulse(self, motor: int, pulse: int) -> None:
        self._send_motor_value("TMGE", motor, pulse)

    def ttl_period(self, motor: int) -> int:
        return int(self._query_motor_command("TMGI?", motor))

    def set_ttl_period(self, motor: int, pulse: int) -> None:
        self._send_motor_value("TMGI", motor, pulse)

    def ttl_output_start(self, motor: int) -> None:
        self._send_motor_command("TMGR", motor)

    def ttl_output_stop(self, motor: int) -> None:
        self._send_motor_command("TMGC", motor)

    def ttl_status(self, motor: int) -> int:
        raw = self._query_motor_command("TMGR?", motor)
        if raw == "YES":
            return 1
        if raw == "NO":
            return 0
        raise PM2CDProtocolError(f"TTL状態応答を解釈できません: {raw!r}")

    def timing_fixed_output(self, enabled: bool) -> None:
        self.communication.send("TMGFX EN" if enabled else "TMGFX DS")

    def timing_fixed_output_status(self) -> str:
        return self.communication.query("TMGFX?")

    def timing_output_channels(self) -> str:
        return self.communication.query("TMGCH?")

    def set_timing_output_channels(self, channels: str) -> None:
        if len(channels) != 4:
            raise ValueError("channelsは4文字で指定してください")
        self.communication.send(f"TMGCH{channels}")

    def change_speed_while_moving(self, motor: int, speed: int) -> None:
        self._send_motor_value("SPC", motor, speed)

    def srq_output(self) -> str:
        return self.communication.query("SRQ_OUT?")

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

    def _send_motor_command(self, command: str, motor: int) -> None:
        self._check_motor(motor)
        self.communication.send(f"{command}{motor:X}")

    def _send_motor_value(self, command: str, motor: int, value: int) -> None:
        self._check_motor(motor)
        self.communication.send(f"{command}{motor:X}{value}")

    def _query_motor_command(self, command: str, motor: int) -> str:
        self._check_motor(motor)
        return self.communication.query(f"{command}{motor:X}")

    def _check_motor(self, motor: int) -> None:
        if motor < 0 or motor >= self.channel_count:
            raise ValueError(f"motorは0から{self.channel_count - 1}の範囲で指定してください")

    @staticmethod
    def _normalize_side(side: str) -> str:
        side = side.lower()
        if side not in ("cw", "ccw"):
            raise ValueError("sideは'cw'または'ccw'で指定してください")
        return side

    @staticmethod
    def _direction(direction: str) -> str:
        direction = direction.lower()
        if direction in ("+", "plus", "cw", "p"):
            return "+"
        if direction in ("-", "minus", "ccw", "n"):
            return "-"
        raise ValueError("directionは'+'/'-'/'cw'/'ccw'で指定してください")

    @staticmethod
    def _backlash_suffix(backlash: str | bool) -> str:
        if backlash is True:
            return "B"
        if backlash is False or backlash is None:
            return ""
        backlash = backlash.upper()
        if backlash in ("", "B", "S"):
            return backlash
        raise ValueError("backlashはTrue/False/'B'/'S'で指定してください")
