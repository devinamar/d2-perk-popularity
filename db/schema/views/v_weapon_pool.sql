-- The perks each weapon definition can roll in each of its perk sockets: the
-- socket's plug set, randomized or fixed. can_roll is 0 for a perk the set
-- still lists but no longer drops; a perk the set lists twice can roll if
-- either entry can. position is its place in the set (the first, for a perk
-- listed twice), the order the game and DIM show the perks in. Compared with
-- v_weapon_roll, it shows where a copy's roll sits in what the weapon could have
-- rolled.
CREATE VIEW v_weapon_pool AS
SELECT ds.itemHash AS item_hash, ds.socketIndex AS socket_idx, p.kind, p.name AS perk,
       e.plugItemHash AS plug_hash, MAX(COALESCE(e.currentlyCanRoll, 1)) AS can_roll,
       MIN(e.position) AS position
FROM DestinyItemSocketEntryDefinition ds
JOIN DestinyInventoryItemDefinition d ON d.hash = ds.itemHash AND d.itemType = 3
JOIN DestinyItemSocketEntryPlugItemRandomizedDefinition e
    ON e.plugSetHash = COALESCE(ds.randomizedPlugSetHash, ds.reusablePlugSetHash)
JOIN v_plug p ON p.hash = e.plugItemHash
WHERE p.kind IS NOT NULL AND p.name != ''
GROUP BY ds.itemHash, ds.socketIndex, e.plugItemHash;
