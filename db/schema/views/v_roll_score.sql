-- How players roll each weapon, per side: one row per perk in each of its
-- columns, merging the side's two content groups, hard and normal
-- (v_group_score). A group's part of a column is setting's hard_weight (hard)
-- or the rest (normal), times its credibility there, the parts then scaled to
-- add up to 1; a group without votes in the column has none. Two well-measured
-- groups so split a score about hard_weight to the rest, while a thin group
-- counts for little, whichever it is:
--   share         the groups' shares, each times its part
--   hard_share,   the perk's share in each group (0 where the group's column
--   normal_share  lacks it; NULL where the group has no votes in the column)
--   hard_part     hard content's part of the column; normal's is the rest
--   hard_n_eff,   each group's effective sample size in the column, and its
--   ..._credibility  credibility (NULL without votes)
--   n_eff         the merged score's effective sample size,
--                 1 / Σ (part² / the group's n_eff)
--   low, high     share's 95% Wilson score interval, with n_eff as its n
--   credibility   n_eff / (n_eff + credibility_k)
--   confidence    n_eff graded: high from 100, medium from 30, low from 10,
--                 very low below
--   rank          the perk's place in its column by share
--   socket        the column's first socket in either group, so a column's
--                 perks sort together where versions place it apart
-- ponytail: n_eff treats the groups as independent, but a copy used in both
-- votes in each, so the range is a little narrow; counting a copy in its
-- hardest group only would make them independent.
-- The weapon's own numbers come from v_weapon_score: weapon_rank, its players,
-- hard_weight and hard and stale flags.
CREATE VIEW v_roll_score AS
WITH grp AS MATERIALIZED (
    SELECT * FROM v_group_score
),
policy AS (
    SELECT (SELECT value FROM setting WHERE key = 'hard_weight') AS hard_weight,
           (SELECT value FROM setting WHERE key = 'credibility_k') AS k
),
col AS (
    SELECT DISTINCT g.side, g.weapon, g.kind, g.tier, g.n_eff,
           CASE g.tier WHEN 'hard' THEN p.hard_weight ELSE 1 - p.hard_weight END
               * g.credibility AS part
    FROM grp g, policy p
),
part AS (
    SELECT side, weapon, kind, tier, n_eff,
           part / SUM(part) OVER (PARTITION BY side, weapon, kind) AS part
    FROM col
),
merged AS (
    SELECT side, weapon, kind, 1.0 / SUM(part * part / n_eff) AS n_eff,
           SUM(CASE WHEN tier = 'hard' THEN part ELSE 0 END) AS hard_part,
           MAX(CASE WHEN tier = 'hard' THEN n_eff END) AS hard_n_eff,
           MAX(CASE WHEN tier = 'normal' THEN n_eff END) AS normal_n_eff
    FROM part
    GROUP BY side, weapon, kind
),
perk AS (
    SELECT g.side, g.weapon, g.kind, MIN(g.socket) AS socket, g.perk,
           SUM(p.part * g.share) AS share,
           MAX(CASE WHEN g.tier = 'hard' THEN g.share END) AS hard_share,
           MAX(CASE WHEN g.tier = 'normal' THEN g.share END) AS normal_share
    FROM grp g
    JOIN part p USING (side, weapon, kind, tier)
    GROUP BY g.side, g.weapon, g.kind, g.perk
)
SELECT p.side, w.weapon_rank, p.weapon, w.players AS weapon_players, w.hard_weight, w.hard,
       w.stale, p.kind, MIN(p.socket) OVER (PARTITION BY p.side, p.weapon, p.kind) AS socket,
       RANK() OVER (PARTITION BY p.side, p.weapon, p.kind ORDER BY p.share DESC) AS rank,
       p.perk, ROUND(p.share, 3) AS share,
       -- z = 1.96: z²/2 = 1.9208, z²/4 = 0.9604, z² = 3.8416
       ROUND((p.share + 1.9208 / m.n_eff
              - 1.96 * sqrt(p.share * (1 - p.share) / m.n_eff + 0.9604 / (m.n_eff * m.n_eff)))
             / (1 + 3.8416 / m.n_eff), 3) AS low,
       ROUND((p.share + 1.9208 / m.n_eff
              + 1.96 * sqrt(p.share * (1 - p.share) / m.n_eff + 0.9604 / (m.n_eff * m.n_eff)))
             / (1 + 3.8416 / m.n_eff), 3) AS high,
       ROUND(m.n_eff, 1) AS n_eff, ROUND(m.n_eff / (m.n_eff + k.k), 2) AS credibility,
       CASE WHEN m.n_eff >= 100 THEN 'high' WHEN m.n_eff >= 30 THEN 'medium'
            WHEN m.n_eff >= 10 THEN 'low' ELSE 'very low' END AS confidence,
       ROUND(m.hard_part, 3) AS hard_part,
       ROUND(CASE WHEN m.hard_n_eff IS NOT NULL THEN COALESCE(p.hard_share, 0) END, 3)
           AS hard_share,
       ROUND(CASE WHEN m.normal_n_eff IS NOT NULL THEN COALESCE(p.normal_share, 0) END, 3)
           AS normal_share,
       ROUND(m.hard_n_eff, 1) AS hard_n_eff,
       ROUND(m.hard_n_eff / (m.hard_n_eff + k.k), 2) AS hard_credibility,
       ROUND(m.normal_n_eff, 1) AS normal_n_eff,
       ROUND(m.normal_n_eff / (m.normal_n_eff + k.k), 2) AS normal_credibility
FROM perk p
JOIN merged m USING (side, weapon, kind)
JOIN v_weapon_score w ON w.side = p.side AND w.weapon = p.weapon
CROSS JOIN policy k;
