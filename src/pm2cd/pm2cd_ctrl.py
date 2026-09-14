#!/usr/bin/env python
# coding: utf-8
"""PM2CD の multiprocessing 対応公開 I/F。"""

from functools import partial
from multiprocessing.managers import BaseManager
from types import MethodType
from typing import Any, List, Optional, Union

from pm2cd.core.communication_tcp import Communication
from pm2cd.core.controller_status import ControllerStatus
from pm2cd.core.home_status import HomeStatus
from pm2cd.core.motor_setting import MotorSetting
from pm2cd.core.motor_status import MotorStatus
from pm2cd.core.stop_mode import StopMode
from pm2cd.core.version_info import VersionInfo
from pm2cd.pm2cd_single import PM2CDsingle
from process_executor import ProcessExecutor
from process_executor.shared_context import SharedContext
from x_logger import XLogger


_SHARED_MOTOR_KEY = "__motor__"
_DISPATCH_HANDLER = "__process_executor_dispatch__"


class _CommunicationManager(BaseManager):
    """単一の Communication を所有する manager。"""


_CommunicationManager.register(
    "Communication",
    Communication,
    exposed=(
        "is_connected",
        "connect",
        "disconnect",
        "send",
        "receive",
        "query",
        "close",
    ),
)


def _create_worker(
    context: SharedContext,
    ip_address: str,
    port: int,
    timeout_sec: float,
    channel_count: int,
    communication: Any,
    log_level: str,
) -> PM2CDsingle:
    """共有 Communication と SharedContext を使用する worker を生成する。"""
    worker = PM2CDsingle(
        ip_address=ip_address,
        port=port,
        timeout_sec=timeout_sec,
        channel_count=channel_count,
        communication=communication,
        log_level=log_level,
    )

    # move()/move_relative() と wait_for_complete() の間で使用する
    # 移動条件を全 worker で共有する。
    worker._move_context = context.state

    def dispatch(
        instance: PM2CDsingle,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """共有状態を反映して PM2CDsingle の public method を実行する。"""
        with context.lock:
            instance._motor = context.state.get(_SHARED_MOTOR_KEY, 0)

        try:
            handler = getattr(instance, method)
            return handler(*args, **kwargs)
        finally:
            # stop_all()/emergency_stop_all() は _move_context.clear() を行うため、
            # motor は method 実行後に必ず共有状態へ戻す。
            with context.lock:
                context.state[_SHARED_MOTOR_KEY] = instance._motor

    setattr(
        worker,
        _DISPATCH_HANDLER,
        MethodType(dispatch, worker),
    )
    return worker


class PM2CD:
    """PM2CDsingle を worker process 内で実行する公開 I/F。"""

    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        channel_count: int = 2,
        worker_count: int = 2,
        logger: Any = None,
        log_level: str = "INFO",
    ) -> None:
        """インスタンスを初期化する。

        Args:
            ip_address: PM2CD の IP アドレス。
            port: PM2CD の TCP ポート番号。
            timeout_sec: TCP 通信および待機処理のタイムアウト秒数。
            channel_count: 制御対象チャンネル数。PM2CD では 2 固定。
            worker_count: ProcessExecutor の worker process 数。
            logger: 使用する logger。None の場合はこのモジュールで生成する。
            log_level: logger を生成する場合のログレベル。
        """
        if logger is None:
            logger = XLogger(
                log_level=log_level,
                logger_name="PM2CD",
            )

        self._logger = logger

        worker_log_level = log_level
        if hasattr(logger, "get_log_level"):
            worker_log_level = logger.get_log_level()

        self._communication_manager = _CommunicationManager()
        self._communication_manager.start()

        try:
            self._communication = self._communication_manager.Communication(
                ip_address=ip_address,
                port=port,
                timeout_sec=timeout_sec,
                log_level=worker_log_level,
            )

            worker_factory = partial(
                _create_worker,
                ip_address=ip_address,
                port=port,
                timeout_sec=timeout_sec,
                channel_count=channel_count,
                communication=self._communication,
                log_level=worker_log_level,
            )

            self._executor = ProcessExecutor(
                worker_factory=worker_factory,
                worker_count=worker_count,
                start_method="spawn",
                logger=self._logger,
            )
        except BaseException:
            self._communication_manager.shutdown()
            raise

        self._shared_context = self._executor.shared_context

        with self._shared_context.lock:
            self._shared_context.state[_SHARED_MOTOR_KEY] = 0

    @property
    def motor(self) -> int:
        """引数省略時に使用するモーター番号を取得する。"""
        with self._shared_context.lock:
            return self._shared_context.state.get(_SHARED_MOTOR_KEY, 0)

    @motor.setter
    def motor(self, value: int) -> None:
        """引数省略時に使用するモーター番号を設定する。"""
        if isinstance(value, bool):
            raise TypeError("motor は int で指定してください")

        if not isinstance(value, int):
            raise TypeError("motor は int で指定してください")

        if value not in (0, 1):
            raise ValueError("motor は0または1で指定してください")

        with self._shared_context.lock:
            self._shared_context.state[_SHARED_MOTOR_KEY] = value

    def _execute(
        self,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """PM2CDsingle の public method を worker process で実行する。"""
        job_id = self._executor.submit(
            _DISPATCH_HANDLER,
            method,
            *args,
            **kwargs,
        )
        return self._executor.wait(job_id)

    def is_connected(self) -> bool:
        """TCP 接続状態を取得する。

        Returns:
            接続中の場合は True、それ以外は False。
        """
        return self._execute("is_connected")

    def connect(self) -> bool:
        """PM2CD へ TCP 接続する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("connect")

    def disconnect(self) -> bool:
        """PM2CD との TCP 接続を切断する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("disconnect")

    def remote(self) -> bool:
        """装置をリモート操作モードへ切り替える。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("remote")

    def local(self) -> bool:
        """装置をローカル操作モードへ切り替える。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("local")

    def version(self):
        """version を実行する。"""
        return self._execute("version")

    def get_version(self) -> Optional[VersionInfo]:
        """装置のソフトウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("get_version")

    def get_hardware_version(self) -> Optional[str]:
        """装置のハードウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("get_hardware_version")

    def get_controller_status(self) -> Optional[ControllerStatus]:
        """コントローラー全体の状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("get_controller_status")

    def controller_status(self) -> Optional[ControllerStatus]:
        """コントローラー全体の状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("controller_status")

    def move(self, motor: Optional[int]=None, pulse: Optional[int]=None, backlash: Union[str, bool, None]=True) -> bool:
        """指定モーターを絶対位置へ移動する。

        motor を省略した場合は motor プロパティを使用する。
        wait_for_complete() がバックラッシュ補正を含む位置決め完了を判定できるよう、
        コマンド送信成功時に目標位置とバックラッシュ条件を保存する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: 絶対目標位置。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "move",
            motor=motor,
            pulse=pulse,
            backlash=backlash
        )

    def move_relative(self, motor: Optional[int]=None, pulse: Optional[int]=None, backlash: Union[str, bool, None]=True) -> bool:
        """指定モーターを現在位置から相対移動する。

        motor を省略した場合は motor プロパティを使用する。
        相対移動では wait_for_complete() の最終位置判定に必要なため、送信前の現在位置
        から絶対目標位置を求めて保存する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: 相対移動量。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "move_relative",
            motor=motor,
            pulse=pulse,
            backlash=backlash
        )

    def scan(self, motor: Optional[int]=None, direction: Optional[str]=None) -> bool:
        """指定方向へ連続スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "scan",
            motor=motor,
            direction=direction
        )

    def constant_speed_scan(self, motor: Optional[int]=None, direction: Optional[str]=None) -> bool:
        """指定方向へ定速スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "constant_speed_scan",
            motor=motor,
            direction=direction
        )

    def jog(self, motor: Optional[int]=None, direction: Optional[str]=None) -> bool:
        """指定方向へ JOG 動作する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "jog",
            motor=motor,
            direction=direction
        )

    def scan_home(self, motor: Optional[int]=None, direction: Optional[str]=None) -> bool:
        """指定方向へ原点探索スキャンを開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "scan_home",
            motor=motor,
            direction=direction
        )

    def home(self, motor: Optional[int]=None) -> bool:
        """記録済み原点位置へ移動する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "home",
            motor=motor
        )

    def find_home(self, motor: Optional[int]=None) -> bool:
        """原点検出動作を開始する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "find_home",
            motor=motor
        )

    def stop(self, motor: Optional[int]=None) -> bool:
        """指定モーターを停止する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "stop",
            motor=motor
        )

    def stop_all(self) -> bool:
        """全モーターを停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("stop_all")

    def emergency_stop(self, motor: Optional[int]=None) -> bool:
        """指定モーターを非常停止する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "emergency_stop",
            motor=motor
        )

    def emergency_stop_all(self) -> bool:
        """全モーターを非常停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("emergency_stop_all")

    def get_status(self, motor: Optional[int]=None) -> Optional[MotorStatus]:
        """指定モーターの状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_status",
            motor=motor
        )

    def get_status_all(self) -> Optional[List[MotorStatus]]:
        """全モーターの状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("get_status_all")

    def status_all(self) -> Optional[List[MotorStatus]]:
        """全モーターの状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("status_all")

    def get_rotate(self, motor: Optional[int]=None) -> Optional[bool]:
        """指定モーターが回転中か確認する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_rotate",
            motor=motor
        )

    def is_busy(self, motor: Optional[int]=None) -> Optional[bool]:
        """指定モーターの BUSY 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "is_busy",
            motor=motor
        )

    def wait_for_complete(self, motor: Optional[int]=None, timeout_sec: float=30.0, interval_sec: float=0.1, target_position: Optional[int]=None) -> Optional[MotorStatus]:
        """指定モーターの位置決め移動または停止完了を待つ。

        backlash=False の位置決めでは、目標位置で inactive になった時点を完了と
        する。短距離移動では active を観測できないことがあるため、active の観測
        自体は完了条件にしない。

        backlash=B/S の位置決めでは、装置は目標位置を一度通過・停止した後、
        バックラッシュ点へ移動し、最後に目標位置へ戻ることがある。そのため最初の
        「目標位置 + inactive」を最終完了とは扱わない。

        バックラッシュ距離が十分長い場合は、
        目標位置(inactive) -> active -> バックラッシュ点(inactive)
        -> active -> 目標位置(inactive)
        の状態遷移を追跡する。

        バックラッシュ距離が短い場合は途中の active/inactive がポーリング間で
        縮退して観測できるため、途中状態の観測を必須にはしない。最初の目標位置
        inactive を中間到達として保持し、その後に再度目標位置 inactive を観測
        した時点を最終到達とする。最初の中間到達自体を観測できず、補正動作全体が
        ポーリング間で終了した場合も、最終位置が安定して再観測されれば完了できる。

        move()/move_relative() の直後であれば、保存された目標位置・backlash 指定・
        backlash 値を自動的に使用する。target_position が明示された場合はその値を
        優先する。位置決めコンテキストがない場合は、stop() 後などの単純な停止待ち
        として inactive を連続して確認する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            timeout_sec: 待機処理のタイムアウト秒数。
            interval_sec: 状態確認のポーリング間隔秒数。
            target_position: 完了判定に使う目標位置。None の場合は直前の
                move()/move_relative() の目標位置を使用する。

        Returns:
            完了条件を満たした最後の MotorStatus。状態取得失敗または
            タイムアウト時は None。
        """
        return self._execute(
            "wait_for_complete",
            motor=motor,
            timeout_sec=timeout_sec,
            interval_sec=interval_sec,
            target_position=target_position
        )

    def get_position(self, motor: Optional[int]=None) -> Optional[int]:
        """指定モーターの現在位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_position",
            motor=motor
        )

    def set_position(self, motor: Optional[int]=None, pulse: Optional[int]=None) -> bool:
        """指定モーターの現在位置カウンタを設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_position",
            motor=motor,
            pulse=pulse
        )

    def zero_position(self, motor: Optional[int]=None) -> bool:
        """指定モーターの現在位置カウンタを 0 にする。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "zero_position",
            motor=motor
        )

    def get_speed(self, motor: Optional[int]=None) -> Optional[int]:
        """set_speed() の基準となる高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_speed",
            motor=motor
        )

    def set_speed(self, motor: Optional[int]=None, speed: Optional[int]=None) -> bool:
        """高速値を基準に低速・中速・高速を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_speed",
            motor=motor,
            speed=speed
        )

    def get_speed_profile(self, motor: Optional[int]=None) -> Optional[List[int]]:
        """低速・中速・高速の設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            低速・中速・高速の順の設定値。取得に失敗した場合は None。
        """
        return self._execute(
            "get_speed_profile",
            motor=motor
        )

    def set_speed_profile(self, motor: Optional[int]=None, low_speed: Optional[int]=None, middle_speed: Optional[int]=None, high_speed: Optional[int]=None) -> bool:
        """低速・中速・高速を個別に設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            low_speed: 低速値。
            middle_speed: 中速値。
            high_speed: 高速値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_speed_profile",
            motor=motor,
            low_speed=low_speed,
            middle_speed=middle_speed,
            high_speed=high_speed
        )

    def get_high_speed(self, motor: Optional[int]=None) -> Optional[int]:
        """高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_high_speed",
            motor=motor
        )

    def set_high_speed(self, motor: Optional[int]=None, speed: Optional[int]=None) -> bool:
        """高速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_high_speed",
            motor=motor,
            speed=speed
        )

    def get_middle_speed(self, motor: Optional[int]=None) -> Optional[int]:
        """中速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_middle_speed",
            motor=motor
        )

    def set_middle_speed(self, motor: Optional[int]=None, speed: Optional[int]=None) -> bool:
        """中速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_middle_speed",
            motor=motor,
            speed=speed
        )

    def get_low_speed(self, motor: Optional[int]=None) -> Optional[int]:
        """低速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_low_speed",
            motor=motor
        )

    def set_low_speed(self, motor: Optional[int]=None, speed: Optional[int]=None) -> bool:
        """低速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_low_speed",
            motor=motor,
            speed=speed
        )

    def get_speed_mode(self, motor: Optional[int]=None) -> Optional[str]:
        """現在の速度モードを取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_speed_mode",
            motor=motor
        )

    def set_speed_mode(self, motor: Optional[int]=None, mode: Optional[Union[int, str]]=None) -> bool:
        """速度モードを設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            mode: 速度モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_speed_mode",
            motor=motor,
            mode=mode
        )

    def get_rate_number(self, motor: Optional[int]=None) -> Optional[int]:
        """加減速レート番号を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_rate_number",
            motor=motor
        )

    def set_rate_number(self, motor: Optional[int]=None, number: Optional[int]=None) -> bool:
        """加減速レート番号を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            number: レート番号。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_rate_number",
            motor=motor,
            number=number
        )

    def get_rate(self, motor: Optional[int]=None) -> Optional[float]:
        """加減速レートを取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            加減速レート。取得に失敗した場合は None。
        """
        return self._execute(
            "get_rate",
            motor=motor
        )

    def set_rate(self, motor: Optional[int]=None, rate: Optional[float]=None) -> bool:
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
        return self._execute(
            "set_rate",
            motor=motor,
            rate=rate
        )

    def get_backlash(self, motor: Optional[int]=None) -> Optional[int]:
        """バックラッシュ補正量を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_backlash",
            motor=motor
        )

    def set_backlash(self, motor: Optional[int]=None, backlash: Optional[int]=None) -> bool:
        """バックラッシュ補正量を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_backlash",
            motor=motor,
            backlash=backlash
        )

    def get_limit(self, motor: Optional[int]=None, side: Optional[str]=None) -> Optional[int]:
        """指定側のソフトウェアリミット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            side: リミット側。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_limit",
            motor=motor,
            side=side
        )

    def set_limit(self, motor: Optional[int]=None, side: Optional[str]=None, pulse: Optional[int]=None) -> bool:
        """指定側のソフトウェアリミット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            side: リミット側。cw または ccw。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_limit",
            motor=motor,
            side=side,
            pulse=pulse
        )

    def get_limit_status(self, motor: Optional[int]=None) -> Optional[List[bool]]:
        """ソフトウェアリミット状態を ``[CW, CCW]`` で取得する。"""
        return self._execute(
            "get_limit_status",
            motor=motor
        )

    def get_limit_status_all(self) -> Optional[List[List[bool]]]:
        """全モーターのソフトウェアリミット状態を ``[[CW, CCW], ...]`` で取得する。"""
        return self._execute("get_limit_status_all")

    def get_hard_limit_status(self, motor: Optional[int]=None) -> Optional[List[bool]]:
        """ハードウェアリミット状態を ``[CW, CCW, HP]`` で取得する。"""
        return self._execute(
            "get_hard_limit_status",
            motor=motor
        )

    def get_hard_limit_status_all(self) -> Optional[List[List[bool]]]:
        """全モーターのハードウェアリミット状態を ``[[CW, CCW, HP], ...]`` で取得する。"""
        return self._execute("get_hard_limit_status_all")

    def get_limit_enabled(self, motor: Optional[int]=None) -> Optional[bool]:
        """ソフトウェアリミットの有効/無効を取得する。"""
        return self._execute(
            "get_limit_enabled",
            motor=motor
        )

    def set_limit_enabled(self, motor: Optional[int]=None, enabled: Optional[bool]=None) -> bool:
        """ソフトウェアリミットを有効/無効にする。"""
        return self._execute(
            "set_limit_enabled",
            motor=motor,
            enabled=enabled
        )

    def get_hard_limit_enabled(self, motor: Optional[int]=None) -> Optional[List[bool]]:
        """ハードウェアリミット enable 設定を ``[CW, CCW, HP]`` で取得する。"""
        return self._execute(
            "get_hard_limit_enabled",
            motor=motor
        )

    def set_hard_limit_enabled(self, motor: Optional[int]=None, enabled: Optional[bool]=None) -> bool:
        """CW/CCW ハードウェアリミットを有効/無効にする。"""
        return self._execute(
            "set_hard_limit_enabled",
            motor=motor,
            enabled=enabled
        )

    def get_hard_limit_normally_closed(self, motor: Optional[int]=None) -> Optional[List[bool]]:
        """ハードウェアLS接点設定を ``[CW, CCW, HP]`` で取得する。

        True は normally closed、False は normally open を表す。
        """
        return self._execute(
            "get_hard_limit_normally_closed",
            motor=motor
        )

    def set_hard_limit_normally_closed(self, motor: Optional[int]=None, side: Optional[str]=None, normally_closed: Optional[bool]=None) -> bool:
        """ハードウェアLSの接点仕様を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            side: ``hp``、``cw``、``ccw``。
            normally_closed: normally closed にする場合は True、
                normally open にする場合は False。
        """
        return self._execute(
            "set_hard_limit_normally_closed",
            motor=motor,
            side=side,
            normally_closed=normally_closed
        )

    def pause(self) -> bool:
        """動作を一時停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("pause")

    def resume(self) -> bool:
        """一時停止を解除する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute("resume")

    def get_pause_status(self) -> Optional[str]:
        """一時停止状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute("get_pause_status")

    def get_hold(self, motor: Optional[int]=None) -> Optional[str]:
        """指定モーターの HOLD 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_hold",
            motor=motor
        )

    def set_hold(self, motor: Optional[int]=None, enabled: Optional[bool]=None) -> bool:
        """指定モーターの HOLD 状態を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            enabled: 有効にする場合は True、無効にする場合は False。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_hold",
            motor=motor,
            enabled=enabled
        )

    def get_hold_on_time(self, motor: Optional[int]=None) -> Optional[int]:
        """HOLD ON 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_hold_on_time",
            motor=motor
        )

    def set_hold_on_time(self, motor: Optional[int]=None, msec: Optional[int]=None) -> bool:
        """HOLD ON 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_hold_on_time",
            motor=motor,
            msec=msec
        )

    def get_hold_off_time(self, motor: Optional[int]=None) -> Optional[int]:
        """HOLD OFF 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_hold_off_time",
            motor=motor
        )

    def set_hold_off_time(self, motor: Optional[int]=None, msec: Optional[int]=None) -> bool:
        """HOLD OFF 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_hold_off_time",
            motor=motor,
            msec=msec
        )

    def get_home_status(self, motor: Optional[int]=None) -> Optional[HomeStatus]:
        """原点検出設定状態を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_home_status",
            motor=motor
        )

    def set_home_status(self, motor: Optional[int]=None, found: Optional[bool]=None, found_direction: Optional[str]=None, auto_start_direction: Optional[str]=None) -> bool:
        """原点検出設定状態を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            found: 原点検出済み状態。
            found_direction: 原点検出方向。
            auto_start_direction: 自動原点検出開始方向。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_home_status",
            motor=motor,
            found=found,
            found_direction=found_direction,
            auto_start_direction=auto_start_direction
        )

    def get_home_position(self, motor: Optional[int]=None) -> Optional[int]:
        """記録済み原点位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_home_position",
            motor=motor
        )

    def set_home_position(self, motor: Optional[int]=None, pulse: Optional[int]=None) -> bool:
        """原点位置を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_home_position",
            motor=motor,
            pulse=pulse
        )

    def get_home_offset(self, motor: Optional[int]=None) -> Optional[int]:
        """原点オフセットを取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_home_offset",
            motor=motor
        )

    def set_home_offset(self, motor: Optional[int]=None, pulse: Optional[int]=None) -> bool:
        """原点オフセットを設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_home_offset",
            motor=motor,
            pulse=pulse
        )

    def get_preset_position(self, motor: Optional[int]=None) -> Optional[int]:
        """プリセット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_preset_position",
            motor=motor
        )

    def set_preset_position(self, motor: Optional[int]=None, pulse: Optional[int]=None) -> bool:
        """プリセット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_preset_position",
            motor=motor,
            pulse=pulse
        )

    def get_jog_pulse(self, motor: Optional[int]=None) -> Optional[int]:
        """JOG パルス数を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_jog_pulse",
            motor=motor
        )

    def set_jog_pulse(self, motor: Optional[int]=None, pulse: Optional[int]=None) -> bool:
        """JOG パルス数を設定する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_jog_pulse",
            motor=motor,
            pulse=pulse
        )

    def get_limit_switch_setting(self, motor: Optional[int]=None) -> Optional[List[bool]]:
        """リミット設定を意味値のリストで取得する。

        Returns:
            ``[software_enable, CW_enable, CCW_enable, HP_enable,
            CW_normally_closed, CCW_normally_closed, HP_normally_closed]``。
            取得に失敗した場合は None。
        """
        return self._execute(
            "get_limit_switch_setting",
            motor=motor
        )

    def get_motor_setting(self, motor: Optional[int]=None) -> Optional[MotorSetting]:
        """モーター設定を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_motor_setting",
            motor=motor
        )

    def set_motor_setting(self, motor: Optional[int]=None, drive_enabled: Optional[bool]=None, hold_mode: Optional[int]=None, output_mode: Optional[int]=None) -> bool:
        """モーター設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            drive_enabled: モータードライブを有効にする場合は True。
            hold_mode: ホールドモード。
            output_mode: 出力モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_motor_setting",
            motor=motor,
            drive_enabled=drive_enabled,
            hold_mode=hold_mode,
            output_mode=output_mode
        )

    def get_stop_mode(self, motor: Optional[int]=None) -> Optional[StopMode]:
        """停止モード設定を取得する。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._execute(
            "get_stop_mode",
            motor=motor
        )

    def set_stop_mode(self, motor: Optional[int]=None, panel_fast: Optional[bool]=None, limit_fast: Optional[bool]=None) -> bool:
        """停止モード設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。None の場合は motor プロパティを使用する。
            panel_fast: パネル停止を高速停止にする場合は True。
            limit_fast: リミット停止を高速停止にする場合は True。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._execute(
            "set_stop_mode",
            motor=motor,
            panel_fast=panel_fast,
            limit_fast=limit_fast
        )

    def number_to_rate(self, index: int) -> Optional[float]:
        """レート番号を RATE_TABLE のレート値へ変換する。

        Args:
            index: RATE_TABLE のインデックス。

        Returns:
            取得または変換に成功した値。失敗した場合は None。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 変換可能な範囲外の場合。
        """
        return self._execute(
            "number_to_rate",
            index=index
        )

    def rate_to_number(self, rate: float) -> Optional[int]:
        """レート値を対応する RATE_TABLE の番号へ変換する。

        Args:
            rate: 変換するレート値。

        Returns:
            取得または変換に成功した値。失敗した場合は None。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 変換可能な範囲外の場合。
        """
        return self._execute(
            "rate_to_number",
            rate=rate
        )

    def close(self) -> bool:
        """worker、共有通信、Communication manager を終了する。"""
        result = False

        try:
            self._executor.close()
        finally:
            try:
                result = self._communication.close()
            finally:
                self._communication_manager.shutdown()

        return result

    def __enter__(self) -> "PM2CD":
        """context manager 開始時に自身を返す。"""
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """context manager 終了時に通信を終了する。"""
        self.close()
