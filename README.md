# Meccha Chameleon Wiki

《Meccha Chameleon（塗鴉躲貓貓）》非官方社群維基百科。收錄遊戲機制、地圖色碼、道具數據、工作坊索引，由志工自主維護。

- **指南** — 遊戲機制與戰術
- **地圖** — 官方場景與標準色碼表（HEX/RGB）
- **道具與外觀** — 工具數據、皮膚解鎖條件
- **工作坊** — Steam 社群自訂地圖索引（4★ 以上）
- **維基專題** — 色碼測量、工作坊審查、條目評級

## 部署

```bash
pip install -r requirements.txt
createdb meccha_wiki
psql -d meccha_wiki -f src/db/schema.sql
python run_web.py
```

Render.com 一鍵部署：`render.yaml` 已備妥，連接 repo 即自動上線。

## 授權

官方素材基於合理使用（Fair Use），社群原創內容採用 CC BY-SA 4.0。
