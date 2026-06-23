# Meccha Chameleon Wiki

《Meccha Chameleon（塗鴉躲貓貓）》主題維基百科 — 半自動化共筆平台。

## 快速啟動

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定資料庫

建立 PostgreSQL 資料庫並執行綱要：

```bash
createdb meccha_wiki
psql -d meccha_wiki -f src/db/schema.sql
```

設定環境變數（或直接編輯 `config/settings.py`）：

```bash
set WIKI_DB_HOST=localhost
set WIKI_DB_NAME=meccha_wiki
set WIKI_DB_USER=wiki_admin
set WIKI_DB_PASSWORD=your_password
```

### 3. 啟動 Web 伺服器

```bash
python run_web.py
```

開啟瀏覽器前往 http://127.0.0.1:5000

### 4. 執行爬蟲（可選）

```bash
python run_scraper.py
```

### 5. 啟動定時排程（可選）

```bash
python scheduler.py
```

## 專案結構

```
WIKI/
├── config/settings.py           # 設定檔
├── run_web.py                   # Web 伺服器入口
├── run_scraper.py               # 爬蟲執行腳本
├── scheduler.py                 # 定時排程
├── wsgi.py                      # 生產部署用
│
├── src/
│   ├── db/
│   │   ├── schema.sql           # PostgreSQL 完整綱要
│   │   └── connection.py        # 資料庫連線池 + CRUD
│   ├── scraper/
│   │   ├── steam.py             # Steam 爬蟲
│   │   └── image.py             # 圖片下載 + WebP 轉換
│   ├── parser/
│   │   └── wikitext.py          # Wiki 標記 → HTML 解析器
│   └── web/
│       ├── app.py               # Flask 應用（路由、認證）
│       ├── static/
│       │   ├── css/wiki.css     # 維基淺色主題
│       │   └── js/wiki.js       # 前端互動功能
│       └── templates/
│           ├── base.html        # 頁面基底
│           ├── page.html        # 條目頁面
│           ├── map.html         # 地圖條目
│           ├── item.html        # 道具條目
│           ├── edit.html        # 編輯器
│           ├── history.html     # 版本歷史
│           ├── login.html       # 登入頁
│           ├── talk.html        # 討論頁
│           ├── disambig.html    # 消歧義頁面
│           └── banners/         # 維護模板通告
│
├── content/                     # Wiki 條目原始檔（Markdown）
│   ├── Guide/
│   ├── Map/
│   ├── Item/
│   └── Workshop/
│
└── assets/                      # 爬蟲下載素材
```

## 路由一覽

| 路由 | 功能 |
|------|------|
| `/` | 首頁 |
| `/<Namespace>:<Title>` | 檢視條目 |
| `/edit/<Namespace>:<Title>` | 編輯條目（需登入） |
| `/history/<Namespace>:<Title>` | 版本歷史 |
| `/rollback/<path>/<rev_id>` | 回滾（管理員限定） |
| `/talk/<Namespace>:<Title>` | 討論頁 |
| `/login` | 登入/註冊 |
| `/logout` | 登出 |

## 授權

- 官方素材：基於合理使用（Fair Use）原則
- 社群原創內容：CC BY-SA 4.0
