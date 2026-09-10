import logging
import time
from typing import List, Optional, Union

from pm2cd.core.communication_tcp import Communication
from pm2cd.core.controller_status import ControllerStatus
from pm2cd.core.home_status import HomeStatus
from pm2cd.core.limit_switch_setting import LimitSwitchSetting
from pm2cd.core.motor_setting import MotorSetting
from pm2cd.core.motor_status import MotorStatus
from pm2cd.core.stop_mode import StopMode
from pm2cd.core.version_info import VersionInfo
from pm2cd.pm2cd_device import PM2CDDevice

# PM2CD の公開制御API。
# 通信層と装置コマンド層を委譲で束ね、上位コードへ装置操作を提供する。


class PM2CD:
    """PM2CD を Python から制御するための公開 I/F。"""

    # --- 初期化・接続管理 ------------------------------------------------------
    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        channel_count: int = 2,
        logger=None,
        log_level: str = "INFO",
    ):
        """インスタンスを初期化する。

        Args:
            ip_address: PM2CD の IP アドレス。
            port: PM2CD の TCP ポート番号。
            timeout_sec: TCP 通信および待機処理のタイムアウト秒数。
            channel_count: 制御対象チャンネル数。PM2CD では 2 固定。
            logger: 使用する logger。None の場合はこのモジュールで生成する。
            log_level: logger を生成する場合のログレベル。

        Raises:
            ValueError: PM2CD 固有の固定条件に反する設定が指定された場合。
        """
        if not logger:
            logging.basicConfig(level=(log_level or "INFO").upper())
            logger = logging.getLogger(__name__)

        self._logger = logger

        if channel_count != 2:
            raise ValueError(f"PM2CDのchannel_countは2です: {channel_count}")

        self._communication = Communication(
            ip_address=ip_address,
            port=port,
            timeout_sec=timeout_sec,
            logger=self._logger,
            log_level=log_level,
        )
        self._device = PM2CDDevice(
            communication=self._communication,
            channel_count=channel_count,
            logger=self._logger,
            log_level=log_level,
        )
        self._communication.connect()

    @property
    def is_connected(
        self,
    ) -> bool:
        """TCP 接続状態を取得する。

        Returns:
            接続中の場合は True、それ以外は False。
        """
        return self._communication.is_connected

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

    def get_version(
        self,
    ) -> Optional[VersionInfo]:
        """装置のソフトウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_version()

    def get_hardware_version(
        self,
    ) -> Optional[str]:
        """装置のハードウェアバージョン情報を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_hardware_version()

    def get_controller_status(
        self,
    ) -> Optional[ControllerStatus]:
        """コントローラー全体の状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_controller_status()

    # --- モータ動作 ------------------------------------------------------------
    def move(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> bool:
        """指定モーターを絶対位置へ移動する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.move(motor, pulse, backlash)

    def move_relative(
        self,
        motor: int,
        pulse: int,
        backlash: Union[str, bool, None] = True,
    ) -> bool:
        """指定モーターを現在位置から相対移動する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.move_relative(motor, pulse, backlash)

    def scan(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ連続スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.scan(motor, direction)

    def constant_speed_scan(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ定速スキャン動作を開始する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.constant_speed_scan(motor, direction)

    def jog(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ JOG 動作する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.jog(motor, direction)

    def scan_home(
        self,
        motor: int,
        direction: str,
    ) -> bool:
        """指定方向へ原点探索スキャンを開始する。

        Args:
            motor: モーター番号。0 または 1。
            direction: 回転方向。cw または ccw。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.scan_home(motor, direction)

    def home(
        self,
        motor: int,
    ) -> bool:
        """記録済み原点位置へ移動する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.home(motor)

    def find_home(
        self,
        motor: int,
    ) -> bool:
        """原点検出動作を開始する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.find_home(motor)

    # --- 停止・状態監視 --------------------------------------------------------
    def stop(
        self,
        motor: int,
    ) -> bool:
        """指定モーターを停止する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.stop(motor)

    def stop_all(
        self,
    ) -> bool:
        """全モーターを停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.stop_all()

    def emergency_stop(
        self,
        motor: int,
    ) -> bool:
        """指定モーターを非常停止する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.emergency_stop(motor)

    def emergency_stop_all(
        self,
    ) -> bool:
        """全モーターを非常停止する。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.emergency_stop_all()

    def get_status(
        self,
        motor: int,
    ) -> Optional[MotorStatus]:
        """指定モーターの状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_status(motor)

    def get_status_all(
        self,
    ) -> Optional[List[MotorStatus]]:
        """全モーターの状態を取得する。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_status_all()

    def get_rotate(
        self,
        motor: int,
    ) -> Optional[bool]:
        """指定モーターが回転中か確認する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_rotate(motor)

    def is_busy(
        self,
        motor: int,
    ) -> Optional[bool]:
        """指定モーターの BUSY 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        status = self.get_status(motor)
        if status is None:
            return None

        return status.is_busy

    def wait_stop(
        self,
        motor: int,
        timeout_sec: float = 30.0,
        interval_sec: float = 0.1,
    ) -> Optional[MotorStatus]:
        """指定モーターが停止するまで状態を監視する。

        Args:
            motor: モーター番号。0 または 1。
            timeout_sec: TCP 通信および待機処理のタイムアウト秒数。
            interval_sec: 状態確認のポーリング間隔秒数。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        # wall clock の補正に影響されない monotonic clock で待機期限を管理する。
        deadline = time.monotonic() + timeout_sec

        while True:
            status = self.get_status(motor)
            if status is None:
                return None

            if not status.is_busy:
                return status

            if time.monotonic() >= deadline:
                self._logger.error(f"wait_stop(): motor {motor} が停止しませんでした")
                return None

            time.sleep(interval_sec)

    # --- 位置・速度設定 --------------------------------------------------------
    def get_position(
        self,
        motor: int,
    ) -> Optional[int]:
        """指定モーターの現在位置を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_position(motor)

    def set_position(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """指定モーターの現在位置カウンタを設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_position(motor, pulse)

    def zero_position(
        self,
        motor: int,
    ) -> bool:
        """指定モーターの現在位置カウンタを 0 にする。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self.set_position(motor, 0)

    def get_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """set_speed() の基準となる高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_speed(motor)

    def set_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """高速値を基準に低速・中速・高速を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_speed(motor, speed)

    def get_speed_profile(
        self,
        motor: int,
    ) -> Optional[List[int]]:
        """低速・中速・高速の設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            低速・中速・高速の順の設定値。取得に失敗した場合は None。
        """
        return self._device.get_speed_profile(motor)

    def set_speed_profile(
        self,
        motor: int,
        low_speed: int,
        middle_speed: int,
        high_speed: int,
    ) -> bool:
        """低速・中速・高速を個別に設定する。

        Args:
            motor: モーター番号。0 または 1。
            low_speed: 低速値。
            middle_speed: 中速値。
            high_speed: 高速値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_speed_profile(
            motor, low_speed, middle_speed, high_speed
        )

    def get_high_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """高速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_high_speed(motor)

    def set_high_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """高速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_high_speed(motor, speed)

    def get_middle_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """中速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_middle_speed(motor)

    def set_middle_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """中速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_middle_speed(motor, speed)

    def get_low_speed(
        self,
        motor: int,
    ) -> Optional[int]:
        """低速設定値を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_low_speed(motor)

    def set_low_speed(
        self,
        motor: int,
        speed: int,
    ) -> bool:
        """低速設定値を設定する。

        Args:
            motor: モーター番号。0 または 1。
            speed: 速度。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_low_speed(motor, speed)

    def get_speed_mode(
        self,
        motor: int,
    ) -> Optional[str]:
        """現在の速度モードを取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_speed_mode(motor)

    def set_speed_mode(
        self,
        motor: int,
        mode: Union[int, str],
    ) -> bool:
        """速度モードを設定する。

        Args:
            motor: モーター番号。0 または 1。
            mode: 速度モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_speed_mode(motor, mode)

    # --- 加減速・バックラッシュ・リミット ------------------------------------
    def get_rate_number(
        self,
        motor: int,
    ) -> Optional[int]:
        """加減速レート番号を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_rate_number(motor)

    def set_rate_number(
        self,
        motor: int,
        number: int,
    ) -> bool:
        """加減速レート番号を設定する。

        Args:
            motor: モーター番号。0 または 1。
            number: レート番号。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_rate_number(motor, number)

    def get_backlash(
        self,
        motor: int,
    ) -> Optional[int]:
        """バックラッシュ補正量を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_backlash(motor)

    def set_backlash(
        self,
        motor: int,
        backlash: int,
    ) -> bool:
        """バックラッシュ補正量を設定する。

        Args:
            motor: モーター番号。0 または 1。
            backlash: バックラッシュ補正指定。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_backlash(motor, backlash)

    def get_limit(
        self,
        motor: int,
        side: str,
    ) -> Optional[int]:
        """指定側のソフトウェアリミット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。
            side: リミット側。cw または ccw。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_limit(motor, side)

    def set_limit(
        self,
        motor: int,
        side: str,
        pulse: int,
    ) -> bool:
        """指定側のソフトウェアリミット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。
            side: リミット側。cw または ccw。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_limit(motor, side, pulse)

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
        return self._device.get_pause_status()

    def get_hold(
        self,
        motor: int,
    ) -> Optional[str]:
        """指定モーターの HOLD 状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_hold(motor)

    def set_hold(
        self,
        motor: int,
        enabled: bool,
    ) -> bool:
        """指定モーターの HOLD 状態を設定する。

        Args:
            motor: モーター番号。0 または 1。
            enabled: 有効にする場合は True、無効にする場合は False。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_hold(motor, enabled)

    def get_hold_on_time(
        self,
        motor: int,
    ) -> Optional[int]:
        """HOLD ON 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_hold_on_time(motor)

    def set_hold_on_time(
        self,
        motor: int,
        msec: int,
    ) -> bool:
        """HOLD ON 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_hold_on_time(motor, msec)

    def get_hold_off_time(
        self,
        motor: int,
    ) -> Optional[int]:
        """HOLD OFF 時間を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_hold_off_time(motor)

    def set_hold_off_time(
        self,
        motor: int,
        msec: int,
    ) -> bool:
        """HOLD OFF 時間を設定する。

        Args:
            motor: モーター番号。0 または 1。
            msec: 時間。単位は ms。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_hold_off_time(motor, msec)

    # --- 原点関連設定 ----------------------------------------------------------
    def get_home_status(
        self,
        motor: int,
    ) -> Optional[HomeStatus]:
        """原点検出設定状態を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_home_status(motor)

    def set_home_status(
        self,
        motor: int,
        found: bool,
        found_direction: str,
        auto_start_direction: str,
    ) -> bool:
        """原点検出設定状態を設定する。

        Args:
            motor: モーター番号。0 または 1。
            found: 原点検出済み状態。
            found_direction: 原点検出方向。
            auto_start_direction: 自動原点検出開始方向。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_home_status(
            motor, found, found_direction, auto_start_direction
        )

    def get_home_position(
        self,
        motor: int,
    ) -> Optional[int]:
        """記録済み原点位置を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_home_position(motor)

    def set_home_position(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """原点位置を設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_home_position(motor, pulse)

    def get_home_offset(
        self,
        motor: int,
    ) -> Optional[int]:
        """原点オフセットを取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_home_offset(motor)

    def set_home_offset(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """原点オフセットを設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_home_offset(motor, pulse)

    # --- プリセット・JOG・装置設定 --------------------------------------------
    def get_preset_position(
        self,
        motor: int,
    ) -> Optional[int]:
        """プリセット位置を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_preset_position(motor)

    def set_preset_position(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """プリセット位置を設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_preset_position(motor, pulse)

    def get_jog_pulse(
        self,
        motor: int,
    ) -> Optional[int]:
        """JOG パルス数を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_jog_pulse(motor)

    def set_jog_pulse(
        self,
        motor: int,
        pulse: int,
    ) -> bool:
        """JOG パルス数を設定する。

        Args:
            motor: モーター番号。0 または 1。
            pulse: パルス値。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_jog_pulse(motor, pulse)

    def get_limit_switch_setting(
        self,
        motor: int,
    ) -> Optional[LimitSwitchSetting]:
        """リミットスイッチ設定を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_limit_switch_setting(motor)

    def get_limit_switch_setting_raw(
        self,
        motor: int,
    ) -> Optional[str]:
        """リミットスイッチ設定を生の設定文字列で取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得した生の設定文字列。失敗した場合は None。
        """
        return self._device.get_limit_switch_setting_raw(motor)

    def set_limit_switch_setting_raw(
        self,
        motor: int,
        setting: str,
    ) -> bool:
        """リミットスイッチ設定を生の設定文字列で書き込む。

        Args:
            motor: モーター番号。0 または 1。
            setting: 装置へ設定する生の設定文字列。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_limit_switch_setting_raw(motor, setting)

    def get_motor_setting(
        self,
        motor: int,
    ) -> Optional[MotorSetting]:
        """モーター設定を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_motor_setting(motor)

    def set_motor_setting(
        self,
        motor: int,
        drive_enabled: bool,
        hold_mode: int,
        output_mode: int,
    ) -> bool:
        """モーター設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。
            drive_enabled: モータードライブを有効にする場合は True。
            hold_mode: ホールドモード。
            output_mode: 出力モード。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
        return self._device.set_motor_setting(
            motor, drive_enabled, hold_mode, output_mode
        )

    def get_stop_mode(
        self,
        motor: int,
    ) -> Optional[StopMode]:
        """停止モード設定を取得する。

        Args:
            motor: モーター番号。0 または 1。

        Returns:
            取得または変換に成功した値。失敗した場合は None。
        """
        return self._device.get_stop_mode(motor)

    def set_stop_mode(
        self,
        motor: int,
        panel_fast: bool,
        limit_fast: bool,
    ) -> bool:
        """停止モード設定を書き込む。

        Args:
            motor: モーター番号。0 または 1。
            panel_fast: パネル停止を高速停止にする場合は True。
            limit_fast: リミット停止を高速停止にする場合は True。

        Returns:
            処理に成功した場合は True、失敗した場合は False。
        """
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

    # --- context manager -------------------------------------------------------
    def __enter__(
        self,
    ) -> "PM2CD":
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

    ctrl = PM2CD(ip_address=ip_address, port=port)

    try:
        if not ctrl.is_connected:
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


if __name__ == "__main__":
    main()
