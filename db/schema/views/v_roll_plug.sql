-- Each vote's perks (v_roll_unit): its copy's plugs in the perk sockets where
-- the weapon gives a choice, some version of the weapon rolling more than one
-- perk there (v_weapon_pool) or copies showing more than one (an origin socket
-- can list its options inline, which v_weapon_pool doesn't see). Exotic fixed
-- columns and one-perk origins drop out, and frames (kind intrinsic) aren't
-- scored: where they differ it's by version or an exotic's upgrade level. A
-- fixed copy of a weapon that otherwise rolls (a quest or curated version)
-- keeps its perks, since players chose to run it.
CREATE VIEW v_roll_plug AS
WITH plug AS MATERIALIZED (
    SELECT u.side, u.tier, u.weapon, u.item_hash, u.membershipId, u.itemInstanceId,
           u.weight, s.socketIndex AS socket_idx, p.kind, p.name AS perk
    FROM v_roll_unit u
    JOIN DestinyItemSocketsComponent s ON s.itemInstanceId = u.itemInstanceId
    JOIN v_plug p ON p.hash = s.plugHash
    WHERE p.kind != 'intrinsic'
),
choice AS MATERIALIZED (
    SELECT d.weapon, pool.socket_idx
    FROM v_weapon_pool pool
    JOIN v_weapon_def d ON d.item_hash = pool.item_hash
    GROUP BY d.weapon, pool.socket_idx
    HAVING COUNT(DISTINCT pool.perk) > 1
    UNION
    SELECT weapon, socket_idx
    FROM plug
    GROUP BY weapon, socket_idx
    HAVING COUNT(DISTINCT perk) > 1
)
SELECT plug.*
FROM plug
JOIN choice USING (weapon, socket_idx);
