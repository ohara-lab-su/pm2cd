# 基本概念

[English](../../en/manual/concepts.html) | [日本語](../../ja/manual/concepts.html)

## レイヤーと責務

- `Communication`: TCPソケット、CR+LFフレーミング、排他制御。装置コマンドの意味は解釈しません。
- `PM2CDDevice`: コマンド生成、応答解析、装置固有の入力検証。
- `PM2CDsingle`: 単一プロセス向け公開インターフェース。モーター選択と移動完了判定を提供します。
- `PM2CD`: `ProcessExecutor` によるマルチプロセス公開インターフェース。共有 `Communication` と `SharedContext` を利用します。

## 重要な区別

`motor` は省略時に用いるチャンネル番号です。`move(..., relative=False)` は絶対位置、`relative=True` は相対移動です。`wait_for_complete()` は直近の移動条件を参照し、バックラッシュ補正中の一時停止と最終停止を区別します。

マルチプロセス版はワーカー数だけTCP接続を作る設計ではありません。通信を共有して直列化します。


> 実機での移動前に配線、リミットスイッチ、移動方向、可動範囲を確認してください。以下のコードは実機では実行していません。
