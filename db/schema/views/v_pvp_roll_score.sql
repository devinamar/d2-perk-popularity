-- The PvP table: v_roll_score's PvP rows, the most popular weapon first, its
-- columns in socket order (the trait pair before each trait on its own) and
-- each column's perks by share.
CREATE VIEW v_pvp_roll_score AS
SELECT * FROM v_roll_score WHERE side = 'pvp'
ORDER BY weapon_rank, weapon, socket, kind != 'traits', kind, rank, perk;
