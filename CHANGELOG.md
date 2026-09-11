# CHANGELOG

## v0.0.1 — 2026-09-11

v0.0.0 からの変更点。

### Added

#### `PM2CD.version`

`get_version()` を呼び出す property として `version` を追加した。

```python
version = ctrl.version
```

`get_version()` 自体は既存のまま残している。

#### rate 値 I/F

rate number を直接指定する既存 I/F

- `get_rate_number(motor)`
- `set_rate_number(motor, number)`

はそのまま維持し、rate 値を直接扱う I/F を追加した。

- `get_rate(motor)`
- `set_rate(motor, rate)`

`get_rate()` は、装置から取得した rate number を既存の `number_to_rate()` で rate 値へ変換して返す。

`set_rate()` は、指定された rate に最も近い設定可能 rate の number を選択し、既存の `set_rate_number()` で設定する。

その最近傍 rate number を求める Ctrl 内部 helper として、非公開メソッド

- `_nearest_rate_number(rate)`

を追加した。

既存の

- `number_to_rate(index)`
- `rate_to_number(rate)`

は変更していない。

### Changed

- `main()` 内の version 取得を `ctrl.version()` から property の `ctrl.version` へ変更した。
- Black によるコードフォーマットを適用した。

### Device

`pm2cd_device.py` は v0.0.0 から変更していない。

## v0.0.0 — 2026-09-11

この版はリリース履歴というより、PM2CD / PM2C-06A Python 制御コードを今後継続して設計・修正するための
「現時点の構造・責務・C版との対応・API理解」を固定する基準文書である。

### 1. 対象と前提

対象は PM2CD / PM2C-06A。PM16C-16 の仕様を PM2CD の装置仕様として流用しない。
ただし、既存 C 版 `dev_pm16c16_*` の実ハンドラー群は、
Python 版 Device 層の実装粒度・処理順序・責務を理解するための先行実装として参照する。

C版について今回確認したのは、
公開 I/F の全体ではなく、
Device ハンドラー内部で実際にコマンド生成、送受信、応答変換を行う処理実体である。
確認済みの範囲には rotate/check_rotate、number/rate 変換、
emergency stop、backlash、display、hold、limit、pause、pulse、rate、speed、speed mode、
status/status_all、SETLS、TTL、version、home、ALLREP、remote、stop、CRLF送受信などが含まれる。

Python 版では C 版の各 `.c` ファイルを機械的に一対一で再現するのではなく、
C 版に存在する実ハンドラーの意味を維持しつつ、通信・データ解析・Device・公開 Ctrl I/F の責務を分離する。

### 2. 全体アーキテクチャ

基本データフローは次の通り。

```text
PM2CD (ctrl: 公開 I/F)
        ↓ 意味ベースの引数・戻り値
PM2CDDevice (device: 装置実ハンドラー)
        ↓ command / raw response
Communication (通信)
        ↕ TCP + CRLF
PM2C-06A

受信 raw response
        ↓
core data class / parser
        ↓ 意味を持つ Python 値
Device
        ↓
Ctrl
```

責務の原則は以下。

- `Communication`: TCP 接続と文字列送受信だけを担当する。PM2CD のコマンド意味を持たない。
- `core`: 装置固有の複合応答を解析し、ビット位置や固定文字列形式を意味のある属性へ変換する。
- `PM2CDDevice`: C版 Device 実ハンドラーに相当する。装置コマンドを知り、コマンド生成、送受信、必要な複数コマンドの連続処理、core
  parser の呼び出しを担当する。
- `PM2CD` (`ctrl`): ユーザー向け公開 I/F。装置の raw 文字列・bit mask・nibble を原則として外へ出さず、`bool`、`int`
  、意味順序を定義した `List[bool]` 等へ変換して返す。

Ctrl は単なる Device への機械的委譲層ではない。
装置内部表現を公開 API から消し、
Python 利用者が装置プロトコルのビット配置を知らなくても操作できる意味 I/F を作る役割を持つ。

### 3. Communication 層

現行 `Communication` は C 版の `dev_pm16c16_send_crlf()` / `dev_pm16c16_send_crlf_receive()`
に対応する共通通信責務を Python 側へ分離したものと理解する。

- `send(command)` はコマンドへ CRLF を付けて送信する。
- `query(command)` は send と receive を同一 lock 範囲で完結させ、要求と応答の対応を保つ。
- `_receive()` は CRLF まで受信し decode する。
- timeout / socket error 時は接続状態を整理する。
- PM2CD 固有の `FL`、`SETLS`、`STS?` 等の意味解釈は行わない。

リミット対応を理由に Communication の責務を増やさない。

### 4. core 層

