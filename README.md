# pm2cd

PM2CD / PM2C-06A を Python から制御するためのパッケージです。

本パッケージは、既存の C版/MADOCA Device handler
の実装思想と装置操作の意味を参照しながら、 Python
では通信、装置固有処理、データ解析、利用者向け制御、multi-process 実行、
FastAPI 通信を分離して構成しています。

現在のバージョンは **v0.1.0** です。

この README は、単なるインストールメモではなく、PM2CD Python 版の
総合マニュアル・設計仕様・チュートリアルとして記述しています。

------------------------------------------------------------------------

## 1. 対象

対象装置は PM2CD / PM2C-06A です。

PM16C-16 と PM2CD / PM2C-06A は同一装置ではありません。 PM16C-16
の仕様をそのまま PM2CD の装置仕様として流用しません。

一方、既存の C版 `dev_pm16c16_*` Device handler 群には、 PM2CD Python
版を設計する上で重要な先行実装があります。

Python 版では、それら C ファイルを機械的に一対一移植するのではなく、

- 一つの意味ある装置操作を一つの Device handler として扱う
- 一つの操作に複数コマンドが必要なら Device 層で完結させる
- 通信そのものは共通通信層へ分離する
- raw response の複合解析は core parser へ分離する
- Ctrl は raw bit / nibble / command string を利用者へ露出しない

という設計思想を引き継いでいます。

------------------------------------------------------------------------

## 2. C版/MADOCA と Python 版の関係

### 2.1 C版の位置づけ

既存 C版は MADOCA 環境の Device handler として実装されてきたコードです。

今回 Python 版の基準として参照しているのは、MADOCA 全体のネットワーク
API を Python へ移植することではなく、Device handler
内部で実際に行われている

- command 生成
- send / receive
- 複数 command の処理順序
- response の変換
- 装置操作としての handler の粒度

です。

確認してきた C版 handler には、rotate/check_rotate、number/rate 変換、
emergency stop、backlash、display、hold、limit、pause、pulse、rate、
speed、speed mode、status/status_all、SETLS、TTL、version、home、
ALLREP、remote、stop、CRLF 送受信などがあります。

### 2.2 Python 版は C版の一対一翻訳ではない

Python 版では C版の責務を次のように再配置しています。

``` text
C版/MADOCA
    Device handler
        |
        | 装置操作の意味・処理順序を参照
        v
Python
    PM2CDDevice
        + core parser
        + Communication
        + PM2CDsingle
        + PM2CD
```

例えば C版の一つの handler が、

1. 設定値を問い合わせる
2. 必要な bit を変更する
3. 設定 command を送る
4. 本来の操作 command を送る

という処理を行う場合、Python 版でも「一つの意味ある装置操作」として
`PM2CDDevice` 内で完結させます。

`set_limit()` はその代表例です。

``` text
SETLS?x
   |
   v
LimitSwitchSetting
   |
   +-- software limit が無効なら enable
   |
   v
SETLSx...
   |
   v
FLx... / BLx...
```

利用者に `SETLS?` と `FL/BL` を別々に操作させる設計にはしません。

### 2.3 MADOCA と Python server は別レイヤー

C版で使用されてきた MADOCA と、Python 版で使用する FastAPI /
`ese774_frame` は同じ通信 framework ではありません。

Python 版 PM2CD は DeviceClass として単独でも利用でき、 必要な場合に
FastAPI server/client を上に載せます。

したがって Python 版の設計では、

``` text
装置制御ロジック
        !=
ネットワーク framework
```

を明確に分離しています。

------------------------------------------------------------------------

## 3. Python 版の全体構成

v0.1.0 の基本構造は次の通りです。

``` text
利用プログラム
    |
    +-- local
    |      |
    |      +--> PM2CDsingle
    |      |
    |      `--> PM2CD
    |
    `-- network
           |
           +--> SyncPM2CDClient / AsyncPM2CDClient
           |
           v
       FastAPI / ese774_frame
           |
           v
         PM2CD
           |
           v
     ProcessExecutor
           |
           +--> PM2CDsingle worker 1
           +--> PM2CDsingle worker 2
           +--> ...
                    |
                    v
                PM2CDDevice
                    |
                    v
          shared Communication proxy
                    |
                    v
             Communication x 1
                    |
                    v
             TCP + CRLF
                    |
                    v
             PM2CD / PM2C-06A
```

受信データについては、

``` text
raw response
    |
    v
core parser
    |
    v
frozen dataclass / Python value
    |
    v
PM2CDDevice
    |
    v
PM2CDsingle
    |
    v
PM2CD / client
```

