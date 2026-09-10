import time
from typing import List, Optional, Union

from .core.communication_tcp import Communication
from .core.controller_status import ControllerStatus
from .core.home_status import HomeStatus
from .core.limit_switch_setting import LimitSwitchSetting
from .core.motor_setting import MotorSetting
from .core.motor_status import MotorStatus
from .core.stop_mode import StopMode
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
            raise ValueError("PM2CDのchannel_countは2です",)

        self._communication = Communication(
            ip_address=ip_address,
            port=port,
            timeout_sec=timeout_sec,
        )
        self._communication.connect()
        self._device = PM2CDDevice(
            communication=self._communication,
            channel_count=channel_count,
            logger=logger,
            log_level=log_level,
        )

    @property
    def is_connected(self,) -> bool:
        return self._communication.is_connected

    def close(self,) -> None:
        self._communication.close()

    def remote(self,) -> None:
        self._device.remote()

    def local(self,) -> None:
        self._device.local()

    def version(self,) -> VersionInfo:
        return self._device.version()

    def hardware_version(self,) -> str:
        return self._device.hardware_version()

    def controller_status(self,) -> ControllerStatus:
        return self._device.controller_status()

    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self._device.move(motor, pulse, backlash,)

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> None:
        self._device.move_relative(motor, pulse, backlash,)

    def scan(self, motor: int, direction: str,) -> None:
        self._device.scan(motor, direction,)

    def constant_speed_scan(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._device.constant_speed_scan(motor, direction,)

    def jog(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._device.jog(motor, direction,)

    def scan_home(
        self,
        motor: int,
        direction: str,
    ) -> None:
        self._device.scan_home(motor, direction,)

    def home(
        self,
        motor: int,
    ) -> None:
        self._device.home(motor,)

    def find_home(
        self,
        motor: int,
    ) -> None:
        self._device.find_home(motor,)

    def stop(
        self,
        motor: int,
    ) -> None:
        self._device.stop(motor,)

    def stop_all(self,) -> None:
        self._device.stop_all()

    def emergency_stop(
        self,
        motor: int,
    ) -> None:
        self._device.emergency_stop(motor,)

    def emergency_stop_all(self,) -> None:
        self._device.emergency_stop_all()

    def status(
        self,
        motor: int,
    ) -> MotorStatus:
        return self._device.status(motor,)

    def status_all(self,) -> List[MotorStatus]:
        return self._device.status_all()

    def check_rotate(
        self,
        motor: int,
    ) -> bool:
        return self._device.check_rotate(motor,)

    def is_busy(
        self,
        motor: int,
    ) -> bool:
        return self.status(motor,).is_busy

    def wait_stop(
        self,
        motor: int,
        timeout_sec: float = 30.0,
        interval_sec: float = 0.1,
    ) -> MotorStatus:
        deadline = time.monotonic() + timeout_sec
        while True:
            status = self.status(motor,)
            if not status.is_busy:
                return status
            if time.monotonic() >= deadline:
                raise TimeoutError(f"motor {motor} が停止しませんでした",)
            time.sleep(interval_sec,)

    def position(
        self,
        motor: int,
    ) -> int:
        return self._device.position(motor,)

    def set_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._device.set_position(motor, pulse,)

    def zero_position(
        self,
        motor: int,
    ) -> None:
        self.set_position(motor, 0,)

    def set_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._device.set_speed(motor, speed,)

    def set_speed_profile(
        self,
        motor: int,
        low_speed: int,
        middle_speed: int,
        high_speed: int,
    ) -> None:
        self._device.set_speed_profile(motor, low_speed, middle_speed, high_speed,)

    def high_speed(
        self,
        motor: int,
    ) -> int:
        return self._device.high_speed(motor,)

    def set_high_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._device.set_high_speed(motor, speed,)

    def middle_speed(
        self,
        motor: int,
    ) -> int:
        return self._device.middle_speed(motor,)

    def set_middle_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._device.set_middle_speed(motor, speed,)

    def low_speed(
        self,
        motor: int,
    ) -> int:
        return self._device.low_speed(motor,)

    def set_low_speed(
        self,
        motor: int,
        speed: int,
    ) -> None:
        self._device.set_low_speed(motor, speed,)

    def speed_mode(
        self,
        motor: int,
    ) -> str:
        return self._device.speed_mode(motor,)

    def set_speed_mode(
        self,
        motor: int,
        mode: Union[int, str],
    ) -> None:
        self._device.set_speed_mode(motor, mode,)

    def rate_number(
        self,
        motor: int,
    ) -> int:
        return self._device.rate_number(motor,)

    def set_rate_number(
        self,
        motor: int,
        number: int,
    ) -> None:
        self._device.set_rate_number(motor, number,)

    def backlash(
        self,
        motor: int,
    ) -> int:
        return self._device.backlash(motor,)

    def set_backlash(
        self,
        motor: int,
        backlash: int,
    ) -> None:
        self._device.set_backlash(motor, backlash,)

    def limit(
        self,
        motor: int,
        side: str,
    ) -> int:
        return self._device.limit(motor, side,)

    def set_limit(
        self,
        motor: int,
        side: str,
        pulse: int,
    ) -> None:
        self._device.set_limit(motor, side, pulse,)

    def pause(self,) -> None:
        self._device.pause()

    def resume(self,) -> None:
        self._device.resume()

    def pause_status(self,) -> str:
        return self._device.pause_status()

    def hold(self, motor: int,) -> str:
        return self._device.hold(motor,)

    def set_hold(
        self,
        motor: int,
        enabled: bool,
    ) -> None:
        self._device.set_hold(motor, enabled,)

    def hold_on_time(
        self,
        motor: int,
    ) -> int:
        return self._device.hold_on_time(motor,)

    def set_hold_on_time(
        self,
        motor: int,
        msec: int,
    ) -> None:
        self._device.set_hold_on_time(motor, msec,)

    def hold_off_time(
        self,
        motor: int,
    ) -> int:
        return self._device.hold_off_time(motor,)

    def set_hold_off_time(
        self,
        motor: int,
        msec: int,
    ) -> None:
        self._device.set_hold_off_time(motor, msec,)

    def home_status(self, motor: int,) -> HomeStatus:
        return self._device.home_status(motor,)

    def set_home_status(
        self,
        motor: int,
        found: bool,
        found_direction: str,
        auto_start_direction: str,
    ) -> None:
        self._device.set_home_status(
            motor,
            found,
            found_direction,
            auto_start_direction,
        )

    def home_position(
        self,
        motor: int,
    ) -> Optional[int]:
        return self._device.home_position(motor,)

    def set_home_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._device.set_home_position(motor, pulse,)

    def home_offset(
        self,
        motor: int,
    ) -> int:
        return self._device.home_offset(motor,)

    def set_home_offset(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._device.set_home_offset(motor, pulse,)

    def preset_position(
        self,
        motor: int,
    ) -> int:
        return self._device.preset_position(motor,)

    def set_preset_position(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._device.set_preset_position(motor, pulse,)

    def jog_pulse(
        self,
        motor: int,
    ) -> int:
        return self._device.jog_pulse(motor,)

    def set_jog_pulse(
        self,
        motor: int,
        pulse: int,
    ) -> None:
        self._device.set_jog_pulse(motor, pulse,)

    def limit_switch_setting(
        self,
        motor: int,
    ) -> LimitSwitchSetting:
        return self._device.limit_switch_setting(motor,)

    def set_limit_switch_setting_raw(
        self,
        motor: int,
        setting: str,
    ) -> None:
        self._device.set_limit_switch_setting_raw(motor, setting,)

    def motor_setting(
        self,
        motor: int,
    ) -> MotorSetting:
        return self._device.motor_setting(motor,)

    def set_motor_setting(
        self,
        motor: int,
        drive_enabled: bool,
        hold_mode: int,
        output_mode: int,
    ) -> None:
        self._device.set_motor_setting(
            motor,
            drive_enabled,
            hold_mode,
            output_mode,
        )

    def stop_mode(
        self,
        motor: int,
    ) -> StopMode:
        return self._device.stop_mode(motor,)

    def set_stop_mode(
        self,
        motor: int,
        panel_fast: bool,
        limit_fast: bool,
    ) -> None:
        self._device.set_stop_mode(motor, panel_fast, limit_fast,)

    def number_to_rate(
        self,
        index: int,
    ) -> float:
        return self._device.number_to_rate(index,)

    def rate_to_number(
        self,
        rate: float,
    ) -> int:
        return self._device.rate_to_number(rate,)

    def __enter__(self,) -> "PM2CD":
        return self

    def __exit__(self, exc_type, exc_value, traceback,) -> None:
        self.close()
