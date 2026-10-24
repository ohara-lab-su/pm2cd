# Quick Start

[English](../../en/manual/quickstart.html) | [日本語](../../ja/manual/quickstart.html)

`PM2CDsingle` は単一プロセス用、`PM2CD` は `ProcessExecutor` を用いた複数ワーカープロセス用です。装置は2チャンネル固定で、モーター番号は `0` と `1` です。デフォルトTCPポートは `7777`、タイムアウトは `3.0` 秒です。

以下は接続と読み取りのみを行う例です。`PM2CDsingle` のコンストラクタは内部で `connect()` を呼び出します。
```python
from pm2cd.pm2cd_single import PM2CDsingle

IP_ADDRESS: str = "192.0.2.10"  # Replace with the controller's address.

controller = PM2CDsingle(ip_address=IP_ADDRESS)
try:
    print(controller.get_version())
    print(controller.get_position(motor=0))
    print(controller.get_status(motor=0))
finally:
    controller.close()
```


> 実機での移動前に配線、リミットスイッチ、移動方向、可動範囲を確認してください。以下のコードは実機では実行していません。
