-- How each weapon is used, per side, from its votes in the side's two content
-- groups, hard and normal (v_roll_unit):
--   players          its copies, active_players those used within setting's
--                    window_days
--   hard_copies,     its copies in each group (a copy used in both counts in
--   normal_copies    each)
--   hard_n_eff,      each group's effective sample size, Kish's (Σw)² / Σw²
--   normal_n_eff
--   hard_weight      hard content's part of the weapon's scores, merged as
--                    v_roll_score merges a column: setting's hard_weight times
--                    the group's credibility, against the rest times normal's
--   hard             1 when that part is at least half: its scores are mostly
--                    hard content's
--   last_seen        when a copy was last used; stale is 1 when that is before
--                    the window: no carnage entries in window_days, a score
--                    kept by the rescue
--   weapon_rank      its place on the side by popularity: hard_weight times its
--                    share of the side's active hard-content votes, plus the
--                    rest times its share of the active normal votes; then the
--                    same over all votes
CREATE VIEW v_weapon_score AS
WITH policy AS (
    SELECT strftime('%Y-%m-%dT%H:%M:%SZ', 'now',
                    '-' || (SELECT value FROM setting WHERE key = 'window_days') || ' days')
               AS cutoff,
           (SELECT value FROM setting WHERE key = 'hard_weight') AS hard_weight,
           (SELECT value FROM setting WHERE key = 'credibility_k') AS k
),
unit AS (
    SELECT u.*, u.last_seen >= p.cutoff AS active
    FROM v_roll_unit u, policy p
),
grp AS (
    SELECT side, weapon, tier, COUNT(*) AS copies, SUM(weight) AS votes,
           SUM(weight * active) AS active_votes,
           1.0 * SUM(weight) * SUM(weight) / SUM(weight * weight) AS n_eff
    FROM unit
    GROUP BY side, weapon, tier
),
part AS (
    SELECT g.*,
           CASE g.tier WHEN 'hard' THEN p.hard_weight ELSE 1 - p.hard_weight END AS tier_weight,
           g.n_eff / (g.n_eff + p.k) AS credibility,
           1.0 * g.votes / SUM(g.votes) OVER (PARTITION BY g.side, g.tier) AS vote_share,
           1.0 * g.active_votes
               / NULLIF(SUM(g.active_votes) OVER (PARTITION BY g.side, g.tier), 0)
               AS active_share
    FROM grp g, policy p
),
weapon AS (
    SELECT side, weapon,
           MAX(CASE WHEN tier = 'hard' THEN copies END) AS hard_copies,
           MAX(CASE WHEN tier = 'normal' THEN copies END) AS normal_copies,
           MAX(CASE WHEN tier = 'hard' THEN n_eff END) AS hard_n_eff,
           MAX(CASE WHEN tier = 'normal' THEN n_eff END) AS normal_n_eff,
           SUM(CASE WHEN tier = 'hard' THEN tier_weight * credibility ELSE 0 END)
               / SUM(tier_weight * credibility) AS hard_part,
           SUM(tier_weight * COALESCE(active_share, 0)) AS active_popularity,
           SUM(tier_weight * vote_share) AS popularity
    FROM part
    GROUP BY side, weapon
),
copies AS (
    SELECT side, weapon, COUNT(DISTINCT itemInstanceId) AS players,
           COUNT(DISTINCT CASE WHEN active THEN itemInstanceId END) AS active_players,
           MAX(last_seen) AS last_seen
    FROM unit
    GROUP BY side, weapon
)
SELECT c.side, c.weapon, c.players, c.active_players,
       COALESCE(w.hard_copies, 0) AS hard_copies, COALESCE(w.normal_copies, 0) AS normal_copies,
       ROUND(COALESCE(w.hard_n_eff, 0), 1) AS hard_n_eff,
       ROUND(COALESCE(w.normal_n_eff, 0), 1) AS normal_n_eff,
       ROUND(w.hard_part, 3) AS hard_weight, w.hard_part >= 0.5 AS hard,
       c.last_seen, c.last_seen < p.cutoff AS stale,
       RANK() OVER (PARTITION BY c.side ORDER BY w.active_popularity DESC, w.popularity DESC)
           AS weapon_rank
FROM copies c
JOIN weapon w USING (side, weapon)
CROSS JOIN policy p;
