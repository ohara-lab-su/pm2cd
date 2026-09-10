import logging
import socket
import threading
from typing import Optional

from .errors import CommunicationError


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

        if not isinstance(
            timeout_sec,
            (
                int,
                float,
            ),
        ) or isinstance(timeout_sec, bool):
            raise TypeError("timeout_secは数値で指定してください")

        if timeout_sec <= 0:
            raise ValueError("timeout_secは0より大きい値を指定してください")

        if not isinstance(encoding, str):
            raise TypeError("encodingはstrで指定してください")

        self.ip_address = ip_address
        self.port = port
        self.timeout_sec = timeout_sec
        self.encoding = encoding

        self._socket = None  # type: Optional[socket.socket]
        self._receive_buffer = bytearray()
        self._delimiter = b"\r\n"
        self._lock = threading.RLock()

    @property
    def is_connected(
        self,
    ) -> bool:
        return self._socket is not None

    def connect(
        self,
    ) -> bool:
        """TCP接続する。

        Returns:
            接続済み、または接続に成功した場合は ``True``。
            接続に失敗した場合は ``False``。
        """
        self._logger.info(f"== connect()")

        with self._lock:
            if self._socket is not None:
                return True

            sock = None  # type: Optional[socket.socket]

            try:
                sock = socket.create_connection(
                    (
                        self.ip_address,
                        self.port,
                    ),
                    timeout=self.timeout_sec,
                )
                sock.settimeout(self.timeout_sec)
            except OSError as exc:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError as close_exc:
                        self._logger.error(
                            f"接続失敗後のTCPソケット破棄にも失敗しました: "
                            f"{close_exc}"
                        )

                self._logger.error(
                    f"TCP接続に失敗しました: " f"{self.ip_address}:{self.port}: {exc}"
                )
                return False

            self._socket = sock
            self._receive_buffer.clear()

            self._logger.info(f"TCP接続しました: {self.ip_address}:{self.port}")
            return True

    def disconnect(
        self,
    ) -> bool:
        """TCP接続を切断する。"""
        self._logger.info(f"== disconnect()")

        with self._lock:
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
        self._logger.info(f"== query(): {command!r}")

        if not isinstance(command, str):
            raise TypeError("commandはstrで指定してください")

        if "\r" in command or "\n" in command:
            raise ValueError("commandに改行文字を含めることはできません")

        with self._lock:
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
        if not self.connect():
            raise CommunicationError(
                f"TCP接続を開始できません: " f"{self.ip_address}:{self.port}"
            )

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
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
            data = command.encode(self.encoding) + self._delimiter
        except (UnicodeEncodeError, LookupError) as exc:
            self._logger.error(
                f"コマンドのエンコードに失敗しました: " f"{command!r}: {exc}"
            )
            return False

        try:
            sock.sendall(data)
        except (OSError, socket.timeout) as exc:
            self._logger.error(f"コマンド送信に失敗しました: " f"{command!r}: {exc}")
            self._close_after_error()
            return False

        return True

    def _receive(
        self,
    ) -> Optional[str]:
        """ロック取得済みの状態で応答を1件受信する。"""
        while True:
            delimiter_index = self._receive_buffer.find(self._delimiter)

            if delimiter_index >= 0:
                raw = bytes(self._receive_buffer[:delimiter_index])
                del self._receive_buffer[: delimiter_index + len(self._delimiter)]

                try:
                    response = raw.decode(self.encoding)
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
        sock = self._socket
        self._socket = None
        self._receive_buffer.clear()

        if sock is None:
            return

        try:
            sock.close()
        except OSError as exc:
            self._logger.error(f"通信異常後のTCPソケット破棄に失敗しました: {exc}")