という流れになります。

------------------------------------------------------------------------

## 4. 各層の責務

### 4.1 `Communication`

TCP 接続と文字列送受信だけを担当します。

主な責務は、

- TCP connect / disconnect
- command への CRLF 付加
- send
- receive
- query
- timeout / socket error 処理
- receive buffer 管理

です。

PM2CD 固有の `STS?`、`SETLS?`、`FL?` などの意味は知りません。

`query()` は send と receive を同一 lock 範囲で処理し、
要求と応答の対応を維持します。

### 4.2 `core`

装置の複合 response を意味のある Python データへ変換します。

現在の主要データ型は frozen dataclass として扱います。

- `MotorStatus`
- `ControllerStatus`
- `HomeStatus`
- `LimitStatus`
- `MotorSetting`
- `LimitSwitchSetting`
- `StopMode`

データ保持と parsing は分離します。

``` text
raw response
    |
    v
parse_xxx()
    |
    v
@dataclass(frozen=True)
```

解析不能な response について、不正な状態 object を無理に生成せず、 取得
API の失敗として `None` を返す設計を基本とします。

### 4.3 `PM2CDDevice`

装置固有の実 handler 層です。

ここが C版 Device handler に最も近い責務を持ちます。

- command 名を知る
- command を組み立てる
- 入力値を検証する
- `Communication` を使用して send/query する
- 必要な複数 command を一つの操作として実行する
- core parser を呼ぶ
- 装置固有 response を Python 値へ変換する

Device を単純な `send()` / `query()` wrapper にはしません。

### 4.4 `PM2CDsingle`

単一 process で動作する高水準の制御クラスです。

主な責務は、

- 利用者向け API
- default `motor`
- 移動コンテキスト
- `wait_for_complete()`
- backlash を含む位置決め完了判定
- Device API を意味ベースの公開 API へ整理

です。

`PM2CDsingle` は `Communication` の外部 injection に対応しています。

``` python
ctrl = PM2CDsingle(
    ip_address=IP_ADDRESS,
    communication=communication,
)
```

この dependency injection point は test 用だけではなく、 v0.1.0 の
multi-process 構成で一つの物理 Communication を 複数 worker
から使用するためにも利用します。

### 4.5 `PM2CD`

v0.1.0 では、利用者向け `PM2CD` は `ProcessExecutor` を使用する
multi-process facade です。

公開 API の意味は `PM2CDsingle` と揃え、 実際の handler 実行を worker
process へ dispatch します。

``` text
PM2CD.method(...)
    |
    v
ProcessExecutor.submit(...)
    |
    v
PM2CDsingle.method(...)
    |
    v
ProcessExecutor.wait(...)
    |
    v
return value
```

このため利用者から見る API は同期的ですが、 内部では handler が worker
process で実行されます。

------------------------------------------------------------------------

## 5. `PM2CDsingle` と `PM2CD` の使い分け

### 5.1 `PM2CDsingle`

一つの Python process 内で直接装置を制御する場合に使用します。

``` python
from pm2cd.pm2cd_single import PM2CDsingle

ctrl = PM2CDsingle(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
)

try:
    ctrl.remote()
    position = ctrl.get_position(0)
    print(position)
finally:
    ctrl.close()
```

構造は単純です。

``` text
application
    |
    v
PM2CDsingle
    |
    v
PM2CDDevice
    |
    v
Communication
    |
    v
PM2CD
```

### 5.2 `PM2CD`

worker process を使用する通常の multi-process 構成です。

``` python
from pm2cd.pm2cd_ctrl import PM2CD

ctrl = PM2CD(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
    worker_count=2,
)

try:
    ctrl.remote()
    position = ctrl.get_position(0)
    print(position)
finally:
    ctrl.close()
```

`worker_count` は `ProcessExecutor` の worker process 数です。

------------------------------------------------------------------------

## 6. なぜ複数 worker でも Communication は一つなのか

### 6.1 誤った構成

worker ごとに `PM2CDsingle` を通常生成すると、 各 worker が自分の
`Communication` を作ります。

``` text
worker 1 -> Communication 1 --+
worker 2 -> Communication 2 --+--> same PM2CD
worker 3 -> Communication 3 --+
```

各 `Communication` の lock は別 process / 別 instance なので、
装置全体の通信順序を保証しません。

### 6.2 v0.1.0 の構成

