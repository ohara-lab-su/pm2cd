import socket
import threading
from typing import Optional

from .errors import CommunicationError


class Communication:
    """TCP/IPによる1行単位の通信を担当する通信層。

    接続、切断、送信、受信をこのクラスだけで完結させる。
    コマンドと応答の区切り文字は装置仕様に合わせてCR+LFを既定とする。
    """

    def __init__(
        self,
        ip_address: str,
        port: int = 7777,
        timeout: float = 3.0,
        encoding: str = "ascii",
        line_end: str = "\r\n",
    ):
        if not ip_address:
            raise ValueError("ip_addressは空にできません")
        if not 1 <= port <= 65535:
            raise ValueError("portは1から65535の範囲で指定してください")
        if timeout <= 0:
            raise ValueError("timeoutは0より大きい値を指定してください")
        if not line_end:
            raise ValueError("line_endは空にできません")

        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        self.encoding = encoding
        self.line_end = line_end

        self._socket: Optional[socket.socket] = None
        self._receive_buffer = bytearray()
        self._lock = threading.RLock()

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        """TCP接続を確立する。既に接続済みなら何もしない。"""
        with self._lock:
            if self._socket is not None:
                return
            try:
                sock = socket.create_connection(
                    (self.ip_address, self.port),
                    timeout=self.timeout,
                )
                sock.settimeout(self.timeout)
                self._socket = sock
            except OSError as exc:
                raise CommunicationError(
                    f"TCP接続に失敗しました: {self.ip_address}:{self.port}: {exc}"
                ) from exc

    def disconnect(self) -> None:
        """TCP接続を切断する。"""
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
            finally:
                sock.close()

    close = disconnect

    def send(self, command: str) -> None:
        """コマンドをCR+LF付きで送信する。"""
        if not isinstance(command, str):
            raise TypeError("commandはstrで指定してください")
        if self.line_end in command:
            raise ValueError("commandに改行コードを含めないでください")

        with self._lock:
            self.connect()
            data = (command + self.line_end).encode(self.encoding)
            try:
                self._require_socket().sendall(data)
            except (OSError, UnicodeError) as exc:
                self._abort_connection()
                raise CommunicationError(
                    f"コマンド送信に失敗しました: {command!r}: {exc}"
                ) from exc

    def receive(self) -> str:
        """CR+LFまでを1応答として受信する。"""
        with self._lock:
            self.connect()
            delimiter = self.line_end.encode(self.encoding)
            try:
                raw = self._receive_until(delimiter)
                return raw.decode(self.encoding)
            except socket.timeout as exc:
                raise CommunicationError("装置からの応答がタイムアウトしました") from exc
            except (OSError, UnicodeError) as exc:
                self._abort_connection()
                raise CommunicationError(f"応答受信に失敗しました: {exc}") from exc

    def query(self, command: str) -> str:
        """コマンドを送信し、続けて1行の応答を受信する。"""
        with self._lock:
            self.send(command)
            return self.receive()

    def _receive_until(self, delimiter: bytes) -> bytes:
        while True:
            index = self._receive_buffer.find(delimiter)
            if index >= 0:
                raw = bytes(self._receive_buffer[:index])
                del self._receive_buffer[:index + len(delimiter)]
                return raw

            chunk = self._require_socket().recv(4096)
            if not chunk:
                self._abort_connection()
                raise CommunicationError("装置側からTCP接続が切断されました")
            self._receive_buffer.extend(chunk)

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise CommunicationError("TCP接続が確立されていません")
        return self._socket

    def _abort_connection(self) -> None:
        sock = self._socket
        self._socket = None
        self._receive_buffer.clear()
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()
