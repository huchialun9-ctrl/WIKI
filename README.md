# Meccha Chameleon Wiki

《Meccha Chameleon（塗鴉躲貓貓）》主題維基百科 — 社群共筆平台。

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

### 4. 執行資料擷取（可選）

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
├── run_scraper.py               # 資料擷取腳本
├── scheduler.py                 # 定時排程
├── wsgi.py                      # 生產部署用
│
├── src/
│   ├── db/
│   │   ├── schema.sql           # PostgreSQL 綱要（13 張表 + 視圖）
│   │   └── connection.py        # 資料庫連線池 + CRUD
│   ├── scraper/
│   │   ├── steam.py             # Steam 頁面資料擷取
│   │   └── image.py             # 圖片下載 + WebP 轉換
│   ├── parser/
│   │   └── wikitext.py          # Wiki 標記 → HTML 解析器
│   ├── security/
│   │   ├── abuse_filter.py      # 濫用過濾器（外部連結限制、清空防護）
│   │   ├── captcha.py           # 人機驗證
│   │   └── throttle.py          # API 請求限流
│   └── web/
│       ├── app.py               # Flask 應用（路由、認證、安全）
│       ├── static/
│       │   ├── css/wiki.css     # 維基淺色主題
│       │   └── js/wiki.js       # 前端互動功能
│       └── templates/
│           ├── base.html        # 頁面基底
│           ├── page.html        # 條目頁面
│           ├── map.html         # 地圖條目（含色碼表）
│           ├── item.html        # 道具條目
│           ├── edit.html        # 編輯器（含驗證碼）
│           ├── history.html     # 版本歷史
│           ├── login.html       # 登入
│           ├── talk.html        # 討論頁
│           ├── disambig.html    # 消歧義頁面
│           └── banners/         # 五種維護模板通告
│
├── content/                     # 條目原始檔（Markdown）
│   ├── Guide/                   # 指南命名空間
│   ├── Map/                     # 地圖命名空間
│   ├── Item/                    # 道具與外觀命名空間
│   ├── Workshop/                # 工作坊命名空間
│   ├── Talk/                    # 討論頁
│   ├── WikiProject/             # 維基專題
│   └── Osaka（消歧義）.md       # 消歧義頁面範例
│
├── render.yaml                  # Render.com 部署設定
├── Procfile                     # Gunicorn 啟動命令
├── runtime.txt                  # Python 版本
├── init_db.py                   # 資料庫初始化腳本
└── .env.example                 # 環境變數範本
```

## 部署 Render.com

1. Fork 此 repo 到你的 GitHub
2. 前往 https://dashboard.render.com 按 **New +** → **Blueprint**
3. 連接 repo，Render 會自動讀取 `render.yaml`
4. 部署完成後，網站會在 `https://meccha-chameleon-wiki.onrender.com` 上線

## 路由一覽

| 路由 | 功能 | 權限 |
|------|------|------|
| `/` | 首頁 | 公開 |
| `/health` | 健康檢查 | 公開 |
| `/<Namespace>:<Title>` | 檢視條目 | 公開 |
| `/edit/<Namespace>:<Title>` | 編輯條目 | 需登入 |
| `/history/<Namespace>:<Title>` | 版本歷史 | 公開 |
| `/rollback/<path>/<rev_id>` | 回滾 | 管理員限定 |
| `/talk/<Namespace>:<Title>` | 討論頁 | 公開 |
| `/login` | 登入 | 公開 |
| `/logout` | 登出 | 已登入 |
| `/api/article-count` | 條目統計 | 公開 |

## 維護模板

| 模板 | 用途 |
|------|------|
| `{{Stub}}` | 內容過少，需要補充 |
| `{{Outdated}}` | 數據可能已過時 |
| `{{Unreferenced}}` | 缺乏來源引用 |
| `{{Spoiler}}` | 隱藏要素透露（可折疊） |
| `{{Merged}}` | 請求合併至其他條目 |

## 授權

- 官方素材：基於合理使用（Fair Use）原則
- 社群原創內容：CC BY-SA 4.0
