# 利用例

<a href="https://ohara-lab-su.github.io/pm2cd/en/manual/examples.html">English</a> | <a href="https://ohara-lab-su.github.io/pm2cd/ja/manual/examples.html">日本語</a>

## 状態取得（読み取り専用）

`PM2CDsingle` は構築時に接続を試みます。使用後は `close()` でリソースを解放してください。

## 移動と完了待ち

以下は**装置と移動範囲を検証した環境でのみ**使用する例です。緊急停止手段を別途確保してください。
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
```python
from pm2cd.pm2cd_single import PM2CDsingle

IP_ADDRESS: str = "192.0.2.10"  # Replace with the controller's address.
TARGET_PULSES: int = 100

controller = PM2CDsingle(ip_address=IP_ADDRESS)
try:
    if controller.move(target=TARGET_PULSES, motor=0):
        status = controller.wait_for_complete(motor=0, timeout_sec=30.0)
        print(status)
finally:
    controller.close()
```


> 実機での移動前に配線、リミットスイッチ、移動方向、可動範囲を確認してください。以下のコードは実機では実行していません。
