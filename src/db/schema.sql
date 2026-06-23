BEGIN;

-- ============================================================
-- Meccha Chameleon Wiki — PostgreSQL Database Schema
-- ============================================================

-- 用戶表
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(64) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(255),
    role            VARCHAR(16) NOT NULL DEFAULT 'editor'
                        CHECK (role IN ('admin', 'editor', 'viewer')),
    edit_count      INTEGER NOT NULL DEFAULT 0,
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 自動確認用戶視圖（註冊滿 7 天且編輯過 20 次以上）
CREATE VIEW autoconfirmed_users AS
SELECT id, username FROM users
WHERE edit_count >= 20
  AND registered_at <= NOW() - INTERVAL '7 days';

-- 命名空間列舉
CREATE TYPE namespace AS ENUM (
    'Guide', 'Map', 'Item', 'Workshop'
);

-- 頁面主表
CREATE TABLE IF NOT EXISTS pages (
    id              SERIAL PRIMARY KEY,
    namespace       namespace NOT NULL,
    title           VARCHAR(255) NOT NULL,
    slug            VARCHAR(255) NOT NULL,
    is_protected    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (namespace, slug)
);

-- 頁面內容版本（修訂歷史）
CREATE TABLE IF NOT EXISTS revisions (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    editor_id       INTEGER NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    summary         VARCHAR(500),
    is_rollback     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_revisions_page_id ON revisions(page_id);

-- 地圖資料
CREATE TABLE IF NOT EXISTS map_data (
    page_id         INTEGER PRIMARY KEY REFERENCES pages(id) ON DELETE CASCADE,
    area_sqm        REAL,
    key_landmarks   TEXT[],
    environment_colors JSONB
);

-- 道具資料
CREATE TABLE IF NOT EXISTS item_data (
    page_id         INTEGER PRIMARY KEY REFERENCES pages(id) ON DELETE CASCADE,
    item_type       VARCHAR(64),
    cooldown_sec    REAL,
    coverage_pct    REAL,
    unlock_condition TEXT
);

-- 皮膚資料
CREATE TABLE IF NOT EXISTS skins (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    page_id         INTEGER REFERENCES pages(id) ON DELETE SET NULL,
    unlock_condition TEXT,
    rarity          VARCHAR(32),
    image_url       TEXT
);

-- Steam 工作坊條目
CREATE TABLE IF NOT EXISTS workshop_entries (
    id              SERIAL PRIMARY KEY,
    workshop_id     BIGINT NOT NULL UNIQUE,
    title           VARCHAR(255) NOT NULL,
    creator_name    VARCHAR(128),
    rating          REAL CHECK (rating >= 0 AND rating <= 5),
    tags            TEXT[],
    preview_url     TEXT,
    page_id         INTEGER REFERENCES pages(id) ON DELETE SET NULL,
    last_synced_at  TIMESTAMPTZ
);

-- 爬蟲抓取紀錄（避免重複）
CREATE TABLE IF NOT EXISTS scrape_log (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(64) NOT NULL,
    checksum        VARCHAR(64),
    payload         JSONB,
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 頁面分類關聯
CREATE TABLE IF NOT EXISTS page_categories (
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    category        VARCHAR(128) NOT NULL,
    PRIMARY KEY (page_id, category)
);

-- ============================================================
-- 第六章：文獻引用、模板、消歧義
-- ============================================================

-- 文獻引用表（腳註）
CREATE TABLE IF NOT EXISTS footnotes (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    ref_index       INTEGER NOT NULL,
    source_type     VARCHAR(16) NOT NULL DEFAULT 'secondary'
                        CHECK (source_type IN ('primary', 'secondary')),
    source_label    VARCHAR(32) NOT NULL DEFAULT 'secondary'
                        CHECK (source_label IN (
                            'steam_official', 'datamine', 'media_review',
                            'community_data', 'other'
                        )),
    content         TEXT NOT NULL,
    url             TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (page_id, ref_index)
);

-- 討論頁
CREATE TABLE IF NOT EXISTS talk_pages (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL UNIQUE REFERENCES pages(id) ON DELETE CASCADE,
    is_locked       BOOLEAN NOT NULL DEFAULT FALSE,
    lock_reason     TEXT,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 討論串
CREATE TABLE IF NOT EXISTS talk_threads (
    id              SERIAL PRIMARY KEY,
    talk_page_id    INTEGER NOT NULL REFERENCES talk_pages(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    author_id       INTEGER NOT NULL REFERENCES users(id),
    is_resolved     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 討論回覆
CREATE TABLE IF NOT EXISTS talk_replies (
    id              SERIAL PRIMARY KEY,
    thread_id       INTEGER NOT NULL REFERENCES talk_threads(id) ON DELETE CASCADE,
    author_id       INTEGER NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 條目評級
CREATE TYPE article_grade AS ENUM (
    'FA', 'GA', 'B', 'C', 'Start', 'Stub'
);

CREATE TABLE IF NOT EXISTS article_grades (
    page_id         INTEGER PRIMARY KEY REFERENCES pages(id) ON DELETE CASCADE,
    grade           article_grade NOT NULL DEFAULT 'Start',
    graded_by       INTEGER REFERENCES users(id),
    graded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 第七章：編輯戰保護與頁面保護日誌
-- ============================================================

-- 頁面保護層級
CREATE TYPE protection_level AS ENUM (
    'none', 'semi', 'full', 'admin'
);

-- 保護紀錄
CREATE TABLE IF NOT EXISTS page_protection_log (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    level           protection_level NOT NULL DEFAULT 'none',
    reason          TEXT,
    duration_hours  INTEGER,
    applied_by      INTEGER NOT NULL REFERENCES users(id),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 目前生效中之頁面保護（輔助視圖）
CREATE VIEW active_page_protections AS
SELECT DISTINCT ON (page_id)
    ppl.page_id,
    ppl.level,
    ppl.reason,
    ppl.expires_at
FROM page_protection_log ppl
WHERE ppl.expires_at IS NULL OR ppl.expires_at > NOW()
ORDER BY ppl.page_id, ppl.created_at DESC;

-- 編輯戰警示（同一頁面短時間內被回滾超過 3 次）
CREATE TABLE IF NOT EXISTS edit_war_warnings (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    triggered_by    INTEGER NOT NULL REFERENCES users(id),
    rollback_count  INTEGER NOT NULL DEFAULT 1,
    window_start    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_escalated    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 既有視圖
-- ============================================================

-- 自動產生雙向連結（Wikilinks）的輔助視圖
CREATE VIEW wikilinks AS
SELECT
    p1.id AS source_page_id,
    p1.title AS source_title,
    p2.id AS target_page_id,
    p2.title AS target_title,
    p2.namespace AS target_namespace
FROM revisions r
JOIN pages p1 ON r.page_id = p1.id
JOIN LATERAL (
    SELECT DISTINCT ON (p2.id) p2.id, p2.title, p2.namespace
    FROM pages p2
    WHERE r.body LIKE '%[[' || p2.title || ']]%'
) p2 ON TRUE;

COMMIT;
