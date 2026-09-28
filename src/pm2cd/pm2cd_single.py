import logging
import time
from typing import List, Optional, Union

from pm2cd.core.communication_tcp import Communication
from pm2cd.core.controller_status import ControllerStatus
from pm2cd.core.home_status import HomeStatus
from pm2cd.core.motor_setting import MotorSetting
from pm2cd.core.motor_status import MotorStatus
from pm2cd.core.stop_mode import StopMode
from pm2cd.core.version_info import VersionInfo
from pm2cd.pm2cd_device import PM2CDDevice

# PM2CD の公開制御API。
# 通信層と装置コマンド層を委譲で束ね、上位コードへ装置操作を提供する。


class PM2CDsingle:
    """PM2CD を単一プロセスから制御するための公開 I/F。"""

    # --- 初期化・接続管理 ------------------------------------------------------
    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        channel_count: int = 2,
        logger=None,
        log_level: str = "INFO",
        communication: Optional[Communication] = None,
    ):
        """インスタンスを初期化する。

        Args:
            ip_address: PM2CD の IP アドレス。
            port: PM2CD の TCP ポート番号。
            timeout_sec: TCP 通信および待機処理のタイムアウト秒数。
            channel_count: 制御対象チャンネル数。PM2CD では 2 固定。
            logger: 使用する logger。None の場合はこのモジュールで生成する。
            log_level: logger を生成する場合のログレベル。
            communication: 使用する Communication インスタンス。
                None の場合は内部で生成する。

        Raises:
            ValueError: PM2CD 固有の固定条件に反する設定が指定された場合。
        """
        if not logger:
            logging.basicConfig(level=(log_level or "INFO").upper())
            logger = logging.getLogger(__name__)

        self._logger = logger

        if channel_count != 2:
            raise ValueError(f"PM2CDのchannel_countは2です: {channel_count}")

        if communication is None:
            communication = Communication(
                ip_address=ip_address,
                port=port,
                timeout_sec=timeout_sec,
                logger=self._logger,
                log_level=log_level,
            )

        self._communication = communication

        self._device = PM2CDDevice(
            communication=self._communication,
            channel_count=channel_count,
            logger=self._logger,
            log_level=log_level,
        )

        self._motor = 0
        # move()/move_relative() が発行した直近の移動条件を軸ごとに保持する。
        # wait_for_complete() はバックラッシュ補正の途中停止と最終停止を区別するために使う。
        self._move_context = {}

        self._communication.connect()

    @property
    def motor(self) -> int:
        """引数省略時に使用するモーター番号を取得する。"""
        return self._motor

    @motor.setter
    def motor(self, value: int) -> None:
        """引数省略時に使用するモーター番号を設定する。

        Args:
            value: モーター番号。0 または 1。

        Raises:
            TypeError: value が int でない場合。
            ValueError: value が 0 または 1 でない場合。
        """
        if isinstance(value, bool):
            raise TypeError("motor は int で指定してください")

        if not isinstance(value, int):
            raise TypeError("motor は int で指定してください")

        if value not in (0, 1):
            raise ValueError("motor は0または1で指定してください")

        self._motor = value

    def _resolve_motor(self, motor: Optional[int]) -> int:
        """明示指定されたモーター番号または既定値を返す。

        Args:
            motor: メソッドで明示指定されたモーター番号。

        Returns:
            motor が指定されていればその値、None なら motor プロパティ。
        """
        if motor is not None:
            return motor

        return self.motor

    def _backlash_enabled(
        self,
        backlash: Union[str, bool, None],
    ) -> bool:
        """バックラッシュ補正を使用する指定か判定する。

        Args:
            backlash: move()/move_relative() のバックラッシュ指定。

        Returns:
            B/S 補正を使用する指定の場合は True。
        """
        if backlash is True:
            return True

        if backlash is False:
            return False

        if backlash is None:
            return False

        if not isinstance(backlash, str):
            return False

        normalized = backlash.strip().upper()
        return normalized in ("B", "S")

    def _motion_active(
        self,
        status: MotorStatus,
    ) -> bool:
        """STS? の情報から軸が動作状態か判定する。

        BUSY だけでは短い動作の状態遷移を取り逃すため、DRIVE と方向情報も
        合わせて active/inactive を判定する。

        Args:
            status: 対象軸の MotorStatus。

        Returns:
            動作状態の場合は True。
        """
        if status.is_busy:
            return True

        if status.is_driving:
            return True

        return status.direction != "S"

    def _set_move_context(
        self,
        motor: int,
        target_position: Optional[int],
        backlash: Union[str, bool, None],
    ) -> None:
        """wait_for_complete() に必要な最小限の移動条件を保存する。

        バックラッシュ補正点は装置内部の動作であり、Python 側では予測しない。
        保存するのは最終目標位置と、B/S 補正を要求したかどうかだけとする。
        """
        self._move_context[motor] = {
            "target_position": target_position,
            "backlash_enabled": self._backlash_enabled(backlash),
        }

    def _clear_move_context(
        self,
        motor: int,
    ) -> None:
        """指定軸の位置決め移動条件を破棄する。"""
        if motor in self._move_context:
            del self._move_context[motor]

    def is_connected(
        self,
    ) -> bool:
        """TCP 接続状態を取得する。

        Returns:
            接続中の場合は True、それ以外は False。
        """
        return self._communication.is_connected()

    def connect(
        self,
    ) -> bool:
        """PM2CD へ TCP 接続する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._communication.connect()

    def disconnect(
        self,
    ) -> bool:
        """PM2CD との TCP 接続を切断する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._communication.disconnect()

    def close(
        self,
    ) -> bool:
        """通信を終了する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._communication.close()

    # --- コントローラ基本状態 --------------------------------------------------
    def remote(
        self,
    ) -> bool:
        """装置をリモート操作モードへ切り替える。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.remote()

    def local(
        self,
    ) -> bool:
        """装置をローカル操作モードへ切り替える。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.local()

    # @property
    def version(self):
        return self.get_version()

    def get_version(
        self,
    ) -> Optional[VersionInfo]:
        """装置のソフトウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.version()

    def get_hardware_version(
        self,
    ) -> Optional[str]:
        """装置のハードウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.hardware_version()

    def get_controller_status(
        self,
    ) -> Optional[ControllerStatus]:
        """コントローラー全体の状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.controller_status()

    def controller_status(
        self,
    ) -> Optional[ControllerStatus]:
        """コントローラー全体の状態を取得する互換メソッド。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self.get_controller_status()

    # --- モータ動作 ------------------------------------------------------------
    def move(
        self,
        target: int,
        motor: Optional[int] = None,
        backlash: Union[str, bool, None] = True,
        relative: bool = False,
    ) -> bool:
        """指定モーターを絶対位置または相対量で移動する。

        motor を省略した場合は motor プロパティを使用する。
        relative=False の場合は target を絶対目標位置として扱い、
        relative=True の場合は target を現在位置からの相対移動量として扱う。
        wait_for_complete() がバックラッシュ補正を含む位置決め完了を判定できるよう、
        コマンド送信成功時に最終的な絶対目標位置とバックラッシュ条件を保存する。

        Args:
            target: 絶対目標位置。relative=True の場合は相対移動量。
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            backlash: バックラッシュ補正指定。
            relative: True の場合は相対移動、False の場合は絶対移動。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor = self._resolve_motor(motor)

        target_position = target
        if relative:
            current_position = self.get_position(motor)
            target_position = None
            if current_position is not None:
                target_position = current_position + target

        if relative:
            result = self._device.move_relative(motor, target, backlash)
        else:
            result = self._device.move(motor, target, backlash)

        if result:
            self._set_move_context(
                motor=motor,
                target_position=target_position,
                backlash=backlash,
            )

        return result

    def move_relative(
        self,
        target: int,
        motor: Optional[int] = None,
        backlash: Union[str, bool, None] = True,
    ) -> bool:
        """指定モーターを現在位置から相対移動する。

        move(..., relative=True) と同じ動作をする互換メソッド。

        Args:
            target: 相対移動量。
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self.move(
            target=target,
            motor=motor,
            backlash=backlash,
            relative=True,
        )

    def scan(
        self,
        motor: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> bool:
        """指定方向へ連続スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if direction is None:
            if motor is None:
                raise TypeError("scan() の引数が不足しています")
            direction = motor
            motor = None

        if direction is None:
            raise TypeError("scan() の direction を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.scan(motor, direction)

    def constant_speed_scan(
        self,
        motor: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> bool:
        """指定方向へ定速スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if direction is None:
            if motor is None:
                raise TypeError("constant_speed_scan() の引数が不足しています")
            direction = motor
            motor = None

        if direction is None:
            raise TypeError("constant_speed_scan() の direction を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.constant_speed_scan(motor, direction)

    def jog(
        self,
        motor: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> bool:
        """指定方向へ JOG 動作する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if direction is None:
            if motor is None:
                raise TypeError("jog() の引数が不足しています")
            direction = motor
            motor = None

        if direction is None:
            raise TypeError("jog() の direction を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.jog(motor, direction)

    def scan_home(
        self,
        motor: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> bool:
        """指定方向へ原点探索スキャンを開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if direction is None:
            if motor is None:
                raise TypeError("scan_home() の引数が不足しています")
            direction = motor
            motor = None

        if direction is None:
            raise TypeError("scan_home() の direction を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.scan_home(motor, direction)

    def home(
        self,
        motor: Optional[int] = None,
    ) -> bool:
        """記録済み原点位置へ移動する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor = self._resolve_motor(motor)
        return self._device.home(motor)

    def find_home(
        self,
        motor: Optional[int] = None,
    ) -> bool:
        """原点検出動作を開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor = self._resolve_motor(motor)
        return self._device.find_home(motor)

    # --- 停止・状態監視 --------------------------------------------------------
    def stop(
        self,
        motor: Optional[int] = None,
    ) -> bool:
        """指定モーターを停止する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor = self._resolve_motor(motor)
        result = self._device.stop(motor)
        if result:
            self._clear_move_context(motor)

        return result

    def stop_all(
        self,
    ) -> bool:
        """全モーターを停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        result = self._device.stop_all()
        if result:
            self._move_context.clear()

        return result

    def emergency_stop(
        self,
        motor: Optional[int] = None,
    ) -> bool:
        """指定モーターを非常停止する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor = self._resolve_motor(motor)
        result = self._device.emergency_stop(motor)
        if result:
            self._clear_move_context(motor)

        return result

    def emergency_stop_all(
        self,
    ) -> bool:
        """全モーターを非常停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        result = self._device.emergency_stop_all()
        if result:
            self._move_context.clear()

        return result

    def get_status(
        self,
        motor: Optional[int] = None,
    ) -> Optional[MotorStatus]:
        """指定モーターの状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.status(motor)

    def get_status_all(
        self,
    ) -> Optional[List[MotorStatus]]:
        """全モーターの状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.status_all()

    def status_all(
        self,
    ) -> Optional[List[MotorStatus]]:
        """全モーターの状態を取得する互換メソッド。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self.get_status_all()

    def get_rotate(
        self,
        motor: Optional[int] = None,
    ) -> Optional[bool]:
        """指定モーターが回転中か確認する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.check_rotate(motor)

    def is_busy(
        self,
        motor: Optional[int] = None,
    ) -> Optional[bool]:
        """指定モーターの BUSY 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        status = self.get_status(motor)
        if status is None:
            return None

        return status.is_busy

    def wait_for_complete(
        self,
        motor: Optional[int] = None,
        timeout_sec: float = 30.0,
        interval_sec: float = 0.1,
        target_position: Optional[int] = None,
        show_position: bool = False,
    ) -> Optional[MotorStatus]:
        """指定モーターの最終停止を待つ。

        位置決め移動では move() が保存した最終目標位置を使用する。
        backlash=False の場合は、目標位置で inactive になれば完了とする。

        B/S バックラッシュ補正では、最初の ``目標位置 + inactive`` が
        補正途中か最終停止かを一回の観測だけでは区別できない。このため、
        最初の到達は保留し、次の観測で active または目標位置外を観測した
        場合は補正軌跡が継続中と判断する。その後、再び目標位置で inactive
        になれば完了とする。補正軌跡が短くポーリング間で観測できない場合は、
        ``目標位置 + inactive`` を2回連続して確認した時点で完了とする。

        装置内部のバックラッシュ補正点は、補正値の符号、移動方向、B/S の
        条件で変化するため、Python 側では計算・予測しない。

        位置決めコンテキストがない場合は、stop() 後などの単純な停止待ち
        として inactive を2回連続して確認する。

        Args:
            motor: モーター番号。None の場合は motor プロパティを使用する。
            timeout_sec: 待機処理のタイムアウト秒数。
            interval_sec: 状態確認のポーリング間隔秒数。
            target_position: 完了判定に使う絶対目標位置。明示指定した場合は
                move() が保存した値より優先する。
            show_position: True の場合は各ポーリングの現在位置を表示する。

        Returns:
            完了条件を満たした最後の MotorStatus。状態取得失敗または
            タイムアウト時は None。
        """
        motor = self._resolve_motor(motor)
        deadline = time.monotonic() + timeout_sec

        context = self._move_context.get(motor)
        backlash_enabled = False

        if context is not None:
            if target_position is None:
                target_position = context.get("target_position")
            backlash_enabled = bool(context.get("backlash_enabled"))

        plain_inactive_count = 0
        target_inactive_seen = False

        while True:
            status = self.get_status(motor)
            if status is None:
                return None

            if show_position:
                print(status.position, flush=True)

            active = self._motion_active(status)

            if target_position is None:
                if active:
                    plain_inactive_count = 0
                else:
                    plain_inactive_count += 1
                    if plain_inactive_count >= 2:
                        return status

            elif not backlash_enabled:
                if not active and status.position == target_position:
                    self._clear_move_context(motor)
                    return status

            else:
                at_target = status.position == target_position

                if target_inactive_seen:
                    if not active and at_target:
                        # 補正軌跡を観測できた場合は戻り先の目標位置。
                        # 観測できなかった場合は目標位置での2回目の停止確認。
                        self._clear_move_context(motor)
                        return status

                    # active または目標位置外なら補正軌跡が続いている。
                    # 補正点そのものは予測せず、目標位置へ戻るまで観測する。
                elif not active and at_target:
                    target_inactive_seen = True

            if time.monotonic() >= deadline:
                if target_position is None:
                    self._logger.error(
                        f"wait_for_complete(): motor {motor} が停止しませんでした"
                    )
                else:
                    self._logger.error(
                        "wait_for_complete(): motor {} が目標位置 {} で完了しませんでした".format(
                            motor,
                            target_position,
                        )
                    )
                return None

            time.sleep(interval_sec)

    # --- 位置・速度設定 --------------------------------------------------------
    def get_position(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """指定モーターの現在位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.position(motor)

    def set_position(
        self,
        motor: Optional[int] = None,
        pulse: Optional[int] = None,
    ) -> bool:
        """指定モーターの現在位置カウンタを設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if pulse is None:
            if motor is None:
                raise TypeError("set_position() の引数が不足しています")
            pulse = motor
            motor = None

        if pulse is None:
            raise TypeError("set_position() の pulse を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_position(motor, pulse)

    def zero_position(
        self,
        motor: Optional[int] = None,
    ) -> bool:
        """指定モーターの現在位置カウンタを 0 にする。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        motor = self._resolve_motor(motor)
        return self.set_position(motor, 0)

    def get_speed(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """set_speed() の基準となる高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.speed(motor)

    def set_speed(
        self,
        motor: Optional[int] = None,
        speed: Optional[int] = None,
    ) -> bool:
        """高速値を基準に低速・中速・高速を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if speed is None:
            if motor is None:
                raise TypeError("set_speed() の引数が不足しています")
            speed = motor
            motor = None

        if speed is None:
            raise TypeError("set_speed() の speed を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_speed(motor, speed)

    def get_speed_profile(
        self,
        motor: Optional[int] = None,
    ) -> Optional[List[int]]:
        """低速・中速・高速の設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            低速・中速・高速の順の設定値。取得に失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.speed_profile(motor)

    def set_speed_profile(
        self,
        motor: Optional[int] = None,
        low_speed: Optional[int] = None,
        middle_speed: Optional[int] = None,
        high_speed: Optional[int] = None,
    ) -> bool:
        """低速・中速・高速を個別に設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            low_speed: 低速値。
            middle_speed: 中速値。
            high_speed: 高速値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if high_speed is None:
            if motor is None or low_speed is None or middle_speed is None:
                raise TypeError("set_speed_profile() の引数が不足しています")
            high_speed = middle_speed
            middle_speed = low_speed
            low_speed = motor
            motor = None

        if low_speed is None:
            raise TypeError("set_speed_profile() の low_speed を指定してください")

        if middle_speed is None:
            raise TypeError("set_speed_profile() の middle_speed を指定してください")

        if high_speed is None:
            raise TypeError("set_speed_profile() の high_speed を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_speed_profile(
            motor, low_speed, middle_speed, high_speed
        )

    def get_high_speed(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.high_speed(motor)

    def set_high_speed(
        self,
        motor: Optional[int] = None,
        speed: Optional[int] = None,
    ) -> bool:
        """高速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if speed is None:
            if motor is None:
                raise TypeError("set_high_speed() の引数が不足しています")
            speed = motor
            motor = None

        if speed is None:
            raise TypeError("set_high_speed() の speed を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_high_speed(motor, speed)

    def get_middle_speed(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """中速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.middle_speed(motor)

    def set_middle_speed(
        self,
        motor: Optional[int] = None,
        speed: Optional[int] = None,
    ) -> bool:
        """中速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if speed is None:
            if motor is None:
                raise TypeError("set_middle_speed() の引数が不足しています")
            speed = motor
            motor = None

        if speed is None:
            raise TypeError("set_middle_speed() の speed を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_middle_speed(motor, speed)

    def get_low_speed(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """低速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.low_speed(motor)

    def set_low_speed(
        self,
        motor: Optional[int] = None,
        speed: Optional[int] = None,
    ) -> bool:
        """低速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if speed is None:
            if motor is None:
                raise TypeError("set_low_speed() の引数が不足しています")
            speed = motor
            motor = None

        if speed is None:
            raise TypeError("set_low_speed() の speed を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_low_speed(motor, speed)

    def get_speed_mode(
        self,
        motor: Optional[int] = None,
    ) -> Optional[str]:
        """現在の速度モードを取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.speed_mode(motor)

    def set_speed_mode(
        self,
        motor: Optional[int] = None,
        mode: Optional[Union[int, str]] = None,
    ) -> bool:
        """速度モードを設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            mode: 速度モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if mode is None:
            if motor is None:
                raise TypeError("set_speed_mode() の引数が不足しています")
            mode = motor
            motor = None

        if mode is None:
            raise TypeError("set_speed_mode() の mode を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_speed_mode(motor, mode)

    # --- 加減速・バックラッシュ・リミット ------------------------------------
    def get_rate_number(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """加減速レート番号を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.rate_number(motor)

    def set_rate_number(
        self,
        motor: Optional[int] = None,
        number: Optional[int] = None,
    ) -> bool:
        """加減速レート番号を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            number: レート番号。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if number is None:
            if motor is None:
                raise TypeError("set_rate_number() の引数が不足しています")
            number = motor
            motor = None

        if number is None:
            raise TypeError("set_rate_number() の number を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_rate_number(motor, number)

    def get_rate(
        self,
        motor: Optional[int] = None,
    ) -> Optional[float]:
        """加減速レートを取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            加減速レート。取得に失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        number = self.get_rate_number(motor)
        if number is None:
            return None

        return self.number_to_rate(number)

    def set_rate(
        self,
        motor: Optional[int] = None,
        rate: Optional[float] = None,
    ) -> bool:
        """加減速レートを設定する。

        指定値に最も近いレート番号を選択して設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            rate: 加減速レート。

        Returns:
            処理に成功した場合は True、失敗した場合は False。

        Raises:
            TypeError: rate の型が不正な場合。
        """
        if rate is None:
            if motor is None:
                raise TypeError("set_rate() の引数が不足しています")
            rate = motor
            motor = None

        if rate is None:
            raise TypeError("set_rate() の rate を指定してください")

        motor = self._resolve_motor(motor)
        number = self._nearest_rate_number(rate)
        return self.set_rate_number(motor, number)

    def get_backlash(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """バックラッシュ補正量を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.backlash(motor)

    def set_backlash(
        self,
        motor: Optional[int] = None,
        backlash: Optional[int] = None,
    ) -> bool:
        """バックラッシュ補正量を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if backlash is None:
            if motor is None:
                raise TypeError("set_backlash() の引数が不足しています")
            backlash = motor
            motor = None

        if backlash is None:
            raise TypeError("set_backlash() の backlash を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_backlash(motor, backlash)

    def get_limit(
        self,
        motor: Optional[int] = None,
        side: Optional[str] = None,
    ) -> Optional[int]:
        """指定側のソフトウェアリミット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            side: リミット側。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        if side is None:
            if motor is None:
                raise TypeError("get_limit() の引数が不足しています")
            side = motor
            motor = None

        if side is None:
            raise TypeError("get_limit() の side を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.limit(motor, side)

    def set_limit(
        self,
        motor: Optional[int] = None,
        side: Optional[str] = None,
        pulse: Optional[int] = None,
    ) -> bool:
        """指定側のソフトウェアリミット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            side: リミット側。cw または ccw。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if pulse is None:
            if motor is None or side is None:
                raise TypeError("set_limit() の引数が不足しています")
            pulse = side
            side = motor
            motor = None

        if side is None:
            raise TypeError("set_limit() の side を指定してください")

        if pulse is None:
            raise TypeError("set_limit() の pulse を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_limit(motor, side, pulse)

    def get_limit_status(
        self,
        motor: Optional[int] = None,
    ) -> Optional[List[bool]]:
        """ソフトウェアリミット状態を ``[CW, CCW]`` で取得する。"""
        motor = self._resolve_motor(motor)
        status = self._device.limit_status(motor)
        if status is None:
            return None

        return status.soft

    def get_limit_status_all(
        self,
    ) -> Optional[List[List[bool]]]:
        """全モーターのソフトウェアリミット状態を ``[[CW, CCW], ...]`` で取得する。"""
        statuses = self._device.limit_status_all()
        if statuses is None:
            return None

        return [status.soft for status in statuses]

    def get_hard_limit_status(
        self,
        motor: Optional[int] = None,
    ) -> Optional[List[bool]]:
        """ハードウェアリミット状態を ``[CW, CCW, HP]`` で取得する。"""
        motor = self._resolve_motor(motor)
        status = self._device.limit_status(motor)
        if status is None:
            return None

        return status.hard

    def get_hard_limit_status_all(
        self,
    ) -> Optional[List[List[bool]]]:
        """全モーターのハードウェアリミット状態を ``[[CW, CCW, HP], ...]`` で取得する。"""
        statuses = self._device.limit_status_all()
        if statuses is None:
            return None

        return [status.hard for status in statuses]

    def get_limit_enabled(
        self,
        motor: Optional[int] = None,
    ) -> Optional[bool]:
        """ソフトウェアリミットの有効/無効を取得する。"""
        motor = self._resolve_motor(motor)
        setting = self._device.limit_switch_setting(motor)
        if setting is None:
            return None

        return setting.digital_limit_enabled

    def set_limit_enabled(
        self,
        motor: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """ソフトウェアリミットを有効/無効にする。"""
        if enabled is None:
            if motor is None:
                raise TypeError("set_limit_enabled() の引数が不足しています")
            enabled = motor
            motor = None

        if enabled is None:
            raise TypeError("set_limit_enabled() の enabled を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_digital_limit_enabled(motor, enabled)

    def get_hard_limit_enabled(
        self,
        motor: Optional[int] = None,
    ) -> Optional[List[bool]]:
        """CW/CCW ハードウェアLSの enable 設定を ``[CW, CCW]`` で取得する。

        HP LS は PM2C/PM4C-06A では常時 enable のため返さない。
        """
        motor = self._resolve_motor(motor)
        setting = self._device.limit_switch_setting(motor)
        if setting is None:
            return None

        return [setting.cw_enabled, setting.ccw_enabled]

    def set_hard_limit_enabled(
        self,
        motor: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """CW/CCW ハードウェアリミットを有効/無効にする。"""
        if enabled is None:
            if motor is None:
                raise TypeError("set_hard_limit_enabled() の引数が不足しています")
            enabled = motor
            motor = None

        if enabled is None:
            raise TypeError("set_hard_limit_enabled() の enabled を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_hard_limit_enabled(motor, enabled)

    def get_hard_limit_normally_closed(
        self,
        motor: Optional[int] = None,
    ) -> Optional[List[bool]]:
        """ハードウェアLS接点設定を ``[CW, CCW, HP]`` で取得する。

        True は normally closed、False は normally open を表す。
        """
        motor = self._resolve_motor(motor)
        setting = self._device.limit_switch_setting(motor)
        if setting is None:
            return None

        return [setting.cw_nc, setting.ccw_nc, setting.hp_nc]

    def set_hard_limit_normally_closed(
        self,
        motor: Optional[int] = None,
        side: Optional[str] = None,
        normally_closed: Optional[bool] = None,
    ) -> bool:
        """ハードウェアLSの接点仕様を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            side: ``hp``、``cw``、``ccw``。
            normally_closed: normally closed にする場合は True、
                normally open にする場合は False。
        """
        if normally_closed is None:
            if motor is None or side is None:
                raise TypeError(
                    "set_hard_limit_normally_closed() の引数が不足しています"
                )
            normally_closed = side
            side = motor
            motor = None

        if side is None:
            raise TypeError(
                "set_hard_limit_normally_closed() の side を指定してください"
            )

        if normally_closed is None:
            raise TypeError(
                "set_hard_limit_normally_closed() の normally_closed を指定してください"
            )

        motor = self._resolve_motor(motor)
        return self._device.set_hard_limit_normally_closed(
            motor,
            side,
            normally_closed,
        )

    # --- 一時停止・励磁保持 ----------------------------------------------------
    def pause(
        self,
    ) -> bool:
        """動作を一時停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.pause()

    def resume(
        self,
    ) -> bool:
        """一時停止を解除する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.resume()

    def get_pause_status(
        self,
    ) -> Optional[str]:
        """一時停止状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.pause_status()

    def get_hold(
        self,
        motor: Optional[int] = None,
    ) -> Optional[str]:
        """指定モーターの HOLD 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.hold(motor)

    def set_hold(
        self,
        motor: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """指定モーターの HOLD 状態を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            enabled: 有効にする場合は True、無効にする場合は False。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if enabled is None:
            if motor is None:
                raise TypeError("set_hold() の引数が不足しています")
            enabled = motor
            motor = None

        if enabled is None:
            raise TypeError("set_hold() の enabled を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_hold(motor, enabled)

    def get_hold_on_time(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """HOLD ON 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.hold_on_time(motor)

    def set_hold_on_time(
        self,
        motor: Optional[int] = None,
        msec: Optional[int] = None,
    ) -> bool:
        """HOLD ON 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if msec is None:
            if motor is None:
                raise TypeError("set_hold_on_time() の引数が不足しています")
            msec = motor
            motor = None

        if msec is None:
            raise TypeError("set_hold_on_time() の msec を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_hold_on_time(motor, msec)

    def get_hold_off_time(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """HOLD OFF 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.hold_off_time(motor)

    def set_hold_off_time(
        self,
        motor: Optional[int] = None,
        msec: Optional[int] = None,
    ) -> bool:
        """HOLD OFF 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if msec is None:
            if motor is None:
                raise TypeError("set_hold_off_time() の引数が不足しています")
            msec = motor
            motor = None

        if msec is None:
            raise TypeError("set_hold_off_time() の msec を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_hold_off_time(motor, msec)

    # --- 原点関連設定 ----------------------------------------------------------
    def get_home_status(
        self,
        motor: Optional[int] = None,
    ) -> Optional[HomeStatus]:
        """原点検出設定状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.home_status(motor)

    def set_home_status(
        self,
        motor: Optional[int] = None,
        found: Optional[bool] = None,
        found_direction: Optional[str] = None,
        auto_start_direction: Optional[str] = None,
    ) -> bool:
        """原点検出設定状態を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            found: 原点検出済み状態。
            found_direction: 原点検出方向。
            auto_start_direction: 自動原点検出開始方向。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if auto_start_direction is None:
            if motor is None or found is None or found_direction is None:
                raise TypeError("set_home_status() の引数が不足しています")
            auto_start_direction = found_direction
            found_direction = found
            found = motor
            motor = None

        if found is None:
            raise TypeError("set_home_status() の found を指定してください")

        if found_direction is None:
            raise TypeError("set_home_status() の found_direction を指定してください")

        if auto_start_direction is None:
            raise TypeError(
                "set_home_status() の auto_start_direction を指定してください"
            )

        motor = self._resolve_motor(motor)
        return self._device.set_home_status(
            motor, found, found_direction, auto_start_direction
        )

    def get_home_position(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """記録済み原点位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.home_position(motor)

    def set_home_position(
        self,
        motor: Optional[int] = None,
        pulse: Optional[int] = None,
    ) -> bool:
        """原点位置を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if pulse is None:
            if motor is None:
                raise TypeError("set_home_position() の引数が不足しています")
            pulse = motor
            motor = None

        if pulse is None:
            raise TypeError("set_home_position() の pulse を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_home_position(motor, pulse)

    def get_home_offset(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """原点オフセットを取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.home_offset(motor)

    def set_home_offset(
        self,
        motor: Optional[int] = None,
        pulse: Optional[int] = None,
    ) -> bool:
        """原点オフセットを設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if pulse is None:
            if motor is None:
                raise TypeError("set_home_offset() の引数が不足しています")
            pulse = motor
            motor = None

        if pulse is None:
            raise TypeError("set_home_offset() の pulse を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_home_offset(motor, pulse)

    # --- プリセット・JOG・装置設定 --------------------------------------------
    def get_preset_position(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """プリセット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.preset_position(motor)

    def set_preset_position(
        self,
        motor: Optional[int] = None,
        pulse: Optional[int] = None,
    ) -> bool:
        """プリセット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if pulse is None:
            if motor is None:
                raise TypeError("set_preset_position() の引数が不足しています")
            pulse = motor
            motor = None

        if pulse is None:
            raise TypeError("set_preset_position() の pulse を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_preset_position(motor, pulse)

    def get_jog_pulse(
        self,
        motor: Optional[int] = None,
    ) -> Optional[int]:
        """JOG パルス数を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.jog_pulse(motor)

    def set_jog_pulse(
        self,
        motor: Optional[int] = None,
        pulse: Optional[int] = None,
    ) -> bool:
        """JOG パルス数を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if pulse is None:
            if motor is None:
                raise TypeError("set_jog_pulse() の引数が不足しています")
            pulse = motor
            motor = None

        if pulse is None:
            raise TypeError("set_jog_pulse() の pulse を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_jog_pulse(motor, pulse)

    def get_limit_switch_setting(
        self,
        motor: Optional[int] = None,
    ) -> Optional[List[bool]]:
        """リミット設定を意味値のリストで取得する。

        Returns:
            ``[digital_limit_enable, CW_enable, CCW_enable,
            CW_normally_closed, CCW_normally_closed, HP_normally_closed]``。
            HP LS は常時 enable のため enable 値には含めない。
            取得に失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        setting = self._device.limit_switch_setting(motor)
        if setting is None:
            return None

        return [
            setting.digital_limit_enabled,
            setting.cw_enabled,
            setting.ccw_enabled,
            setting.cw_nc,
            setting.ccw_nc,
            setting.hp_nc,
        ]

    def get_motor_setting(
        self,
        motor: Optional[int] = None,
    ) -> Optional[MotorSetting]:
        """モーター設定を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.motor_setting(motor)

    def set_motor_setting(
        self,
        motor: Optional[int] = None,
        drive_enabled: Optional[bool] = None,
        hold_mode: Optional[int] = None,
        output_mode: Optional[int] = None,
    ) -> bool:
        """モーター設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            drive_enabled: モータードライブを有効にする場合は True。
            hold_mode: ホールドモード。
            output_mode: 出力モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if output_mode is None:
            if motor is None or drive_enabled is None or hold_mode is None:
                raise TypeError("set_motor_setting() の引数が不足しています")
            output_mode = hold_mode
            hold_mode = drive_enabled
            drive_enabled = motor
            motor = None

        if drive_enabled is None:
            raise TypeError("set_motor_setting() の drive_enabled を指定してください")

        if hold_mode is None:
            raise TypeError("set_motor_setting() の hold_mode を指定してください")

        if output_mode is None:
            raise TypeError("set_motor_setting() の output_mode を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_motor_setting(
            motor, drive_enabled, hold_mode, output_mode
        )

    def get_stop_mode(
        self,
        motor: Optional[int] = None,
    ) -> Optional[StopMode]:
        """停止モード設定を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        motor = self._resolve_motor(motor)
        return self._device.stop_mode(motor)

    def set_stop_mode(
        self,
        motor: Optional[int] = None,
        panel_fast: Optional[bool] = None,
        limit_fast: Optional[bool] = None,
    ) -> bool:
        """停止モード設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            panel_fast: パネル停止を高速停止にする場合は True。
            limit_fast: リミット停止を高速停止にする場合は True。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        if limit_fast is None:
            if motor is None or panel_fast is None:
                raise TypeError("set_stop_mode() の引数が不足しています")
            limit_fast = panel_fast
            panel_fast = motor
            motor = None

        if panel_fast is None:
            raise TypeError("set_stop_mode() の panel_fast を指定してください")

        if limit_fast is None:
            raise TypeError("set_stop_mode() の limit_fast を指定してください")

        motor = self._resolve_motor(motor)
        return self._device.set_stop_mode(motor, panel_fast, limit_fast)

    # --- RATE変換 --------------------------------------------------------------
    def number_to_rate(
        self,
        index: int,
    ) -> Optional[float]:
        """レート番号を RATE_TABLE のレート値へ変換する。

        Args:
            index: RATE_TABLE のインデックス。

        Returns:
            取得または変換に成功した値。失敗した場合は None。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 変換可能な範囲外の場合。
        """
        return self._device.number_to_rate(index)

    def rate_to_number(
        self,
        rate: float,
    ) -> Optional[int]:
        """レート値を対応する RATE_TABLE の番号へ変換する。

        Args:
            rate: 変換するレート値。

        Returns:
            取得または変換に成功した値。失敗した場合は None。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 変換可能な範囲外の場合。
        """
        return self._device.rate_to_number(rate)

    def _nearest_rate_number(
        self,
        rate: float,
    ) -> int:
        """指定値に最も近いレート番号を取得する。"""
        if isinstance(rate, bool):
            raise TypeError("rateは数値で指定してください")

        if not isinstance(rate, (int, float)):
            raise TypeError("rateは数値で指定してください")

        target = abs(float(rate))

        nearest_number = self._device.RATE_MIN
        nearest_rate = self.number_to_rate(nearest_number)
        nearest_difference = abs(target - nearest_rate)

        number = self._device.RATE_MIN + 1
        while number <= self._device.RATE_MAX:
            table_rate = self.number_to_rate(number)
            difference = abs(target - table_rate)

            if difference < nearest_difference:
                nearest_number = number
                nearest_difference = difference

            number += 1

        return nearest_number

    # --- context manager -------------------------------------------------------
    def __enter__(
        self,
    ) -> "PM2CDsingle":
        """context manager 開始時に接続を確立する。

        Returns:
            'PM2CD' 型の結果。
        """
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """context manager 終了時に接続を切断する。

        Args:
            exc_type: with ブロック内で発生した例外の型。
            exc_value: with ブロック内で発生した例外。
            traceback: with ブロック内で発生した例外の traceback。

        Returns:
            None。
        """
        self.close()


def main() -> None:
    """PM2CD 公開 I/F の基本的な使用例を実行する。

    実機の IP アドレスに変更してから、パッケージのモジュールとして実行する。
    この例では装置を動かすコマンドは送信せず、接続と状態取得だけを確認する。

    Returns:
        None。
    """
    ip_address = "10.170.10.62"
    port = 7777

    ctrl = PM2CDsingle(ip_address=ip_address, port=port)

    try:
        if not ctrl.is_connected():
            print("PM2CD へ接続できませんでした")
            return

        version = ctrl.version()
        if version is None:
            print("VER? の取得に失敗しました")
        else:
            print(f"version: {version}")

        controller_status = ctrl.controller_status()
        if controller_status is None:
            print("STQ? の取得に失敗しました")
        else:
            print(f"controller_status: {controller_status}")

        motor_status = ctrl.status_all()
        if motor_status is None:
            print("STS? の取得に失敗しました")
        else:
            for status in motor_status:
                print(status)
    finally:
        ctrl.close()


def main1() -> None:
    ip_address = "10.170.10.62"
    port = 7777

    ctrl = PM2CDsingle(ip_address=ip_address, port=port)
    ctrl.remote()

    try:
        if not ctrl.is_connected():
            print("PM2CD へ接続できませんでした")
            return

        version = ctrl.version()
        print(f"version: {version}")

    finally:
        ctrl.close()


def main2() -> None:
    ip_address = "10.170.10.62"
    port = 7777

    ctrl = PM2CDsingle(ip_address=ip_address, port=port)
    try:
        if not ctrl.is_connected():
            print("PM2CD へ接続できませんでした")
            return
        ctrl.remote()
        ctrl.move(1000, motor=0)
        ctrl.wait_for_complete()
        ret = ctrl.get_position()
        print(ret)

    finally:
        ctrl.close()


if __name__ == "__main__":
    # main()
    # main1()
    main2()
