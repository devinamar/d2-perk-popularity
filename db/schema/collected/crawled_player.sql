-- The players whose activity histories a crawl has read, and when, so a crawl
-- reads each history again only after a week (extract/scan.py). Kept when the
-- schema changes, with what the scans collected.
CREATE TABLE crawled_player (
    -- The player's destinyUserInfo.membershipId, as their PGCR entries name it.
    membershipId  TEXT PRIMARY KEY,
    -- When the crawl last read their history (ISO 8601, UTC).
    crawled_at    TEXT NOT NULL
);
