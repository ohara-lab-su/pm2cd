import logging
import socket
import threading
from typing import Optional

from pm2cd.core.errors import CommunicationError

# TCP通信層。PM2CD 固有のコマンド解釈は行わず、送受信だけを担当する。
# 通信異常時は接続状態と受信バッファを破棄し、次回通信へ異常応答を持ち越さない。


class Communication:
    """PMシリーズ用のTCP通信層。

    TCPソケットの生成、接続、CR+LF単位の送受信、切断までをこのクラス内で
    完結させる。

    通常運転中に発生し得る通信失敗はログへ原因を記録し、``False`` または
    ``None`` を返す。コンストラクタ引数の不正など、戻り値では表現できない
    呼び出し側の誤りは例外とする。
    """

    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        encoding: str = "ascii",
        logger=None,
        log_level: str = "INFO",
    ):
        """インスタンスを初期化する。

        Args:
            ip_address: PM2CD の IP アドレス。
            port: PM2CD の TCP ポート番号。
            timeout_sec: TCP 通信および待機処理のタイムアウト秒数。
            encoding: encoding。
            logger: 使用する logger。None の場合はこのモジュールで生成する。
            log_level: logger を生成する場合のログレベル。

        Raises:
            TypeError: 引数の型が不正な場合。
            ValueError: 引数の値が不正な場合。
        """
        if not logger:
            logging.basicConfig(level=(log_level or "INFO").upper())
            logger = logging.getLogger(__name__)

        self._logger = logger

        if not isinstance(ip_address, str):
            raise TypeError("ip_addressはstrで指定してください")

        if not ip_address:
            raise ValueError("ip_addressは空にできません")

        if not isinstance(port, int) or isinstance(port, bool):
            raise TypeError("portはintで指定してください")

        if port < 1 or port > 65535:
            raise ValueError("portは1から65535の範囲で指定してください")

        if not isinstance(timeout_sec, (int, float)) or isinstance(timeout_sec, bool):
            raise TypeError("timeout_secは数値で指定してください")

        if timeout_sec <= 0:
            raise ValueError("timeout_secは0より大きい値を指定してください")

        if not isinstance(encoding, str):
            raise TypeError("encodingはstrで指定してください")

        self._ip_address = ip_address
        self._port = port
        self._timeout_sec = timeout_sec
        self._encoding = encoding

        self._socket = None  # type: Optional[socket.socket]
        self._receive_buffer = bytearray()
        self._delimiter = b"\r\n"
        self._lock = threading.RLock()

    @property
    def ip_address(
        self,
    ):
        """ip_address を返す。"""
        return self._ip_address

    @property
    def port(
        self,
    ):
        """port を返す。"""
        return self._port

    @property
    def timeout_sec(
        self,
    ):
        """timeout_sec を返す。"""
        return self._timeout_sec

    @property
    def encoding(
        self,
    ):
        """encoding を返す。"""
        return self._encoding

    def is_connected(
        self,
    ) -> bool:
        """TCP 接続状態を取得する。

        Returns:
            接続中の場合は True、それ以外は False。
        """
        if self._socket is None:
            return False

        return True

    def connect(
        self,
    ) -> bool:
        """TCP接続する。

        Returns:
            接続済み、または接続に成功した場合は ``True``。
            接続に失敗した場合は ``False``。
        """
        self._logger.info(f"== connect()")

        # 接続状態の変更を送受信と同じロックで直列化する。
        with self._lock:
            if self._socket is not None:
                return True

            sock = None  # type: Optional[socket.socket]

            try:
                sock = socket.create_connection(
                    (self._ip_address, self._port), timeout=self._timeout_sec
                )
                sock.settimeout(self._timeout_sec)
            except OSError as exc:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError as close_exc:
                        self._logger.error(
                            f"接続失敗後のTCPソケット破棄にも失敗しました: {close_exc}"
                        )

                message = (
                    f"TCP接続に失敗しました: {self._ip_address}:{self._port}: {exc}"
                )
                self._logger.error(message)
                return False

            # 新しい TCP セッションへ以前の受信断片を持ち越さない。
            self._socket = sock
            self._receive_buffer.clear()

            self._logger.info(f"TCP接続しました: {self._ip_address}:{self._port}")
            return True

    def disconnect(
        self,
    ) -> bool:
        """TCP接続を切断する。"""
        self._logger.info(f"== disconnect()")

        with self._lock:
            # 切断処理中に別経路から古いソケットを使用しないよう、先に内部状態を切り離す。
            sock = self._socket
            self._socket = None
            self._receive_buffer.clear()

            if sock is None:
                return True

            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                sock.close()
            except OSError as exc:
                self._logger.error(f"TCP切断に失敗しました: {exc}")
                return False

            self._logger.info(f"TCP切断しました")
            return True

    def send(
        self,
        command: str,
    ) -> bool:
        """CR+LFを付加してコマンドを送信する。"""
        self._logger.info(f"== send(): {command!r}")

        if not isinstance(command, str):
            raise TypeError("commandはstrで指定してください")

        if "\r" in command or "\n" in command:
            raise ValueError("commandに改行文字を含めることはできません")

        with self._lock:
            return self._send(command)

    def receive(
        self,
    ) -> Optional[str]:
        """CR+LF単位で装置応答を1件受信する。"""
        self._logger.info(f"== receive()")

        with self._lock:
            return self._receive()

    def query(
        self,
        command: str,
    ) -> Optional[str]:
        """コマンドを送信し、その応答を1件受信する。"""
        self._logger.debug(f"== query(): {command!r}")

        if not isinstance(command, str):
            raise TypeError("commandはstrで指定してください")

        if "\r" in command or "\n" in command:
            raise ValueError("commandに改行文字を含めることはできません")

        with self._lock:
            # query は同一ロック内で send -> receive を完結させ、別コマンドの応答が
            # 間へ入り込まないようにする。
            if not self._send(command):
                return None

            return self._receive()

    def close(
        self,
    ) -> bool:
        """通信を終了する。"""
        return self.disconnect()

    def __enter__(
        self,
    ) -> "Communication":
        """context manager 開始時に接続を確立する。

        Returns:
            'Communication' 型の結果。

        Raises:
            CommunicationError: PM2CD への接続を確立できない場合。
        """
        if not self.connect():
            raise CommunicationError(
                f"TCP接続を開始できません: {self._ip_address}:{self._port}"
            )

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
        self.disconnect()

    def _send(
        self,
        command: str,
    ) -> bool:
        """ロック取得済みの状態でコマンドを送信する。"""
        sock = self._require_socket("送信")
        if sock is None:
            return False

        try:
            data = command.encode(self._encoding) + self._delimiter
        except (UnicodeEncodeError, LookupError) as exc:
            self._logger.error(
                f"コマンドのエンコードに失敗しました: {command!r}: {exc}"
            )
            return False

        try:
            sock.sendall(data)
        except (OSError, socket.timeout) as exc:
            self._logger.error(f"コマンド送信に失敗しました: {command!r}: {exc}")
            self._close_after_error()
            return False

        return True

    def _receive(
        self,
    ) -> Optional[str]:
        """ロック取得済みの状態で応答を1件受信する。"""
        while True:
            # 受信済みバッファからCR+LF終端の1応答だけを切り出す。
            delimiter_index = self._receive_buffer.find(self._delimiter)

            if delimiter_index >= 0:
                raw = bytes(self._receive_buffer[:delimiter_index])
                del self._receive_buffer[: delimiter_index + len(self._delimiter)]

                try:
                    response = raw.decode(self._encoding)
                except (UnicodeDecodeError, LookupError) as exc:
                    self._logger.error(f"装置応答のデコードに失敗しました: {exc}")
                    self._close_after_error()
                    return None

                return response

            sock = self._require_socket("受信")
            if sock is None:
                return None

            try:
                chunk = sock.recv(4096)
            except socket.timeout as exc:
                self._logger.error(f"装置応答の受信がタイムアウトしました: {exc}")

                # タイムアウト後に遅延応答が到着すると、次のqueryが古い応答を
                # 誤って受信する可能性があるため、接続を破棄して同期を取り直す。
                self._close_after_error()
                return None
            except OSError as exc:
                self._logger.error(f"装置応答の受信に失敗しました: {exc}")
                self._close_after_error()
                return None

            if not chunk:
                self._logger.error(f"装置側からTCP接続が切断されました")
                self._close_after_error()
                return None

            self._receive_buffer.extend(chunk)

    def _require_socket(
        self,
        operation: str,
    ) -> Optional[socket.socket]:
        """接続済みソケットを返す。"""
        if self._socket is None:
            self._logger.error(f"TCP接続されていないため{operation}できません")
            return None

        return self._socket

    def _close_after_error(
        self,
    ) -> None:
        """通信異常後にソケットと受信バッファを破棄する。"""
        # エラー発生後はソケット参照を先に無効化し、再利用を防止する。
        sock = self._socket
        self._socket = None
        self._receive_buffer.clear()

        if sock is None:
            return

        try:
            sock.close()
        except OSError as exc:
            self._logger.error(f"通信異常後のTCPソケット破棄に失敗しました: {exc}")


def main() -> None:
    """Communication の基本的な送受信例を実行する。

    実機の IP アドレスに変更してから、パッケージのモジュールとして実行する。
    ``VER?`` を送信し、CR+LF で区切られた装置応答を 1 件受信する。

    Returns:
        None。
    """
    ip_address = "10.170.10.62"
    port = 7777

    communication = Communication(ip_address=ip_address, port=port)

    if not communication.connect():
        print("PM2CD へ接続できませんでした")
        return

    try:
        response = communication.query("VER?")
        if response is None:
            print("VER? の取得に失敗しました")
        else:
            print(f"VER?: {response}")
    finally:
        communication.disconnect()


if __name__ == "__main__":
    main()