v0.1.0 では `BaseManager` が一つの `Communication` を所有し、 各 worker
には proxy を渡します。

``` text
worker 1 --+
worker 2 --+--> Communication proxy --> Communication x 1 --> PM2CD
worker N --+
```

したがって、

``` text
worker process      N
PM2CDsingle         N
Communication       1
TCP connection      1
```

となります。

これは `ProcessExecutor` が PM2CD
の通信を自動的に共有しているのではありません。

**物理 resource の ownership は PM2CD 側の設計です。**

------------------------------------------------------------------------

## 7. `ProcessExecutor` との関係

`ProcessExecutor` は PM2CD 専用 framework ではありません。

PM2CD 側が利用している主な機能は、

- worker process の生成
- `worker_factory(context)`
- handler dispatch
- `submit()`
- `wait()`
- `SharedContext`
- manager-backed shared state
- process-safe lock

です。

概念上の責務は次のように分離します。

``` text
ProcessExecutor
    |
    +-- process を管理する
    +-- job を dispatch する
    +-- shared context を提供する
    |
    `-- PM2CD protocol は知らない

PM2CD
    |
    +-- PM2CDsingle を worker として構成する
    +-- Communication を一つだけ所有する
    +-- controller state を SharedContext へ置く
    |
    `-- PM2CD 固有の resource ownership を決める
```

### 7.1 `worker_factory(context)`

PM2CD は `worker_factory(context)` を使用して各 worker の `PM2CDsingle`
を生成します。

その際、

- 共通 `Communication` proxy
- `SharedContext.state`

を worker に接続します。

### 7.2 shared state

worker が複数あると、通常の instance variable は worker ごとに別です。

PM2CD では少なくとも、

- default `motor`
- 移動コンテキスト

は worker をまたいで意味を維持する必要があります。

そのため `SharedContext.state` を使用します。

------------------------------------------------------------------------

## 8. 移動コンテキストと `wait_for_complete()`

`move()` / `move_relative()` は、単に command を送るだけではありません。

位置決め完了判定のため、モーターごとに直前の移動条件を保持します。

主な内容は、

- target position
- backlash 指定
- backlash enabled
- backlash value

です。

### 8.1 backlash なし

基本的な完了判定は、

``` text
move
  |
  v
active
  |
  v
target position + inactive
  |
  v
complete
```

です。

ただし短い移動では polling 間で active
状態を観測できない場合があるため、 active
を観測したこと自体を必須条件にはしません。

### 8.2 backlash あり

backlash 補正では概念的に、

``` text
target
  |
  v
backlash point
  |
  v
target
```

という追加動作が入ります。

そのため最初に target position で inactive になっただけでは、
補正完了と即断できません。

`wait_for_complete()` は直前の移動コンテキストを参照して、 最終 target
への復帰までを判定します。

短い backlash 動作では active/inactive 遷移が polling
間で縮退する場合も考慮します。

### 8.3 multi-process での共有

`move()` を worker 1、`wait_for_complete()` を worker 2
が処理する可能性があります。

そのため v0.1.0 の `PM2CD` では移動コンテキストを `SharedContext.state`
へ置きます。

``` text
worker 1: move()
       |
       v
SharedContext.state
       |
       v
worker 2: wait_for_complete()
```

これにより worker scheduling に依存せず同じ制御意味を維持します。

------------------------------------------------------------------------

## 9. `motor` property

`PM2CDsingle` / `PM2CD` は default motor を `motor` property
で保持します。

``` python
ctrl.motor = 0
position = ctrl.get_position()
```

各 API で motor を明示した場合は、その値を優先します。

``` python
position = ctrl.get_position(1)
```

multi-process `PM2CD` では default motor も shared state として扱い、
worker ごとに異なる default motor にならないようにします。

------------------------------------------------------------------------

## 10. FastAPI / `ese774_frame`

PM2CD は `ese774_frame` の完全自動ディスパッチを使用します。

基本設定は、

``` text
FastApiServer
api_spec=None
object_name="pm2cd"
```

です。

個別の Pydantic model や `ApiSpec` を PM2CD 側で列挙せず、
公開メソッドとアノテーションを利用して API を構成します。

### 10.1 dataclass の転送

PM2CD は状態取得 API で frozen dataclass を返します。

例:

- `MotorStatus`
- `ControllerStatus`
- `HomeStatus`
- `LimitStatus`
- `MotorSetting`
- `LimitSwitchSetting`
- `StopMode`

これらを完全自動ディスパッチで JSON 化し、 client
側で元の型へ復元するため、 **`ese774_frame v0.6.0` 以上を使用します。**

