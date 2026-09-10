import time
from typing import Union

from .core.communication_tcp import Communication
from .core.motor_status import MotorStatus
from .core.version_info import VersionInfo
from .pm2cd_device import PM2CDDevice


class PM2CD:
    """PM2CD を Python から制御するための公開 I/F。"""

    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        channel_count: int = 2,
        logger=None,
        log_level: str = "INFO",
    ):
        if channel_count != 2:
            raise ValueError("PM2CDのchannel_countは2です")

        self.communication = Communication(
            ip_address=ip_address,
            port=port,
            timeout_sec=timeout_sec,
        )
        self.communication.connect()
        self.device = PM2CDDevice(
            communication=self.communication,
            channel_count=channel_count,
            logger=logger,
            log_level=log_level,
        )

    @property
    def is_connected(self) -> bool:
        return self.communication.is_connected

    def close(self) -> None:
        self.communication.close()

    def remote(self) -> None:
        self.device.remote()

    def local(self) -> None:
        self.device.local()

    def version(self) -> VersionInfo:
        return self.device.version()

    def hardware_version(self) -> str:
        return self.device.hardware_version()

    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self.device.move(motor, pulse, backlash)

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self.device.move_relative(motor, pulse, backlash)

    def scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self.device.scan(motor, direction)

    def constant_speed_scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self.device.constant_speed_scan(motor, direction)

    def jog(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self.device.jog(motor, direction)

    def home(
        self,
        motor: int,
    ) -> None:
        self.device.home(motor)

    def find_home(
        self,
        motor: int,
    ) -> None:
        self.device.find_home(motor)

    def stop(
        self,
        motor: int,
    ) -> None:
        self.device.stop(motor)

    def stop_all(self) -> None:
        self.device.stop_all()

    def emergency_stop(
        self,
        motor: int,
    ) -> None:
        self.device.emergency_stop(motor)

    def emergency_stop_all(self) -> None:
        self.device.emergency_stop_all()

    def status(
        self,
        motor: int,
    ) -> MotorStatus:
        return self.device.status(motor)

    def status_all(self) -> list[MotorStatus]:
        return self.device.status_all()

    def is_busy(
        self,
        motor: int,
    ) -> bool:
        return self.status(motor).is_busy

    def wait_stop(
        self,
        motor: int,
        timeout_sec: float = 30.0,
        interval_sec: float = 0.1,
    ) -> MotorStatus:
        deadline = time.monotonic() + timeout_sec
        while True:
            status = self.status(motor)
            if not status.is_busy:
                return status
            if time.monotonic() >= deadline:
                raise TimeoutError(f"motor {motor} が停止しませんでした")
            time.sleep(interval_sec)

    def position(
        self,
        motor: int,
    ) -> int:
        return self.device.position(motor)

    def set_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self.device.set_position(motor, pulse)

    def zero_position(self, motor: int) -> None:
        self.set_position(motor, 0)

    def set_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self.device.set_speed(motor, speed)

    def set_speed_profile(
        self,
        motor: int,
        low_speed: int,
        middle_speed: int,
        high_speed: int,
    ) -> None:
        self.device.set_speed_profile(motor, low_speed, middle_speed, high_speed)

    def high_speed(
        self,
        motor: int,
    ) -> int:
        return self.device.high_speed(motor)

    def set_high_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self.device.set_high_speed(motor, speed)

    def middle_speed(
        self,
        motor: int,
    ) -> int:
        return self.device.middle_speed(motor)

    def set_middle_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self.device.set_middle_speed(motor, speed)

    def low_speed(
        self,
        motor: int,
    ) -> int:
        return self.device.low_speed(motor)

    def set_low_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self.device.set_low_speed(motor, speed)

    def speed_mode(
        self,
        motor: int,
    ) -> str:
        return self.device.speed_mode(motor)

    def set_speed_mode(
        self,
        motor: int,
        mode: Union[int, str],
    ) -> None:
        self.device.set_speed_mode(motor, mode)

    def rate_number(
        self,
        motor: int,
    ) -> int:
        return self.device.rate_number(motor)

    def set_rate_number(
        self,
        motor: int,
        number: int,
    ) -> None:
        self.device.set_rate_number(motor, number)

    def backlash(
        self,
        motor: int,
    ) -> int:
        return self.device.backlash(motor)

    def set_backlash(
        self,
        motor: int,
        backlash: int,
    ) -> None:
        self.device.set_backlash(motor, backlash)

    def limit(
        self,
        motor: int,
        side: str,
    ) -> int:
        return self.device.limit(motor, side)

    def set_limit(
        self,
        motor: int,
        side: str,
        pulse: int,
    ) -> None:
        self.device.set_limit(motor, side, pulse)

    def pause(self) -> None:
        self.device.pause()

    def resume(self) -> None:
        self.device.resume()

    def pause_status(self) -> str:
        return self.device.pause_status()

    def hold(
        self,
        motor: int,
    ) -> str:
        return self.device.hold(motor)

    def set_hold(
        self,
        motor: int,
        enabled: bool,
    ) -> None:
        self.device.set_hold(motor, enabled)

    def number_to_rate(
        self,
        index: int,
    ) -> float:
        return self.device.number_to_rate(index)

    def rate_to_number(
        self,
        rate: float,
    ) -> int:
        return self.device.rate_to_number(rate)

    def __enter__(self) -> "PM2CD":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
