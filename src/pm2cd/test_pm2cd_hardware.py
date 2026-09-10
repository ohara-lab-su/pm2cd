import time
from typing import Callable, Optional

from .pm2cd_ctrl import PM2CD


class PM2CDHardwareTest:
    """PM2CD の公開 I/F を実機に接続して確認するテストクラス。

    モック通信は使用しない。書込み系は可能な限り対応する読出しコマンド、
    または STS? / PS? により実機側の状態変化を確認する。
    """

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
        print(f"[PASS] {name}: {value}")

    def _status_text(self, motor: Optional[int] = None) -> str:
        if motor is None:
            motor = self.motor
        status = self.ctrl.status(motor)
        return repr(status)

    def _ensure_remote_and_stopped(self) -> None:
        self.ctrl.emergency_stop_all()
        time.sleep(0.05)
        self.ctrl.remote()
        status = self.ctrl.status(self.motor)
        if status.remote_local != "R":
            raise AssertionError(f"REMOTEへ移行していません: {status.raw!r}")
        if status.is_busy:
            raise AssertionError(f"motor {self.motor} が停止していません: {status!r}")

    def _temporary_low_motion_speed(self) -> tuple[str, int]:
        old_mode = self.ctrl.speed_mode(self.motor)
        old_low = self.ctrl.low_speed(self.motor)
        test_low = min(max(50, 5), 100_000)
        self.ctrl.set_low_speed(self.motor, test_low)
        self.ctrl.set_speed_mode(self.motor, "L")
        return old_mode, old_low

    def _restore_motion_speed(self, old_mode: str, old_low: int) -> None:
        self.ctrl.set_low_speed(self.motor, old_low)
        self.ctrl.set_speed_mode(self.motor, old_mode)

    def test_is_connected(self) -> None:
        if not self.ctrl.is_connected:
            raise AssertionError("TCP接続されていません")
        self._show("is_connected", self.ctrl.is_connected)

    def test_version(self) -> None:
        result = self.ctrl.version()
        if not result.is_pm2cd:
            raise AssertionError(f"PM2CD系のVER?応答ではありません: {result.raw!r}")
        self._show("version", result.raw)

    def test_hardware_version(self) -> None:
        result = self.ctrl.hardware_version()
        if not result.startswith("HD-VER"):
            raise AssertionError(f"VERH?応答が不正です: {result!r}")
        self._show("hardware_version", result)

    def test_local(self) -> None:
        self.ctrl.stop_all()
        self.ctrl.local()
        status = self.ctrl.status(self.motor)
        if status.remote_local != "L":
            raise AssertionError(f"LOC後もLOCALではありません: {status.raw!r}")
        self._show("local", status.raw)
        self.ctrl.remote()

    def test_remote(self) -> None:
        self.ctrl.stop_all()
        self.ctrl.remote()
        status = self.ctrl.status(self.motor)
        if status.remote_local != "R":
            raise AssertionError(f"REM後もREMOTEではありません: {status.raw!r}")
        self._show("remote", status.raw)

    def test_status(self) -> None:
        status = self.ctrl.status(self.motor)
        self._show("status", repr(status))
        print(f"       raw STS?: {status.raw}")

    def test_status_all(self) -> None:
        statuses = self.ctrl.status_all()
        if len(statuses) != 2:
            raise AssertionError(f"PM2CDなのにstatus数が2ではありません: {len(statuses)}")
        self._show("status_all", statuses)
        print(f"       raw STS?: {statuses[0].raw}")

    def test_is_busy(self) -> None:
        value = self.ctrl.is_busy(self.motor)
        self._show("is_busy", value)

    def test_wait_stop(self) -> None:
        status = self.ctrl.wait_stop(
            self.motor,
            timeout_sec=self.motion_timeout_sec,
        )
        if status.is_busy:
            raise AssertionError(f"wait_stop後もBUSYです: {status!r}")
        self._show("wait_stop", repr(status))

    def test_position(self) -> None:
        value = self.ctrl.position(self.motor)
        self._show("position", value)

    def test_set_position(self) -> None:
        original = self.ctrl.position(self.motor)
        test_value = original + 1 if original < 8_388_607 else original - 1
        try:
            self.ctrl.set_position(self.motor, test_value)
            actual = self.ctrl.position(self.motor)
            if actual != test_value:
                raise AssertionError(f"PS設定不一致: expected={test_value}, actual={actual}")
            self._show("set_position", actual)
        finally:
            self.ctrl.set_position(self.motor, original)

    def test_zero_position(self) -> None:
        original = self.ctrl.position(self.motor)
        try:
            self.ctrl.zero_position(self.motor)
            actual = self.ctrl.position(self.motor)
            if actual != 0:
                raise AssertionError(f"zero_position後の位置が0ではありません: {actual}")
            self._show("zero_position", actual)
        finally:
            self.ctrl.set_position(self.motor, original)

    def test_jog(self) -> None:
        self._ensure_remote_and_stopped()
        before = self.ctrl.position(self.motor)
        self.ctrl.jog(self.motor, "cw")
        self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
        after = self.ctrl.position(self.motor)
        if after != before + 1:
            raise AssertionError(f"JOGPは1 pulseのはずです: before={before}, after={after}")
        self._show("jog", f"{before} -> {after}")

    def test_move_relative(self) -> None:
        self._ensure_remote_and_stopped()
        before = self.ctrl.position(self.motor)
        self.ctrl.move_relative(self.motor, self.test_pulse, backlash=False)
        self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
        after = self.ctrl.position(self.motor)
        expected = before + self.test_pulse
        if after != expected:
            raise AssertionError(f"REL位置不一致: expected={expected}, actual={after}")
        self._show("move_relative", f"{before} -> {after}")
        self.ctrl.move_relative(self.motor, -self.test_pulse, backlash=False)
        self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)

    def test_move(self) -> None:
        self._ensure_remote_and_stopped()
        before = self.ctrl.position(self.motor)
        target = before + self.test_pulse
        if target > 8_388_607:
            target = before - self.test_pulse
        self.ctrl.move(self.motor, target, backlash=False)
        self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
        after = self.ctrl.position(self.motor)
        if after != target:
            raise AssertionError(f"ABS位置不一致: expected={target}, actual={after}")
        self._show("move", f"{before} -> {after}")
        self.ctrl.move(self.motor, before, backlash=False)
        self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)

    def test_scan(self) -> None:
        self._ensure_remote_and_stopped()
        old_mode, old_low = self._temporary_low_motion_speed()
        before = self.ctrl.position(self.motor)
        try:
            self.ctrl.scan(self.motor, "cw")
            time.sleep(self.scan_time_sec)
            self.ctrl.stop(self.motor)
            self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
            after = self.ctrl.position(self.motor)
            if after == before:
                raise AssertionError("SCANで位置が変化していません")
            self._show("scan", f"{before} -> {after}; {self._status_text()}")
        finally:
            self.ctrl.emergency_stop(self.motor)
            self._restore_motion_speed(old_mode, old_low)

    def test_constant_speed_scan(self) -> None:
        self._ensure_remote_and_stopped()
        old_mode, old_low = self._temporary_low_motion_speed()
        before = self.ctrl.position(self.motor)
        try:
            self.ctrl.constant_speed_scan(self.motor, "ccw")
            time.sleep(self.scan_time_sec)
            self.ctrl.stop(self.motor)
            self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
            after = self.ctrl.position(self.motor)
            if after == before:
                raise AssertionError("CSCANで位置が変化していません")
            self._show("constant_speed_scan", f"{before} -> {after}; {self._status_text()}")
        finally:
            self.ctrl.emergency_stop(self.motor)
            self._restore_motion_speed(old_mode, old_low)

    def test_stop(self) -> None:
        self._ensure_remote_and_stopped()
        old_mode, old_low = self._temporary_low_motion_speed()
        try:
            self.ctrl.scan(self.motor, "cw")
            time.sleep(self.scan_time_sec)
            self.ctrl.stop(self.motor)
            status = self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
            self._show("stop", repr(status))
        finally:
            self.ctrl.emergency_stop(self.motor)
            self._restore_motion_speed(old_mode, old_low)

    def test_stop_all(self) -> None:
        self._ensure_remote_and_stopped()
        old_mode, old_low = self._temporary_low_motion_speed()
        try:
            self.ctrl.scan(self.motor, "cw")
            time.sleep(self.scan_time_sec)
            self.ctrl.stop_all()
            status = self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
            self._show("stop_all", repr(status))
        finally:
            self.ctrl.emergency_stop_all()
            self._restore_motion_speed(old_mode, old_low)

    def test_emergency_stop(self) -> None:
        self._ensure_remote_and_stopped()
        old_mode, old_low = self._temporary_low_motion_speed()
        try:
            self.ctrl.scan(self.motor, "cw")
            time.sleep(self.scan_time_sec)
            self.ctrl.emergency_stop(self.motor)
            status = self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
            self._show("emergency_stop", repr(status))
        finally:
            self.ctrl.emergency_stop(self.motor)
            self._restore_motion_speed(old_mode, old_low)

    def test_emergency_stop_all(self) -> None:
        self._ensure_remote_and_stopped()
        old_mode, old_low = self._temporary_low_motion_speed()
        try:
            self.ctrl.scan(self.motor, "cw")
            time.sleep(self.scan_time_sec)
            self.ctrl.emergency_stop_all()
            status = self.ctrl.wait_stop(self.motor, timeout_sec=self.motion_timeout_sec)
            self._show("emergency_stop_all", repr(status))
        finally:
            self.ctrl.emergency_stop_all()
            self._restore_motion_speed(old_mode, old_low)

    def test_high_speed(self) -> None:
        self._show("high_speed", self.ctrl.high_speed(self.motor))

    def test_set_high_speed(self) -> None:
        original = self.ctrl.high_speed(self.motor)
        test_value = 100 if original != 100 else 110
        try:
            self.ctrl.set_high_speed(self.motor, test_value)
            actual = self.ctrl.high_speed(self.motor)
            if actual != test_value:
                raise AssertionError(f"HSPD設定不一致: expected={test_value}, actual={actual}")
            self._show("set_high_speed", actual)
        finally:
            self.ctrl.set_high_speed(self.motor, original)

    def test_middle_speed(self) -> None:
        self._show("middle_speed", self.ctrl.middle_speed(self.motor))

    def test_set_middle_speed(self) -> None:
        original = self.ctrl.middle_speed(self.motor)
        test_value = 80 if original != 80 else 90
        try:
            self.ctrl.set_middle_speed(self.motor, test_value)
            actual = self.ctrl.middle_speed(self.motor)
            if actual != test_value:
                raise AssertionError(f"MSPD設定不一致: expected={test_value}, actual={actual}")
            self._show("set_middle_speed", actual)
        finally:
            self.ctrl.set_middle_speed(self.motor, original)

    def test_low_speed(self) -> None:
        self._show("low_speed", self.ctrl.low_speed(self.motor))

    def test_set_low_speed(self) -> None:
        original = self.ctrl.low_speed(self.motor)
        test_value = 50 if original != 50 else 60
        try:
            self.ctrl.set_low_speed(self.motor, test_value)
            actual = self.ctrl.low_speed(self.motor)
            if actual != test_value:
                raise AssertionError(f"LSPD設定不一致: expected={test_value}, actual={actual}")
            self._show("set_low_speed", actual)
        finally:
            self.ctrl.set_low_speed(self.motor, original)

    def test_set_speed_profile(self) -> None:
        original = (
            self.ctrl.low_speed(self.motor),
            self.ctrl.middle_speed(self.motor),
            self.ctrl.high_speed(self.motor),
        )
        expected = (50, 100, 200)
        try:
            self.ctrl.set_speed_profile(self.motor, *expected)
            actual = (
                self.ctrl.low_speed(self.motor),
                self.ctrl.middle_speed(self.motor),
                self.ctrl.high_speed(self.motor),
            )
            if actual != expected:
                raise AssertionError(f"speed profile不一致: expected={expected}, actual={actual}")
            self._show("set_speed_profile", actual)
        finally:
            self.ctrl.set_speed_profile(self.motor, *original)

    def test_set_speed(self) -> None:
        original = (
            self.ctrl.low_speed(self.motor),
            self.ctrl.middle_speed(self.motor),
            self.ctrl.high_speed(self.motor),
        )
        speed = 300
        expected = (30, 100, 300)
        try:
            self.ctrl.set_speed(self.motor, speed)
            actual = (
                self.ctrl.low_speed(self.motor),
                self.ctrl.middle_speed(self.motor),
                self.ctrl.high_speed(self.motor),
            )
            if actual != expected:
                raise AssertionError(f"set_speed不一致: expected={expected}, actual={actual}")
            self._show("set_speed", actual)
        finally:
            self.ctrl.set_speed_profile(self.motor, *original)

    def test_speed_mode(self) -> None:
        self._show("speed_mode", self.ctrl.speed_mode(self.motor))

    def test_set_speed_mode(self) -> None:
        original = self.ctrl.speed_mode(self.motor)
        target = "LSPD" if original != "LSPD" else "MSPD"
        try:
            self.ctrl.set_speed_mode(self.motor, target)
            actual = self.ctrl.speed_mode(self.motor)
            if actual != target:
                raise AssertionError(f"SPD設定不一致: expected={target}, actual={actual}")
            self._show("set_speed_mode", actual)
        finally:
            self.ctrl.set_speed_mode(self.motor, original)

    def test_rate_number(self) -> None:
        self._show("rate_number", self.ctrl.rate_number(self.motor))

    def test_set_rate_number(self) -> None:
        original = self.ctrl.rate_number(self.motor)
        target = 5 if original != 5 else 6
        try:
            self.ctrl.set_rate_number(self.motor, target)
            actual = self.ctrl.rate_number(self.motor)
            if actual != target:
                raise AssertionError(f"RTE設定不一致: expected={target}, actual={actual}")
            self._show("set_rate_number", actual)
        finally:
            self.ctrl.set_rate_number(self.motor, original)

    def test_backlash(self) -> None:
        self._show("backlash", self.ctrl.backlash(self.motor))

    def test_set_backlash(self) -> None:
        original = self.ctrl.backlash(self.motor)
        target = original + 1 if original < 9999 else original - 1
        try:
            self.ctrl.set_backlash(self.motor, target)
            actual = self.ctrl.backlash(self.motor)
            if actual != target:
                raise AssertionError(f"BACKLASH設定不一致: expected={target}, actual={actual}")
            self._show("set_backlash", actual)
        finally:
            self.ctrl.set_backlash(self.motor, original)

    def test_limit(self) -> None:
        cw = self.ctrl.limit(self.motor, "cw")
        ccw = self.ctrl.limit(self.motor, "ccw")
        self._show("limit", f"CW={cw}, CCW={ccw}")

    def test_set_limit(self) -> None:
        for side in ("cw", "ccw"):
            original = self.ctrl.limit(self.motor, side)
            self.ctrl.set_limit(self.motor, side, original)
            actual = self.ctrl.limit(self.motor, side)
            if actual != original:
                raise AssertionError(
                    f"digital limit設定不一致: side={side}, expected={original}, actual={actual}"
                )
        self._show("set_limit", "CW/CCW read-back OK")

    def test_pause(self) -> None:
        self.ctrl.pause()
        actual = self.ctrl.pause_status()
        if actual != "ON":
            raise AssertionError(f"PAUSE ON後の応答がONではありません: {actual!r}")
        self._show("pause", actual)
        self.ctrl.resume()

    def test_resume(self) -> None:
        self.ctrl.pause()
        self.ctrl.resume()
        actual = self.ctrl.pause_status()
        if actual != "OFF":
            raise AssertionError(f"PAUSE OFF後の応答がOFFではありません: {actual!r}")
        self._show("resume", actual)

    def test_pause_status(self) -> None:
        self._show("pause_status", self.ctrl.pause_status())

    def test_hold(self) -> None:
        self._show("hold", self.ctrl.hold(self.motor))

    def test_set_hold(self) -> None:
        original = self.ctrl.hold(self.motor)
        self.ctrl.set_hold(self.motor, original == "ON")
        actual = self.ctrl.hold(self.motor)
        if actual != original:
            raise AssertionError(f"HOLD設定不一致: expected={original}, actual={actual}")
        self._show("set_hold", actual)

    def test_number_to_rate(self) -> None:
        number = self.ctrl.rate_number(self.motor)
        rate = self.ctrl.number_to_rate(number)
        self._show("number_to_rate", f"{number:03d} -> {rate} ms/1000PPS")

    def test_rate_to_number(self) -> None:
        number = self.ctrl.rate_number(self.motor)
        rate = self.ctrl.number_to_rate(number)
        actual = self.ctrl.rate_to_number(rate)
        if actual != number:
            raise AssertionError(f"RATE TABLE逆変換不一致: expected={number}, actual={actual}")
        self._show("rate_to_number", f"{rate} -> {actual:03d}")

    def test_find_home(self) -> None:
        if not self.enable_home_tests:
            print("[SKIP] find_home: enable_home_tests=False")
            return
        self._ensure_remote_and_stopped()
        self.ctrl.find_home(self.motor)
        status = self.ctrl.wait_stop(self.motor, timeout_sec=max(self.motion_timeout_sec, 120.0))
        self._show("find_home", repr(status))

    def test_home(self) -> None:
        if not self.enable_home_tests:
            print("[SKIP] home: enable_home_tests=False")
            return
        self._ensure_remote_and_stopped()
        self.ctrl.home(self.motor)
        status = self.ctrl.wait_stop(self.motor, timeout_sec=max(self.motion_timeout_sec, 120.0))
        self._show("home", repr(status))

    def test_close(self) -> None:
        self.ctrl.close()
        if self.ctrl.is_connected:
            raise AssertionError("close後もTCP接続状態です")
        self._show("close", self.ctrl.is_connected)

    def run_all(self) -> None:
        tests: list[Callable[[], None]] = [
            self.test_is_connected,
            self.test_version,
            self.test_hardware_version,
            self.test_status,
            self.test_status_all,
            self.test_is_busy,
            self.test_wait_stop,
            self.test_local,
            self.test_remote,
            self.test_position,
            self.test_set_position,
            self.test_zero_position,
            self.test_high_speed,
            self.test_set_high_speed,
            self.test_middle_speed,
            self.test_set_middle_speed,
            self.test_low_speed,
            self.test_set_low_speed,
            self.test_set_speed_profile,
            self.test_set_speed,
            self.test_speed_mode,
            self.test_set_speed_mode,
            self.test_rate_number,
            self.test_set_rate_number,
            self.test_backlash,
            self.test_set_backlash,
            self.test_limit,
            self.test_set_limit,
            self.test_pause_status,
            self.test_pause,
            self.test_resume,
            self.test_hold,
            self.test_set_hold,
            self.test_number_to_rate,
            self.test_rate_to_number,
            self.test_jog,
            self.test_move_relative,
            self.test_move,
            self.test_scan,
            self.test_constant_speed_scan,
            self.test_stop,
            self.test_stop_all,
            self.test_emergency_stop,
            self.test_emergency_stop_all,
            self.test_find_home,
            self.test_home,
        ]

        try:
            for test in tests:
                print(f"\n--- {test.__name__} ---")
                test()
        finally:
            if self.ctrl.is_connected:
                self.ctrl.emergency_stop_all()
                self.ctrl.resume()
                self.ctrl.remote()
                self.test_close()


if __name__ == "__main__":
    # PM2C-06A の工場出荷時 LAN アドレス。実機設定に合わせて変更してください。
    IP_ADDRESS = "192.168.1.55"

    tester = PM2CDHardwareTest(
        ip_address=IP_ADDRESS,
        motor=0,
        test_pulse=10,
        scan_time_sec=0.2,
        enable_home_tests=False,
    )
    tester.run_all()
