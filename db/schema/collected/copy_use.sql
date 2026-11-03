-- Each weapon copy's uses by category, folded from the PGCRs the scans keep
-- (extract/votes.py): the copy, the category it was used in, its player and
-- version, and when it was last used there. The roll scores' votes are built
-- from these rows (v_roll_unit), so they outlive the raw PGCR rows, which are
-- pruned after setting's raw_days. extract/votes.py purges them to a rolling
-- window, each weapon keeping its newest copies up to setting's rescue_copies.
-- Kept when the schema changes, with what the scans collected.
CREATE TABLE copy_use (
    -- The copy: DestinyHistoricalWeaponStats.itemInstanceId.
    itemInstanceId  TEXT NOT NULL,
    -- The activity_category key of the PGCRs it was used in.
    category        TEXT NOT NULL,
    -- Its player, as their PGCR entries name them.
    membershipId    TEXT NOT NULL,
    -- The copy's weapon definition: its version.
    item_hash       INTEGER NOT NULL,
    -- The newest of those PGCRs' periods (ISO 8601, UTC).
    last_seen       TEXT NOT NULL,
    -- 1 when every one of those uses was a clear its player didn't make from
    -- the start, in a category with checkpoints (v_weapon_use's checkpoint),
    -- which weighs its vote less (v_roll_unit); 0 otherwise, as for rows
    -- folded before it was kept.
    checkpoint      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (itemInstanceId, category)
);