### 10.2 client

同期 client と非同期 client を使用できます。

``` text
SyncPM2CDClient
AsyncPM2CDClient
```

client は `object_name="pm2cd"` で server と対応します。

------------------------------------------------------------------------

## 11. server の起動

### 11.1 module 側

v0.1.0 の server module は worker 数を受け取れます。

``` python
from pm2cd.server import run

run(
    worker_count=2,
)
```

内部では、

``` text
run(worker_count)
    |
    v
create_server(worker_count)
    |
    v
FastApiServer(device_kwargs)
    |
    v
PM2CD(worker_count=worker_count)
```

と渡されます。

server process の数と、PM2CD 内部の `ProcessExecutor.worker_count` は
別の概念です。

### 11.2 example server

実際の起動 example は worker 数をコード側で設定します。

``` python
from pm2cd.server import run

WORKER_COUNT = 2


def main() -> None:
    run(
        worker_count=WORKER_COUNT,
    )


if __name__ == "__main__":
    main()
```

worker 数のための CLI option は使用しません。

------------------------------------------------------------------------

## 12. 基本チュートリアル

以下では `PM2CD` を使用します。

### 12.1 接続と終了

``` python
from pm2cd.pm2cd_ctrl import PM2CD

ctrl = PM2CD(
    ip_address="10.170.10.62",
    port=7777,
    timeout_sec=3.0,
    worker_count=2,
)

try:
    print(ctrl.is_connected())
finally:
    ctrl.close()
```

### 12.2 REMOTE へ切り替える

``` python
ctrl.remote()
```

LOCAL へ戻す場合は、

``` python
ctrl.local()
```

です。

### 12.3 状態を取得する

``` python
status = ctrl.get_status(0)

if status is not None:
    print(status.position)
    print(status.is_busy)
```

全軸:

``` python
statuses = ctrl.get_status_all()
```

### 12.4 現在位置を取得する

``` python
position = ctrl.get_position(0)
print(position)
```

default motor を使用する場合:

``` python
ctrl.motor = 0
position = ctrl.get_position()
```

### 12.5 絶対位置移動

``` python
ctrl.move(
    0,
    1000,
    backlash=False,
)

status = ctrl.wait_for_complete(
    0,
    timeout_sec=30.0,
)
```

### 12.6 backlash 付き位置決め

``` python
ctrl.move(
    0,
    1000,
    backlash=True,
)

status = ctrl.wait_for_complete(
    0,
    timeout_sec=30.0,
)
```

`PM2CD` では移動コンテキストが worker 間で共有されるため、 `move()` と
`wait_for_complete()` が別 worker で実行されても backlash
条件を引き継ぎます。

### 12.7 相対移動

``` python
ctrl.move_relative(
    0,
    100,
    backlash=True,
)

ctrl.wait_for_complete(
    0,
    timeout_sec=30.0,
)
```

### 12.8 通常停止と非常停止

通常停止:

``` python
ctrl.stop(0)
ctrl.stop_all()
```

非常停止:

``` python
ctrl.emergency_stop(0)
ctrl.emergency_stop_all()
```

通常停止と非常停止は別 API として扱います。

------------------------------------------------------------------------

## 13. 速度・rate・backlash

### 13.1 speed

``` python
speed = ctrl.get_speed(0)
ctrl.set_speed(0, 1000)
```

LOW / MIDDLE / HIGH をまとめて扱う API:

``` python
profile = ctrl.get_speed_profile(0)
```

個別 API:

``` text
get_high_speed / set_high_speed
get_middle_speed / set_middle_speed
get_low_speed / set_low_speed
```

### 13.2 rate

rate number:

``` python
number = ctrl.get_rate_number(0)
ctrl.set_rate_number(0, number)
```

rate 値:

``` python
rate = ctrl.get_rate(0)
ctrl.set_rate(0, rate)
```

変換 API:

``` python
rate = ctrl.number_to_rate(number)
number = ctrl.rate_to_number(rate)
```

### 13.3 backlash

``` python
backlash = ctrl.get_backlash(0)
ctrl.set_backlash(0, backlash)
```

------------------------------------------------------------------------

## 14. limit

PM2CD Python API では、無修飾の `limit` は software limit を意味します。

hardware limit は `hard_` を明示します。

### 14.1 software limit position

``` python
cw = ctrl.get_limit(0, "cw")
ccw = ctrl.get_limit(0, "ccw")

ctrl.set_limit(0, "cw", 10000)
ctrl.set_limit(0, "ccw", -10000)
```

