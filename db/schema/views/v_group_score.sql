-- How players roll each weapon in each of a side's two content groups, hard
-- and normal: one row per perk in each of its columns, from the group's votes
-- in v_roll_plug. Barrels, magazines (and the like), stocks, grips and origins
-- each make a column (kind); a copy's traits make one column together (kind
-- 'traits', perk "Trait 1 + Trait 2"), since traits are picked as a pair, and
-- each trait also makes one of its own, for showing and ordering them singly
-- (kind 'trait1', 'trait2', in socket order). Each vote counts its weight in
-- its group (v_roll_unit):
--   votes        the perk's weighted votes; players, its votes unweighted
--   share        votes / the column's weighted votes
--   n_eff        the column's effective sample size, Kish's (Σw)² / Σw²: what
--                its unequal weights are worth as equally weighted votes
--   low, high    share's 95% Wilson score interval, with n_eff as its n
--   credibility  n_eff / (n_eff + setting's credibility_k): how far the group's
--                column is trusted when v_roll_score merges a side's groups
--   confidence   n_eff graded: high from 100, medium from 30, low from 10,
--                very low below
--   socket       the column's first socket, the order the game shows them in
CREATE VIEW v_group_score AS
WITH plug AS MATERIALIZED (
    SELECT * FROM v_roll_plug
),
pick AS (
    SELECT side, tier, weapon, itemInstanceId, weight, kind, socket_idx, perk
    FROM plug
    WHERE kind != 'trait'
    UNION ALL
    SELECT side, tier, weapon, itemInstanceId, weight,
           'trait' || ROW_NUMBER() OVER (PARTITION BY side, tier, itemInstanceId
                                         ORDER BY socket_idx),
           socket_idx, perk
    FROM plug
    WHERE kind = 'trait'
    UNION ALL
    SELECT side, tier, weapon, itemInstanceId, weight, 'traits', MIN(socket_idx),
           group_concat(perk, ' + ' ORDER BY socket_idx)
    FROM plug
    WHERE kind = 'trait'
    GROUP BY side, tier, weapon, itemInstanceId
),
col AS (
    SELECT side, tier, weapon, kind, MIN(socket_idx) AS socket, SUM(weight) AS total,
           1.0 * SUM(weight) * SUM(weight) / SUM(weight * weight) AS n_eff
    FROM pick
    GROUP BY side, tier, weapon, kind
),
perk AS (
    SELECT p.side, p.tier, p.weapon, p.kind, c.socket, p.perk, COUNT(*) AS players,
           SUM(p.weight) AS votes, 1.0 * SUM(p.weight) / c.total AS share, c.n_eff
    FROM pick p
    JOIN col c USING (side, tier, weapon, kind)
    GROUP BY p.side, p.tier, p.weapon, p.kind, p.perk
)
SELECT side, tier, weapon, kind, socket, perk, players, votes, share, n_eff,
       -- z = 1.96: z²/2 = 1.9208, z²/4 = 0.9604, z² = 3.8416
       (share + 1.9208 / n_eff
        - 1.96 * sqrt(share * (1 - share) / n_eff + 0.9604 / (n_eff * n_eff)))
           / (1 + 3.8416 / n_eff) AS low,
       (share + 1.9208 / n_eff
        + 1.96 * sqrt(share * (1 - share) / n_eff + 0.9604 / (n_eff * n_eff)))
           / (1 + 3.8416 / n_eff) AS high,
       n_eff / (n_eff + (SELECT value FROM setting WHERE key = 'credibility_k')) AS credibility,
       CASE WHEN n_eff >= 100 THEN 'high' WHEN n_eff >= 30 THEN 'medium'
            WHEN n_eff >= 10 THEN 'low' ELSE 'very low' END AS confidence
FROM perk;
