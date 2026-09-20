-- Migration 0004: full applications flow (answers, claim, ticket refs, messages)
ALTER TABLE applications ADD COLUMN answers TEXT;
ALTER TABLE applications ADD COLUMN claimed_by TEXT;
ALTER TABLE applications ADD COLUMN decided_by TEXT;
ALTER TABLE applications ADD COLUMN thread_id TEXT;
ALTER TABLE applications ADD COLUMN log_channel_id TEXT;
ALTER TABLE applications ADD COLUMN log_message_id TEXT;

CREATE TABLE IF NOT EXISTS application_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    author_discord_id TEXT NOT NULL,
    content TEXT NOT NULL,
    from_site INTEGER NOT NULL DEFAULT 0,
    delivered_to_discord INTEGER NOT NULL DEFAULT 0,
    delivered_to_site INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_app_messages_app ON application_messages(application_id, created_at);
CREATE INDEX IF NOT EXISTS idx_app_messages_outbox ON application_messages(delivered_to_discord) WHERE delivered_to_discord = 0;