### 14.2 software limit state

``` python
status = ctrl.get_limit_status(0)
```

意味順序:

``` text
[CW, CCW]
```

### 14.3 hardware limit state

``` python
status = ctrl.get_hard_limit_status(0)
```

意味順序:

``` text
[CW, CCW, HP]
```

### 14.4 enable

software/digital limit:

``` python
enabled = ctrl.get_limit_enabled(0)
ctrl.set_limit_enabled(0, True)
```

hardware limit:

``` python
enabled = ctrl.get_hard_limit_enabled(0)
ctrl.set_hard_limit_enabled(0, True)
```

### 14.5 normally closed / open

``` python
setting = ctrl.get_hard_limit_normally_closed(0)

ctrl.set_hard_limit_normally_closed(
    0,
    "cw",
    True,
)
```

公開 API では raw `DYYY0yyy` を直接扱いません。

------------------------------------------------------------------------

## 15. HOME / HOLD / PAUSE

HOME:

``` text
home
find_home
scan_home
get_home_status
set_home_status
get_home_position
set_home_position
get_home_offset
set_home_offset
```

preset / JOG:

``` text
get_preset_position
set_preset_position
get_jog_pulse
set_jog_pulse
```

HOLD:

``` text
get_hold
set_hold
get_hold_on_time
set_hold_on_time
get_hold_off_time
set_hold_off_time
```

PAUSE:

``` text
pause
resume
get_pause_status
```

------------------------------------------------------------------------

## 16. motor / stop setting

motor setting:

``` text
get_motor_setting
set_motor_setting
```

stop mode:

``` text
get_stop_mode
set_stop_mode
```

取得値は dataclass として扱います。

------------------------------------------------------------------------

## 17. 主な公開 API

### 接続・mode

``` text
motor
is_connected
connect
disconnect
remote
local
close
```

### version / controller

``` text
version
get_version
get_hardware_version
get_controller_status
controller_status
```

### motion

``` text
move
move_relative
scan
constant_speed_scan
jog
scan_home
home
find_home
stop
stop_all
emergency_stop
emergency_stop_all
get_rotate
is_busy
wait_for_complete
```

### status / position

``` text
get_status
get_status_all
status_all
get_position
set_position
zero_position
```

### speed / rate / backlash

``` text
get_speed
set_speed
get_speed_profile
set_speed_profile
get_high_speed
set_high_speed
get_middle_speed
set_middle_speed
get_low_speed
set_low_speed
get_speed_mode
set_speed_mode
get_rate_number
set_rate_number
get_rate
set_rate
number_to_rate
rate_to_number
get_backlash
set_backlash
```

### limit

``` text
get_limit
set_limit
get_limit_status
get_limit_status_all
get_hard_limit_status
get_hard_limit_status_all
get_limit_enabled
set_limit_enabled
get_hard_limit_enabled
set_hard_limit_enabled
get_hard_limit_normally_closed
set_hard_limit_normally_closed
get_limit_switch_setting
```

### pause / hold

``` text
pause
resume
get_pause_status
get_hold
set_hold
get_hold_on_time
set_hold_on_time
get_hold_off_time
set_hold_off_time
```

### HOME / preset / JOG

``` text
get_home_status
set_home_status
get_home_position
set_home_position
get_home_offset
set_home_offset
get_preset_position
set_preset_position
get_jog_pulse
set_jog_pulse
```

### setting

``` text
get_motor_setting
set_motor_setting
get_stop_mode
set_stop_mode
```

------------------------------------------------------------------------

## 18. 戻り値の基本方針

装置制御 API は概ね次の方針です。

``` text
操作成功/失敗    bool
値取得成功       値
値取得失敗       None
```

取得 API は `Optional[...]` のアノテーションを持つものがあります。

状態・設定 object は frozen dataclass として扱い、
取得後に状態を書き換える設計にはしません。

------------------------------------------------------------------------

## 19. エラーと入力検証

入力値は可能な限り `PM2CDDevice` 側で検証し、
不正な値を装置へ送らない構成にします。

通信層の error は通信責務として扱い、 装置 response の解析失敗は parser
/ Device の責務として扱います。

Ctrl は装置 protocol の raw error 表現を利用者 API
の中心には置きません。

------------------------------------------------------------------------

## 20. server/client 利用時の構成

network 越しの利用では次の構成になります。

