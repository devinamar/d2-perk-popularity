-- The PvE table: v_roll_score's PvE rows, the most popular weapon first, its
-- columns in socket order (the trait pair before each trait on its own) and
-- each column's perks by share.
CREATE VIEW v_pve_roll_score AS
SELECT * FROM v_roll_score WHERE side = 'pve'
ORDER BY weapon_rank, weapon, socket, kind != 'traits', kind, rank, perk;
