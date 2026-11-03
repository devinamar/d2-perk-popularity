-- The activity categories the scans keep, and what a vote from each counts for
-- in its side's roll scores (pve or pvp): the weight doubles at each step up
-- in difficulty. hard is 1 for the high-end categories, which make each side's
-- hard group (the rest its normal group): the scans keep every one
-- (extract/scan.py), and the scores lean toward that group (setting's
-- hard_weight; v_roll_score, v_weapon_score). checkpoints is 1 for raids and
-- dungeons, which can be run from a checkpoint: their clears made from the
-- start count more (setting's full_clear_weight; v_weapon_use, v_roll_unit).
-- v_pgcr_category holds the rules that sort a PGCR into one. Kept by hand; the
-- rows are part of the view, so a change here rebuilds the database on the
-- next run (keeping what the scans collected).
CREATE VIEW activity_category (key, label, side, weight, hard, checkpoints) AS VALUES
    ('raid_master', 'Master raid', 'pve', 32, 1, 1),
    ('gm', 'Grandmaster Vanguard Alert', 'pve', 16, 1, 0),
    ('dungeon_master', 'Master dungeon', 'pve', 8, 1, 1),
    ('raid', 'Raid', 'pve', 4, 0, 1),
    ('dungeon', 'Dungeon', 'pve', 2, 0, 1),
    ('portal', 'Strikes and Portal', 'pve', 1, 0, 0),
    ('trials', 'Trials of Osiris', 'pvp', 8, 1, 0),
    ('competitive', 'Competitive', 'pvp', 4, 1, 0),
    ('quickplay', 'Regular playlist', 'pvp', 2, 0, 0),
    ('gambit', 'Gambit', 'pvp', 1, 0, 0);