core は「複合的な装置応答フォーマットの意味解釈」を担当する。
単一整数を返す `FL?` / `BL?` 等まで無条件にクラス化する必要はない。

現在確認している core クラスは次の通り。

- `ControllerStatus`: コントローラ状態応答の解析。
- `MotorStatus`: `STS?` の軸状態解析。
- `HomeStatus`: home 関係の複合状態解析。
- `MotorSetting`: motor setting 応答解析。
- `StopMode`: stop mode の意味表現。
- `LimitSwitchSetting`: `SETLS?x` の設定値 `DYYY0yyy` の解析。
- `LimitStatus`: `HDSTLS?` の hardware/software limit 現在状態の分離解析。

#### 4.1 LimitSwitchSetting

`SETLS?x` は「現在リミットに当たっているか」ではなく、リミット機能の設定である。この区別は必須。

`DYYY0yyy` を保持し、公開する意味属性は以下。

```text
digital_limit_enabled : software/digital limit enable
hp_enabled            : HP hardware LS enable
ccw_enabled           : CCW hardware LS enable
cw_enabled            : CW hardware LS enable
hp_nc                  : HP contact is normally closed
ccw_nc                 : CCW contact is normally closed
cw_nc                  : CW contact is normally closed
```

`digital_limit_enabled` は `@property`。以前 method として定義され Device が property として参照していた不整合を修正した。

read-modify-write 用に以下を持つ。

```python
with_digital_limit(enabled: bool) -> Optional[str]
with_hardware_limit(enabled: bool) -> Optional[str]
with_hardware_limit_normally_closed(
    side: str,
normally_closed: bool,
) -> Optional[str]
```

PM2C-06A では CW/CCW hardware LS の enable / contact specification が連動する仕様を考慮し、
CW/CCW を同じ値へ更新する。
HP は独立して保持・更新する。

#### 4.2 LimitStatus

`LimitStatus` は設定ではなく現在状態を表す。
`HDSTLS?` の `abcdHHHHSSSS` を解析し、軸ごとに hardware/software limit を分離する。

意味属性は以下。

```text
hard_cw
hard_ccw
hard_hp
soft_cw
soft_ccw
```

Ctrl へ渡しやすい意味リストも持つ。

```python
hard -> [CW, CCW, HP]
soft -> [CW, CCW]
```

raw nibble / bit mask は Ctrl の公開 API へ露出させない。

#### 4.3 MotorStatus と limit の関係

`MotorStatus` は `STS?` の通常運転状態を解析する。
`STS?` の LS nibble は CW/CCW/HP/HOLD OFF を含むが、
hardware/software limit を明示的に分離する情報として扱わない。

既存 `legacy_status_bits` は旧 C API の互換的表現を再構成する処理であり、
hardware/software limit の真の分離状態として使用しない。
hardware/software の分離が必要な公開 I/F は `HDSTLS?` → `LimitStatus` を使用する。

### 5. Device 層

Device は C 版実ハンドラーの責務を維持する。Device を単純な `send()` / `query()` の薄い wrapper に崩さない。

C版では各実ハンドラーがコマンド生成、送受信、必要なら複数コマンド、
戻り値変換を担当していた。Python 版では raw 応答解析の一部を core へ分離するが、
操作として一体である複数コマンド処理は Device に残す。

代表的対応は次の通り。

```text
C版実ハンドラー                  Python Device
------------------------------------------------------------
get/put pulse                    position / set_position
get/put speed                    speed / set_speed
get/put speed mode               speed_mode / set_speed_mode
get/put rate                     rate_number / set_rate_number
get/put backlash                 backlash / set_backlash
get/put limit                    limit / set_limit
get status / status_all          status / status_all
get/put HLD                      hold / set_hold
home                             home
stop / stop_all                  stop / stop_all
emstop / emstop_all              emergency_stop / emergency_stop_all
check_rotate / rotate            check_rotate / move 系
number/rate conversion           number_to_rate / rate_to_number
send_crlf(_receive)              Communication.send/query
```

完全な一対一対応を意味するものではない。
Python 側では同じ装置操作をより自然な Python API へ整理している。

#### 5.1 software limit position

Device API:

```python
limit(motor: int, side: str) -> Optional[int]
set_limit(motor: int, side: str, pulse: int) -> bool
```

対応コマンド:

```text
CW  : FL?x / FLx±ddddddd
CCW : BL?x / BLx±ddddddd
```

無修飾の `limit` は software limit を意味する。
hardware limit に `limit` だけの名前を与えない。

`set_limit()` は単純な `FL` / `BL` send ではない。C版 `put_limit` と同じ意味の複合実ハンドラーである。

