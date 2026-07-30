import socket
import threading
from typing import Optional

from .errors import CommunicationError


class Communication:
    """PMシリーズ用のTCP通信層。

    TCPソケットの生成、接続、CR+LF単位の送受信、切断までをこのクラス内で
    完結させる。外部の通信オブジェクトや別バックエンドは使用しない。
    """

    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout_sec: float = 3.0,
        encoding: str = "ascii",
    ):
        if not isinstance(ip_address, str):
            raise TypeError("ip_addressはstrで指定してください")
        if not ip_address:
            raise ValueError("ip_addressは空にできません")
        if not isinstance(port, int):
            raise TypeError("portはintで指定してください")
        if port < 1 or port > 65535:
            raise ValueError("portは1から65535の範囲で指定してください")
        if timeout_sec <= 0:
            raise ValueError("timeout_secは0より大きい値を指定してください")

        self.ip_address = ip_address
        self.port = port
        self.timeout_sec = timeout_sec
        self.encoding = encoding

        self._socket: Optional[socket.socket] = None
        self._receive_buffer = bytearray()
        self._delimiter = b"\r\n"
        self._lock = threading.RLock()

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        with self._lock:
            if self._socket is not None:
                return

            try:
                sock = socket.create_connection(
                    (self.ip_address, self.port),
                    timeout=self.timeout_sec,
                )
                sock.settimeout(self.timeout_sec)
            except OSError as exc:
                raise CommunicationError(
                    f"TCP接続に失敗しました: {self.ip_address}:{self.port}"
                ) from exc

            self._socket = sock
            self._receive_buffer.clear()

    def disconnect(self) -> None:
        with self._lock:
            sock = self._socket
            self._socket = None
            self._receive_buffer.clear()

            if sock is None:
                return

            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                sock.close()
            except OSError as exc:
                raise CommunicationError("TCP切断に失敗しました") from exc

    def send(self, command: str) -> None:
        if not isinstance(command, str):
            raise TypeError("commandはstrで指定してください")
        if "\r" in command or "\n" in command:
            raise ValueError("commandに改行文字を含めることはできません")

        with self._lock:
            sock = self._require_socket()
            data = command.encode(self.encoding) + self._delimiter
            try:
                sock.sendall(data)
            except (OSError, socket.timeout) as exc:
                self._close_after_error()
                raise CommunicationError(
                    f"コマンド送信に失敗しました: {command!r}"
                ) from exc

    def receive(self) -> str:
        with self._lock:
            while True:
                delimiter_index = self._receive_buffer.find(self._delimiter)
                if delimiter_index >= 0:
                    raw = bytes(self._receive_buffer[:delimiter_index])
                    del self._receive_buffer[
                        :delimiter_index + len(self._delimiter)
                    ]
                    try:
                        return raw.decode(self.encoding)
                    except UnicodeDecodeError as exc:
                        raise CommunicationError(
                            "装置応答のデコードに失敗しました"
                        ) from exc

                sock = self._require_socket()
                try:
                    chunk = sock.recv(4096)
                except socket.timeout as exc:
                    raise CommunicationError(
                        "装置応答の受信がタイムアウトしました"
                    ) from exc
                except OSError as exc:
                    self._close_after_error()
                    raise CommunicationError(
                        "装置応答の受信に失敗しました"
                    ) from exc

                if not chunk:
                    self._close_after_error()
                    raise CommunicationError(
                        "装置側からTCP接続が切断されました"
                    )

                self._receive_buffer.extend(chunk)

    def query(self, command: str) -> str:
        with self._lock:
            self.send(command)
            return self.receive()

    def close(self) -> None:
        self.disconnect()

    def __enter__(self) -> "Communication":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise CommunicationError("TCP接続されていません")
        return self._socket

    def _close_after_error(self) -> None:
        sock = self._socket
        self._socket = None
        self._receive_buffer.clear()
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
