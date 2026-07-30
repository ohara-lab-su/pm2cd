# コボッタ制御
view on [github](https://github.com/ohara-lab-su/cobotta2/) / [ohara-lab-su (doc)](https://ohara-lab-su.github.io/)

---
```{toctree}
:maxdepth: 2
:caption: Contents:

api/modules
tutorials/index
function/index
camera/index
joypad/index
tips/index
history/index
```
---

## コボッタ制御クラス構成(v0.10.3)

基本的に cobotta 制御は下記の４つのクラスから作られる。

### 基本制御クラス

基本となるクラスは4つある。
このクラスを用いて、二つの I/F クラスが作られる

- cobotta_bcap.py: b-CAP を使った cobotta 制御クラス(low-level)
- cobotta_orin2.py: ORiN2 を使った cobotta 制御クラス
- cobotta_ctrl.py: cobotta 制御の I/F クラス
- cobotta_ctrl_joypad.py: cobotta_bcap を使った Joypad 制御+cobotta制御

#### b-CAP を用いる制御

b-CAP による直接制御によりコボッタを制御する class とその　I/F class
```text
制御class: cobotta_bcap.py
↓
I/Fclass: cobotta_ctrl_joypad.py
```

#### ORiN2 を用いる制御

ORiN2 による直接制御によりコボッタを制御する class とその　I/F class
```text
制御class: cobotta_orin2.py
↓
I/Fclass: cobotta_ctrl.py
```

cobotta_orin2 と cobotta_b-cab は基本的な使い方においてはほぼ置換可能なレベル
で作られている。ただし、ORiN2 は windows の COM で作られているために、
オブジェクトのインスタンスを別スレッドで動かすことができない。

そたのめに、gRPC のようなフレームワークに乗せる場合は、フレームワーク内で、
一つのスレッドに COM オブジェクトを張り付かせて、一種のサーバーループにより
エンドポイントとしてのハンドラを動かす必要がある。

かなりめんどくさい。

##### ORiN2 を使う上での注意事項

ORiN2 は Windows の
COM (Component Object Model) で与えられるために注意が必要となる。
COM はライブラリの共有などで、
動的であれ静的であれ、
いわゆるリンク（コンパイル時の静的な型結合）を前提としない形である。

COM は実体としては DLL をロードし、
ABI（バイナリレベルインターフェース）に基づいて、
オブジェクト上の関数を呼び出す仕組みである。

オブジェクトは Windows 上のメモリ空間に存在し、
プロセス内呼び出し、
あるいはプロセス間呼び出しとしてアクセスされる。
(**COM の呼び出しをネットワーク越しに拡張した仕組みは DCOM という。**)

問題は、ORiN2 を使うときの注意として、必ず ORiN2 の手続きに従って
オブジェクトを閉じてからプログラムを終了しないと、COM の参照が残り、
結果としてオブジェクトが解放されずメモリ上に残る点である。

**たとえば、Take Arm したままになる問題がある**

これは非常に厄介で、Windows 上で Win32（C++ など）
で明示的に管理している場合に比べ、
Python などから COM を使う場合に特に発生しやすい。

これは、COM の参照カウント（AddRef / Release）による寿命管理と、
Python のガーベジコレクションおよび win32com の動的バインディング
との間にズレがあるためである。

すなわち、COM 設計と Python バインディングの組み合わせで生じやすい問題であり、
デンソーウェーブが Python 向けに安全なラッパーなどを提供いないため、
実運用上は安定定期に動作せず。問題として顕在化しやすい。

このため、Python から ORiN2 を使用する場合は、
オブジェクトの解放を意識した実装を行わないと、
さまざまな問題が発生する可能性がある。

デンソーウェーブにおいて、python が公式には非対応である理由だ。
つまり不完全なのです。

つまり、COM は python 利用ではかなりの注意が必要で、
問題が起こりやすく。原理的に python として不可能な使い方が多数存在する。
この制御クラスでは、無理やり、python にしているために、
潜在的には不安定なままである。

### pad:　joypad を使うためのクラスライブラリ

```text
├── pad
│  ├── input_grpc_client.py
│  ├── input_grpc_server.py
│  ├── input_joypad_local.py
│  ├── joypad_core.py
│  ├── joypad_mover.py
│  └── joypad_runtime.py
```

### server_fastapi: [ese774](https://ohara-lab-su.github.io/ese774_frame/) を使った通信Frame

server_fastapi 以下は ese774 を使った通信構築するためのもの。
制御class ごとに作り直す必要がある。

#### サーバーのI/F定義

```text
├── server_fastapi
│   ├── clients/
│   ├── models/
│   ├── routers/
│   ├── spec_ctrl.py
│   └── spec_state.py
```

- clients/: クライアントクラス集
- models/: I/F 定義クラス (pydantic のモデル)集
- routers/: サーバー定義
- spec_ctrl.py: I/F定義ファイル spec 
 
#### サーバー起動スクリプト

```text
│    ├── joypad_grpc_server.py
│    └── orin2_grpc_server.py
```

#### クライアント

```text
│   ├── clients
│   │   ├── async_cobotta_client.py
│   │   ├── async_cobotta_state_client.py
│   │   ├── sync_cobotta_client.py
```

### server_grpc: [grpc_frame](https://ohara-lab-su.github.io/grpc_frame/) を使った通信Frame

server_grpc 以下は gRPC を使った通信構築するためのもの。

```text
├── server_grpc
│    ├── bcap_grpc_async_client.py
│    ├── joypad_grpc_client.py
│    ├── orin2_grpc_client.py
```

#### クライアント

```text
├── server_grpc
│    ├── bcap_grpc_async_client.py
│    ├── joypad_grpc_client.py
│    ├── orin2_grpc_client.py
```

#### pyi 作成スクリプト
一般的な動的なディスパッチにしていると、
元のmethodなどの定義をクライアント側に呼べないことがおおい。
エディタで補完ができなくなるために、
スタブ(pyi) を事前に構築していく。
そのためのスクリプト

```text
│    ├── make_bcap_pyi.py
│    ├── make_joypad_pyi.py
│    ├── make_orin2_pyi.py
```

ese774 フレームを用いたサーバー起動と、
ese774 クライアントフレームを継承した、
クライアントクラスの生成。

## 制御サンプル/test

制御クラスの実装時のテストに用いている制御サンプル/test。
ほぼ全ての機能をテストでき、使い方を生部ことができる

[github](https://github.com/ohara-lab-su/cobotta2/tree/main/tests)

- direct: ミニマムな制御テスト
- fastapi: ese774 を用いたテスト
- grpc: grpc を用いたテスト
- local: 通信を使わず cobottaCtrl を用いたテスト


---
## 作者
- Kengo NAKADA