```text
SETLS?x
  ↓
LimitSwitchSetting
  ↓ software/digital limit が無効なら D=1 に更新
SETLSx...
  ↓
FLx±pulse または BLx±pulse
```

したがって「software limit position を設定する操作」が必要な前提設定まで Device 内で保証する。

符号付き位置コマンドは `+d` を使用し、正値も `+` を明示する。

#### 5.2 limit setting

Device API:

```python
limit_switch_setting(motor: int) -> Optional[LimitSwitchSetting]
limit_switch_setting_raw(motor: int) -> Optional[str]
set_limit_switch_setting_raw(motor: int, setting: str) -> bool
set_digital_limit_enabled(motor: int, enabled: bool) -> bool
set_hard_limit_enabled(motor: int, enabled: bool) -> bool
set_hard_limit_normally_closed(
    motor: int,
side: str,
normally_closed: bool,
) -> bool
```

`limit_switch_setting_raw` / `set_limit_switch_setting_raw` は
Device 内部の装置ハンドラーとして存在してよいが、Ctrl の公開 API には raw `DYYY0yyy` を露出させない。

意味変更は `SETLS?` → `LimitSwitchSetting` → `with_*()` → `SETLS` の read-modify-write とし、
対象外の設定ビットを保持する。

#### 5.3 limit current status

Device API:

```python
limit_status(motor: int) -> Optional[LimitStatus]
limit_status_all() -> Optional[List[LimitStatus]]
```

`limit_status_all()` は `HDSTLS?` を query し、`LimitStatus.parse_all()` へ渡す。`limit_status(motor)` はその軸を選択する。

ここでは `SETLS?` を現在状態取得に使わない。

### 6. Ctrl 層

Ctrl はユーザー向け API。Device/core の raw 表現を意味値へ変換する。

設計原則:

- raw command string を要求しない。
- raw response string を返さない。
- bit mask / nibble を返さない。
- boolean の意味が複数ある場合は API 名で意味を明示する。
- 複数の limit 入力状態は順序を定義した Python `List[bool]` で返す。
- 無修飾 `limit` は software limit。
- hardware limit は `hard_` を明示する。
- 公開名に意味不明瞭な略語（例: `NC`）を使わず、`normally_closed` のように意味を表す。

#### 6.1 Ctrl limit API

```python
get_limit(motor: int, side: str) -> Optional[int]
set_limit(motor: int, side: str, pulse: int) -> bool
```

software limit position の取得・設定。

```python
get_limit_status(motor: int) -> Optional[List[bool]]
```

戻り値:

```text
[CW, CCW]
```

software limit の現在状態。

```python
get_limit_status_all() -> Optional[List[List[bool]]]
```

全軸の software limit 状態。

```python
get_hard_limit_status(motor: int) -> Optional[List[bool]]
```

戻り値:

```text
[CW, CCW, HP]
```

hardware limit の現在状態。

```python
get_hard_limit_status_all() -> Optional[List[List[bool]]]
```

全軸の hardware limit 状態。

```python
get_limit_enabled(motor: int) -> Optional[bool]
set_limit_enabled(motor: int, enabled: bool) -> bool
```

software/digital limit enable の取得・設定。

```python
get_hard_limit_enabled(motor: int) -> Optional[List[bool]]
```

戻り値:

```text
[CW, CCW, HP]
```

hardware LS enable 設定を意味値として返す。

```python
set_hard_limit_enabled(motor: int, enabled: bool) -> bool
```

PM2C-06A の CW/CCW hardware limit enable を設定する。現 Device 実装では PM2C-06A の連動仕様に従い CW/CCW を同時更新し、HP
設定を保持する。

```python
get_hard_limit_normally_closed(motor: int) -> Optional[List[bool]]
```

戻り値:

```text
[CW, CCW, HP]
```

`True` は normally closed、`False` は normally open。

```python
set_hard_limit_normally_closed(
    motor: int,
side: str,
normally_closed: bool,
) -> bool
```

`side` は `hp` / `cw` / `ccw`。PM2C-06A の仕様に従い CW/CCW は同時更新する。

```python
get_limit_switch_setting(motor: int) -> Optional[List[bool]]
```

現修正版に存在する意味 I/F。raw `DYYY0yyy` は返さない。ただし、`get_limit_enabled()`、`get_hard_limit_enabled()`、
`get_hard_limit_normally_closed()` と情報が重複するため、公開 API として残すかは未確定。今後 API 全体を精査する対象。

### 7. 現行 Ctrl 公開 API 一覧

以下は修正版 `PM2CD` クラスで確認している公開メソッド一覧。

#### 接続・モード

```text
is_connected
connect
disconnect
close
remote
local
```

#### バージョン・コントローラ状態

