-- The weapon each version is scored as, worked out by extract/versions.py at
-- each manifest ingest and replaced with the manifest. A family (the name
-- without " (Adept)", " (Timelost)" or " (Harrowed)") is one weapon unless two
-- or more of its versions roll different trait pools; then each pool is a
-- weapon of its own, named "<family> (<label>)". The rule lives in versions.py:
-- a change to it must also bump the rule number in this table's weapon
-- comment, which rebuilds the database and so re-ingests the manifest (a
-- comment above CREATE isn't stored, so editing it changes nothing).
CREATE TABLE weapon_version (
    -- The version: a weapon definition's hash.
    item_hash  INTEGER PRIMARY KEY,
    -- The weapon it is scored as (grouping rule 1): its family's name, or the
    -- name with its pool's label when its family's versions roll different
    -- trait pools.
    weapon     TEXT NOT NULL
);