``` text
client application
      |
      v
SyncPM2CDClient
or AsyncPM2CDClient
      |
      v
HTTP / FastAPI
      |
      v
ese774_frame FastApiServer
      |
      v
PM2CD
      |
      v
ProcessExecutor
      |
      v
PM2CDsingle worker x N
      |
      v
shared Communication
      |
      v
PM2CD
```

`PM2CD` の内部 worker 数を増やしても、 装置への TCP connection
を増やさないことが v0.1.0 の重要な設計条件です。

------------------------------------------------------------------------

## 21. example の考え方

example は段階的に確認できるようにします。

### 21.1 single local

目的:

- framework を介さず PM2CDsingle 自体を確認する
- 装置 protocol / Device / Ctrl の基準動作を確認する

### 21.2 multi local

目的:

- `PM2CD` + `ProcessExecutor` を確認する
- worker process からの実制御を確認する
- worker 数を2以上にしても Communication が一つである構成を確認する

### 21.3 FastAPI server/client

目的:

- `ese774_frame` の完全自動ディスパッチを確認する
- dataclass の server/client 間転送を確認する
- network 越しでも同じ PM2CD 公開 API を使用する

### 21.4 server 起動 example

worker 数は example script の定数で指定します。

``` python
WORKER_COUNT = 2
```

CLI option で worker 数を与える方式にはしません。

------------------------------------------------------------------------

## 22. 推奨する確認順序

装置を使った動作確認は、層を一度に増やさず次の順序で行います。

``` text
1. Communication
       |
2. PM2CDDevice
       |
3. PM2CDsingle local
       |
4. PM2CD multi local
       |
5. FastAPI server
       |
6. Sync/Async client
```

multi-process の問題と network framework
の問題を同時に切り分けないためです。

特に新しい motion API の確認では、一つの method を小さく確認してから
次の層へ進めます。

------------------------------------------------------------------------

## 23. `close()` と resource ownership

multi-process `PM2CD` では `Communication` は全 worker の共有 resource
です。

したがって、一つの worker に `PM2CDsingle.close()`
を実行させてはいけません。

`PM2CD.close()` は、

``` text
ProcessExecutor.close()
        |
        v
shared Communication.close()
        |
        v
CommunicationManager.shutdown()
```

の順で終了します。

物理 resource を作成した owner が最後に一度だけ閉じる、という構成です。

------------------------------------------------------------------------

## 24. 設計上の重要事項

### 24.1 Ctrl と Device を混ぜない

Ctrl に command string を直接書き始めると、 C版で整理されていた Device
handler の責務が崩れます。

装置固有 command は Device に置きます。

### 24.2 Device を薄くしすぎない

一つの意味ある操作に複数 command が必要なら、 その一連の処理は Device
handler に残します。

### 24.3 core dataclass に処理を持たせすぎない

dataclass はデータを表します。

response parsing は parser 関数へ分離します。

### 24.4 ProcessExecutor に装置固有責務を入れない

ProcessExecutor は PM2CD の TCP socket や protocol を知りません。

Communication の共有方法は PM2CD が決めます。

### 24.5 shared は公開 API の概念にしない

worker 間で state を共有していても、 `get_shared_xxx()` のような専用 API
を利用者へ追加しません。

shared state は multi-process 実装の内部事情です。

------------------------------------------------------------------------

## 25. dependency

FastAPI 完全自動ディスパッチを使用する場合:

``` text
ese774_frame >= 0.6.0
```

が必要です。

multi-process `PM2CD` は `ProcessExecutor` の、

``` text
worker_factory
SharedContext
shared_context
submit
wait
```

を使用します。

PM2CD と ProcessExecutor の責務は分離されており、 ProcessExecutor
自体には PM2CD 固有コードを入れません。

------------------------------------------------------------------------

## 26. v0.1.0 の位置づけ

v0.0.x では主に、

- C版 Device handler の意味の整理
- Communication / core / Device / Ctrl の責務分離
- `PM2CDsingle` API の拡張
- backlash を含む `wait_for_complete()`
- frozen dataclass + parser
- FastAPI 完全自動ディスパッチ

を整備しました。

v0.1.0 では、その single-process 制御ロジックを壊さず、 `PM2CD`
を実用的な multi-process facade として成立させました。

中心となる設計は、

``` text
PM2CDsingle worker x N
        +
SharedContext
        +
Communication x 1
        +
TCP connection x 1
```

です。

これにより、単一 process の装置制御クラス、multi-process 制御、 FastAPI
server/client を同じ Device/Ctrl
設計の上に積み上げる構成になっています。