```text
get_version
get_hardware_version
get_controller_status
```

#### 移動・走査・停止

```text
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
wait_stop
```

`AESTP` は emergency stop。通常初期化・通常停止用途には使用しない。

#### motor status

```text
get_status
get_status_all
```

#### position

```text
get_position
set_position
zero_position
```

#### speed

```text
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
```

#### rate

```text
get_rate_number
set_rate_number
number_to_rate
rate_to_number
```

#### backlash

```text
get_backlash
set_backlash
```

#### limit

```text
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

#### pause

```text
pause
resume
get_pause_status
```

#### hold

```text
get_hold
set_hold
get_hold_on_time
set_hold_on_time
get_hold_off_time
set_hold_off_time
```

#### home setting/status

```text
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

#### motor / stop setting

```text
get_motor_setting
set_motor_setting
get_stop_mode
set_stop_mode
```

#### context manager

```text
__enter__
__exit__
```

### 8. 現行 Device API 一覧

Device は公開ユーザー API ではなく実ハンドラー層。確認しているメソッドは以下。

#### 基本・状態

```text
remote
local
version
hardware_version
controller_status
status
status_all
check_rotate
```

#### motion

```text
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
```

#### position/speed/rate/backlash

```text
position
set_position
speed
set_speed
speed_profile
set_speed_profile
high_speed
set_high_speed
middle_speed
set_middle_speed
low_speed
set_low_speed
speed_mode
set_speed_mode
rate_number
set_rate_number
backlash
set_backlash
```

#### limit

```text
limit
set_limit
limit_status
limit_status_all
set_digital_limit_enabled
set_hard_limit_enabled
set_hard_limit_normally_closed
limit_switch_setting
limit_switch_setting_raw
set_limit_switch_setting_raw
```

#### pause/hold

```text
pause
resume
pause_status
hold
set_hold
hold_on_time
set_hold_on_time
hold_off_time
set_hold_off_time
```

#### home/preset/jog setting

```text
home_status
set_home_status
home_position
set_home_position
home_offset
set_home_offset
preset_position
set_preset_position
jog_pulse
set_jog_pulse
```

#### motor/stop setting

```text
motor_setting
set_motor_setting
stop_mode
set_stop_mode
```

#### conversion/helper

```text
number_to_rate
rate_to_number
_send_motor_command
_set_speed_value
_set_hold_time
_query_motor_int
_query_motor_msec
_query_msec
_query_int
_parse_int
_query_text
_query_on_off
_motor_text
_check_motor
_check_position
_check_speed
_check_int
_normalize_direction
_normalize_side
_normalize_speed_mode
_backlash_suffix
_direction_digit
_bool_digit
```

underscore helper は Device 内部実装用であり Ctrl API へ公開しない。

### 9. C版から維持する設計思想

今回の C ファイル群から重要なのはコマンド名のコピーではなく、Device 実ハンドラーの粒度である。

1. 1つの意味ある装置操作を1ハンドラーとして扱う。
2. その操作に複数コマンドが必要なら、Device ハンドラー内で連続処理する。
3. 通信そのものは共通化する。
4. 受信後の装置固有データ解釈は、Python では必要に応じ core クラスへ分離する。
5. Ctrl は装置内部表現をそのまま公開しない。

特に `set_limit()` はこの方針を確認する代表例であり、`SETLS?` と `FL/BL` を別々のユーザー操作へ分解して終わりにしてはいけない。software
limit position 設定として必要な前提を Device が満たす。

### 10. 現時点で確定している limit の意味区分

```text
software limit position
    FL? / FL
    BL? / BL

limit function setting
    SETLS?
    software limit enable
    hardware LS enable
    hardware LS contact specification

current limit state
    HDSTLS?
    hardware/software を分離して取得

normal motor/controller status
    STS?
    MotorStatus
```

`SETLS?` を current limit state と解釈しない。

### 11. v0.0.0 での修正内容

- `LimitSwitchSetting.digital_limit_enabled` を property として統一。
- `LimitSwitchSetting` に hardware limit enable/contact の read-modify-write 処理を追加。
- `HDSTLS?` 用 `LimitStatus` core parser を追加。
- Device に `limit_status()` / `limit_status_all()` を追加。
- Device に software/hardware limit setting の意味操作を追加。
- `set_limit()` の C版由来の software limit 自動 enable 処理を維持。
- limit position の符号付きコマンド生成を `+d` として正値の `+` も明示。
- Ctrl では raw SETLS API を公開せず、limit 状態・enable・contact specification を `bool` / `List[bool]` の意味 I/F
  として公開。
- software limit は無修飾 `limit`、hardware limit は `hard_` を明示する命名方針を維持。

