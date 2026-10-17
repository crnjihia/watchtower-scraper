-- Watchtower Scraper Database Schema

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site VARCHAR(64) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    title VARCHAR(512) NOT NULL,
    company VARCHAR(255),
    location VARCHAR(255),
    category VARCHAR(128),
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT uq_site_external_id UNIQUE (site, external_id)
);

CREATE INDEX IF NOT EXISTS ix_items_site ON items (site);
CREATE INDEX IF NOT EXISTS ix_items_external_id ON items (external_id);
CREATE INDEX IF NOT EXISTS ix_items_last_seen_at ON items (last_seen_at);
CREATE INDEX IF NOT EXISTS ix_items_active ON items (active);
CREATE INDEX IF NOT EXISTS ix_item_site_active ON items (site, active);

CREATE TABLE IF NOT EXISTS item_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    price_kes FLOAT,
    scraped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_item_snapshots_item_id ON item_snapshots (item_id);
CREATE INDEX IF NOT EXISTS ix_item_snapshots_scraped_at ON item_snapshots (scraped_at);

CREATE TABLE IF NOT EXISTS change_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    kind VARCHAR(32) NOT NULL,
    diff JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_change_events_item_id ON change_events (item_id);
CREATE INDEX IF NOT EXISTS ix_change_events_kind ON change_events (kind);
CREATE INDEX IF NOT EXISTS ix_change_events_created_at ON change_events (created_at);
CREATE INDEX IF NOT EXISTS ix_change_events_notified_at ON change_events (notified_at);
CREATE INDEX IF NOT EXISTS ix_change_events_unnotified ON change_events (notified_at, created_at);

CREATE TABLE IF NOT EXISTS spider_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spider VARCHAR(64) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    items_seen INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS ix_spider_runs_spider ON spider_runs (spider);
CREATE INDEX IF NOT EXISTS ix_spider_runs_status ON spider_runs (status);
