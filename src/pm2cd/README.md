# PM16C-16 Python package

3層構成です。

- `PM16C16Communication`: 外部から渡された通信オブジェクトと送受信する
- `PM16C16Device`: PM16C-16コマンド、応答解析、装置状態を扱う
- `PM16C16`: Python利用者向けI/F

通信オブジェクトの生成、接続、切断はこのパッケージでは行いません。

```python
from pm16c16 import PM16C16

communication = ExistingCommunicationObject(...)
pm = PM16C16(communication)

pm.remote()
print(pm.version())
pm.set_speed(0, 1000)
pm.move(0, 10000)
print(pm.wait_stop(0))
```

通信オブジェクトは、次のいずれかを実装してください。

- `send_line(str)` と `read_line()`
- `write(bytes)` と `readline()`
