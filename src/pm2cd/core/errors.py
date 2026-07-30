class MotorControlError(Exception):
    """モーター制御に関する基底例外。"""


class CommunicationError(MotorControlError):
    """通信処理に失敗した場合の例外。"""


class ProtocolError(MotorControlError):
    """装置応答を解釈できない場合の例外。"""