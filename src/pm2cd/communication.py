from typing import Any

from pm2cd.errors import PM2CDCommunicationError


class PM2CDCommunication:
    """PM2CDとの1行単位の送受信を担当する通信層。"""

    def __init__(self, communication: Any, encoding: str = "ascii", line_end: str = "\r\n"):
        self.communication = communication
        self.encoding = encoding
        self.line_end = line_end

    def send(self, command: str) -> None:
        if hasattr(self.communication, "send_line"):
            self.communication.send_line(command)
            return

        if hasattr(self.communication, "write"):
            self.communication.write((command + self.line_end).encode(self.encoding))
            if hasattr(self.communication, "flush"):
                self.communication.flush()
            return

        raise PM2CDCommunicationError("通信オブジェクトには send_line() または write() が必要です")

    def receive(self) -> str:
        if hasattr(self.communication, "read_line"):
            response = self.communication.read_line()
        elif hasattr(self.communication, "readline"):
            response = self.communication.readline()
        else:
            raise PM2CDCommunicationError("通信オブジェクトには read_line() または readline() が必要です")

        if response is None or response == b"" or response == "":
            raise PM2CDCommunicationError("PM2CDから応答がありません")

        if isinstance(response, bytes):
            response = response.decode(self.encoding)

        return str(response).rstrip("\r\n")

    def query(self, command: str) -> str:
        self.send(command)
        return self.receive()