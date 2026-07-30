# pm2cd

TCP/IP専用のPM2CD制御パッケージです。

## 構成

- `src/pm2cd/core/communication_tcp.py`: TCP通信層
- `src/pm2cd/pm2cd_device.py`: 装置コマンド・応答解析層
- `src/pm2cd/pm2cd_ctrl.py`: 利用者向けI/F層
- `src/pm2cd/server_fastapi/`: ese774_frame用通信レイヤー

`core`は他機種パッケージと共有せず、このパッケージ内に保持します。
