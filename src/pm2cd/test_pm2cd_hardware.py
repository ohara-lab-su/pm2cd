import time

from .pm2cd_ctrl import PM2CD


class PM2CDHardwareTest:
    """PM2CD の公開 I/F を実機で確認する。"""

    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        motor: int = 0,
        test_pulse: int = 10,
        scan_time_sec: float = 0.2,
        motion_timeout_sec: float = 30.0,
        enable_home_tests: bool = False,
    ):
        self.ctrl = PM2CD(
            ip_address=ip_address,
            port=port,
            timeout_sec=timeout_sec,
        )
        self.motor = motor
        self.test_pulse = test_pulse
        self.scan_time_sec = scan_time_sec
        self.motion_timeout_sec = motion_timeout_sec
        self.enable_home_tests = enable_home_tests

    @staticmethod
    def _show(name: str, value) -> None:
        print("[PASS] {}: {}".format(name, value))

    def _ensure_remote_and_stopped(self) -> None:
        self.ctrl.emergency_stop_all()
        time.sleep(0.05)
        self.ctrl.remote()
        status = self.ctrl.status(self.motor)
        if status.remote_local != "R":
            raise AssertionError("REMOTEへ移行していません: {!r}".format(status.raw))
        if status.is_busy:
            raise AssertionError("motor {} が停止していません".format(self.motor))

    def _wait(self) -> None:
        self.ctrl.wait_stop(
            self.motor,
            timeout_sec=self.motion_timeout_sec,
        )

    def test_connection(self) -> None:
        if not self.ctrl.is_connected:
            raise AssertionError("TCP接続されていません")
        self._show("is_connected", self.ctrl.is_connected)

    def test_version(self) -> None:
        value = self.ctrl.version()
        if not value.is_pm2cd:
            raise AssertionError("PM2CD系のVER?応答ではありません: {!r}".format(value.raw))
        self._show("version", value.raw)
        self._show("hardware_version", self.ctrl.hardware_version())

    def test_remote_local(self) -> None:
        self.ctrl.stop_all()
        self.ctrl.local()
        status = self.ctrl.status(self.motor)
        if status.remote_local != "L":
            raise AssertionError("LOC後もLOCALではありません")
        self.ctrl.remote()
        status = self.ctrl.status(self.motor)
        if status.remote_local != "R":
            raise AssertionError("REM後もREMOTEではありません")
        self._show("remote/local", status.raw)

    def test_controller_status(self) -> None:
        value = self.ctrl.controller_status()
        self._show("controller_status", value)

    def test_status(self) -> None:
        value = self.ctrl.status(self.motor)
        self._show("status", value)
        values = self.ctrl.status_all()
        if len(values) != 2:
            raise AssertionError("status_allの軸数が2ではありません")
        self._show("status_all", values)
        self._show("check_rotate", self.ctrl.check_rotate(self.motor))
        self._show("is_busy", self.ctrl.is_busy(self.motor))

    def test_position(self) -> None:
        original = self.ctrl.position(self.motor)
        self.ctrl.set_position(self.motor, original)
        actual = self.ctrl.position(self.motor)
        if actual != original:
            raise AssertionError("PS read-back不一致")
        self._show("position/set_position", actual)

    def test_zero_position(self) -> None:
        original = self.ctrl.position(self.motor)
        try:
            self.ctrl.zero_position(self.motor)
            if self.ctrl.position(self.motor) != 0:
                raise AssertionError("zero_positionに失敗しました")
        finally:
            self.ctrl.set_position(self.motor, original)
        self._show("zero_position", "OK")

    def test_speed(self) -> None:
        high = self.ctrl.high_speed(self.motor)
        middle = self.ctrl.middle_speed(self.motor)
        low = self.ctrl.low_speed(self.motor)
        self.ctrl.set_high_speed(self.motor, high)
        self.ctrl.set_middle_speed(self.motor, middle)
        self.ctrl.set_low_speed(self.motor, low)
        self.ctrl.set_speed_profile(self.motor, low, middle, high)
        self._show("speed", (low, middle, high))

    def test_set_speed(self) -> None:
        original_high = self.ctrl.high_speed(self.motor)
        original_middle = self.ctrl.middle_speed(self.motor)
        original_low = self.ctrl.low_speed(self.motor)
        try:
            self.ctrl.set_speed(self.motor, original_high)
            expected_middle = original_high // 3
            if expected_middle < 5:
                expected_middle = 5
            expected_low = original_high // 10
            if expected_low < 5:
                expected_low = 5
            if self.ctrl.middle_speed(self.motor) != expected_middle:
                raise AssertionError("set_speed MSPD不一致")
            if self.ctrl.low_speed(self.motor) != expected_low:
                raise AssertionError("set_speed LSPD不一致")
        finally:
            self.ctrl.set_speed_profile(
                self.motor,
                original_low,
                original_middle,
                original_high,
            )
        self._show("set_speed", "OK")

    def test_speed_mode(self) -> None:
        original = self.ctrl.speed_mode(self.motor)
        self.ctrl.set_speed_mode(self.motor, original)
        actual = self.ctrl.speed_mode(self.motor)
        if actual != original:
            raise AssertionError("speed_mode read-back不一致")
        self._show("speed_mode", actual)

    def test_rate(self) -> None:
        original = self.ctrl.rate_number(self.motor)
        self.ctrl.set_rate_number(self.motor, original)
        actual = self.ctrl.rate_number(self.motor)
        if actual != original:
            raise AssertionError("rate read-back不一致")
        rate = self.ctrl.number_to_rate(actual)
        number = self.ctrl.rate_to_number(rate)
        if number != actual:
            raise AssertionError("RATE変換不一致")
        self._show("rate", (actual, rate))

    def test_backlash(self) -> None:
        original = self.ctrl.backlash(self.motor)
        self.ctrl.set_backlash(self.motor, original)
        actual = self.ctrl.backlash(self.motor)
        if actual != original:
            raise AssertionError("backlash read-back不一致")
        self._show("backlash", actual)

    def test_limit(self) -> None:
        cw = self.ctrl.limit(self.motor, "cw")
        ccw = self.ctrl.limit(self.motor, "ccw")
        self.ctrl.set_limit(self.motor, "cw", cw)
        self.ctrl.set_limit(self.motor, "ccw", ccw)
        if self.ctrl.limit(self.motor, "cw") != cw:
            raise AssertionError("CW digital limit read-back不一致")
        if self.ctrl.limit(self.motor, "ccw") != ccw:
            raise AssertionError("CCW digital limit read-back不一致")
        self._show("limit", (cw, ccw))

    def test_pause(self) -> None:
        original = self.ctrl.pause_status()
        self.ctrl.pause()
        if self.ctrl.pause_status() != "ON":
            raise AssertionError("PAUSE ONに失敗しました")
        self.ctrl.resume()
        if self.ctrl.pause_status() != "OFF":
            raise AssertionError("PAUSE OFFに失敗しました")
        if original == "ON":
            self.ctrl.pause()
        self._show("pause/resume", original)

    def test_hold(self) -> None:
        original = self.ctrl.hold(self.motor)
        enabled = False
        if original == "ON":
            enabled = True
        self.ctrl.set_hold(self.motor, enabled)
        if self.ctrl.hold(self.motor) != original:
            raise AssertionError("HOLD read-back不一致")
        self._show("hold", original)

    def test_hold_time(self) -> None:
        on_time = self.ctrl.hold_on_time(self.motor)
        off_time = self.ctrl.hold_off_time(self.motor)
        self.ctrl.set_hold_on_time(self.motor, on_time)
        self.ctrl.set_hold_off_time(self.motor, off_time)
        if self.ctrl.hold_on_time(self.motor) != on_time:
            raise AssertionError("HOLD ON time read-back不一致")
        if self.ctrl.hold_off_time(self.motor) != off_time:
            raise AssertionError("HOLD OFF time read-back不一致")
        self._show("hold_time", (on_time, off_time))

    def test_home_parameters(self) -> None:
        status = self.ctrl.home_status(self.motor)
        offset = self.ctrl.home_offset(self.motor)
        position = self.ctrl.home_position(self.motor)
        self.ctrl.set_home_status(
            self.motor,
            status.found,
            status.found_direction,
            status.auto_start_direction,
        )
        self.ctrl.set_home_offset(self.motor, offset)
        if position is not None:
            self.ctrl.set_home_position(self.motor, position)
        self._show("home_parameters", (status, position, offset))

    def test_local_parameters(self) -> None:
        preset = self.ctrl.preset_position(self.motor)
        jog_pulse = self.ctrl.jog_pulse(self.motor)
        self.ctrl.set_preset_position(self.motor, preset)
        self.ctrl.set_jog_pulse(self.motor, jog_pulse)
        if self.ctrl.preset_position(self.motor) != preset:
            raise AssertionError("SPRS read-back不一致")
        if self.ctrl.jog_pulse(self.motor) != jog_pulse:
            raise AssertionError("SETJG read-back不一致")
        self._show("local_parameters", (preset, jog_pulse))

    def test_limit_switch_setting(self) -> None:
        value = self.ctrl.limit_switch_setting(self.motor)
        self.ctrl.set_limit_switch_setting_raw(self.motor, value.raw)
        actual = self.ctrl.limit_switch_setting(self.motor)
        if actual.raw != value.raw:
            raise AssertionError("SETLS read-back不一致")
        self._show("limit_switch_setting", actual)

    def test_motor_setting(self) -> None:
        value = self.ctrl.motor_setting(self.motor)
        self.ctrl.set_motor_setting(
            self.motor,
            value.drive_enabled,
            value.hold_mode,
            value.output_mode,
        )
        actual = self.ctrl.motor_setting(self.motor)
        if actual.raw != value.raw:
            raise AssertionError("SETMT read-back不一致")
        self._show("motor_setting", actual)

    def test_stop_mode(self) -> None:
        value = self.ctrl.stop_mode(self.motor)
        self.ctrl.set_stop_mode(
            self.motor,
            value.panel_fast,
            value.limit_fast,
        )
        actual = self.ctrl.stop_mode(self.motor)
        if actual.raw != value.raw:
            raise AssertionError("STOPMD read-back不一致")
        self._show("stop_mode", actual)

    def test_jog(self) -> None:
        self._ensure_remote_and_stopped()
        before = self.ctrl.position(self.motor)
        self.ctrl.jog(self.motor, "cw")
        self._wait()
        after = self.ctrl.position(self.motor)
        if after != before + 1:
            raise AssertionError("JOGPは1 pulseではありません")
        self.ctrl.jog(self.motor, "ccw")
        self._wait()
        self._show("jog", (before, after))

    def test_move(self) -> None:
        self._ensure_remote_and_stopped()
        before = self.ctrl.position(self.motor)
        target = before + self.test_pulse
        if target > 8_388_607:
            target = before - self.test_pulse
        self.ctrl.move(self.motor, target, backlash=False)
        self._wait()
        if self.ctrl.position(self.motor) != target:
            raise AssertionError("ABS移動位置不一致")
        self.ctrl.move(self.motor, before, backlash=False)
        self._wait()
        self._show("move", "OK")

    def test_move_relative(self) -> None:
        self._ensure_remote_and_stopped()
        before = self.ctrl.position(self.motor)
        self.ctrl.move_relative(self.motor, self.test_pulse, backlash=False)
        self._wait()
        if self.ctrl.position(self.motor) != before + self.test_pulse:
            raise AssertionError("REL移動位置不一致")
        self.ctrl.move_relative(self.motor, -self.test_pulse, backlash=False)
        self._wait()
        self._show("move_relative", "OK")

    def test_scan_and_stop(self) -> None:
        self._ensure_remote_and_stopped()
        self.ctrl.scan(self.motor, "cw")
        time.sleep(self.scan_time_sec)
        self.ctrl.stop(self.motor)
        self._wait()
        self.ctrl.constant_speed_scan(self.motor, "ccw")
        time.sleep(self.scan_time_sec)
        self.ctrl.stop_all()
        self._wait()
        self._show("scan/constant_speed_scan/stop/stop_all", "OK")

    def test_emergency_stop(self) -> None:
        self._ensure_remote_and_stopped()
        self.ctrl.scan(self.motor, "cw")
        time.sleep(self.scan_time_sec)
        self.ctrl.emergency_stop(self.motor)
        self._wait()
        self.ctrl.scan(self.motor, "ccw")
        time.sleep(self.scan_time_sec)
        self.ctrl.emergency_stop_all()
        self._wait()
        self._show("emergency_stop/emergency_stop_all", "OK")

    def test_home_motion(self) -> None:
        if not self.enable_home_tests:
            self._show("home motion", "SKIP")
            return
        self._ensure_remote_and_stopped()
        self.ctrl.scan_home(self.motor, "cw")
        self._wait()
        self.ctrl.find_home(self.motor)
        self._wait()
        self.ctrl.home(self.motor)
        self._wait()
        self._show("scan_home/find_home/home", "OK")

    def run_all(self) -> None:
        tests = [
            self.test_connection,
            self.test_version,
            self.test_remote_local,
            self.test_controller_status,
            self.test_status,
            self.test_position,
            self.test_zero_position,
            self.test_speed,
            self.test_set_speed,
            self.test_speed_mode,
            self.test_rate,
            self.test_backlash,
            self.test_limit,
            self.test_pause,
            self.test_hold,
            self.test_hold_time,
            self.test_home_parameters,
            self.test_local_parameters,
            self.test_limit_switch_setting,
            self.test_motor_setting,
            self.test_stop_mode,
            self.test_jog,
            self.test_move,
            self.test_move_relative,
            self.test_scan_and_stop,
            self.test_emergency_stop,
            self.test_home_motion,
        ]
        try:
            for test in tests:
                test()
        finally:
            try:
                self.ctrl.emergency_stop_all()
            finally:
                self.ctrl.close()
