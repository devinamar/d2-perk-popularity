-- The data policy, kept by hand: what counts as current, what is kept, and how
-- a side's two content groups, hard and normal, merge into its scores.
--   window_days    a copy is active while it was used in the last this many
--                  days; its older uses are purged unless rescued
--   rescue_copies  each weapon (per side) keeps its newest copies up to this
--                  many, however old: a weapon that drops out of use keeps its
--                  last known scores, and a rarely used one collects every
--                  copy seen, up to this many
--   raw_days       raw PGCR rows (headers, entries, weapons) are kept this long
--   full_clear_weight  a full clear's part against a checkpoint clear's in
--                  raids and dungeons (activity_category's checkpoints): a
--                  copy used there only in clears its player didn't make from
--                  the start votes (1 - this) / this of its category's weight,
--                  a third at 0.75
--   late_join_seconds  a player who joined a run more than this many seconds
--                  in didn't clear it from the start: a fireteam there from
--                  the start loads in within about 5 seconds, a late joiner
--                  half a minute or more after
--   hard_weight    hard content's part of a side's scores when both groups
--                  are well measured; normal content has the rest
--   credibility_k  a group's credibility is n_eff / (n_eff + this), 0.5 at
--                  this many effective votes; a group's part shrinks with it,
--                  so a thin sample can't carry hard content's weight
-- extract/votes.py purges by it; v_weapon_score and v_roll_score merge by it.
-- Like activity_category, a change here rebuilds the database on the next run
-- (keeping what the scans collected).
CREATE VIEW setting (key, value) AS VALUES
    ('window_days', 30),
    ('rescue_copies', 100),
    ('raw_days', 14),
    ('full_clear_weight', 0.75),
    ('late_join_seconds', 30),
    ('hard_weight', 0.75),
    ('credibility_k', 30);
