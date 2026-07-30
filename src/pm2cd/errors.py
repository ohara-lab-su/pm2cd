class PM2CDError(Exception):
    """PM2CD制御に関する基底例外。"""


class PM2CDCommunicationError(PM2CDError):
    """通信処理に失敗した場合の例外。"""


class PM2CDProtocolError(PM2CDError):
    """装置応答を解釈できない場合の例外。"""