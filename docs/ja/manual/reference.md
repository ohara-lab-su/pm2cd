# 手動リファレンス

[English](../../en/manual/reference.html) | [日本語](../../ja/manual/reference.html)

## 公開制御クラス

| クラス | 用途 |
|---|---|
| `pm2cd.pm2cd_single.PM2CDsingle` | 単一プロセス制御 |
| `pm2cd.pm2cd_ctrl.PM2CD` | 複数ワーカープロセス制御 |
| `pm2cd.pm2cd_device.PM2CDDevice` | 装置コマンド層 |
| `pm2cd.core.communication_tcp.Communication` | TCP通信層 |

## よく使う操作

| API | 動作 |
|---|---|
| `get_position(motor)` | 現在位置を取得 |
| `move(target, motor, backlash, relative)` | 絶対・相対移動 |
| `move_relative(target, motor, backlash)` | 相対移動 |
| `wait_for_complete(motor, timeout_sec, interval_sec, target_position, show_position)` | 移動完了待機 |
| `stop(motor)` / `emergency_stop(motor)` | 通常停止 / 緊急停止 |
| `get_status(motor)` / `get_status_all()` | ステータス取得 |
| `set_speed(motor, ...)` / `get_speed(motor)` | 速度設定・取得（引数詳細は自動API参照） |
| `get_limit(motor, ...)` / `set_limit(motor, ...)` | ソフトリミット操作（引数詳細は自動API参照） |

`bool` の戻り値は成功・失敗、読み取り系は失敗時に `None` を返す場合があります。設定・操作によっては入力不正で例外が発生します。

## 移動操作のシグネチャ

```python
move(target: int, motor: Optional[int] = None, backlash: Union[str, bool, None] = True, relative: bool = False) -> bool
move_relative(target: int, motor: Optional[int] = None, backlash: Union[str, bool, None] = True) -> bool
```

## 実装由来の値の制約

`PM2CDDevice` は位置 `-8388608`～`8388607`、速度 `5`～`100000` pps、バックラッシュ `-9999`～`9999`、ホールド時間 `50`～`3000` ms を定義しています。個別APIの入力制約はソース実装を優先してください。


> 実機での移動前に配線、リミットスイッチ、移動方向、可動範囲を確認してください。以下のコードは実機では実行していません。
