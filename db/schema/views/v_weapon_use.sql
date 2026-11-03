-- One row per weapon use the heat maps count: a weapon a player got kills with
-- in a PGCR the scan kept and the player finished, matched to the copy they
-- still had equipped (its plugs are in DestinyItemSocketsComponent). A use
-- counts its PGCR category's weight on that category's side (pve or pvp).
-- checkpoint is 1 for a clear the player didn't make from the start, in a
-- category with checkpoints (raids and dungeons): the run started from a
-- checkpoint, or the player joined more than setting's late_join_seconds in;
-- a PGCR that doesn't say how its run started counts as started fresh.
CREATE VIEW v_weapon_use AS
SELECT c.instanceId, c.period, c.category, c.side, c.weight, w.characterId,
       w.referenceId AS item_hash, wd.weapon, w.itemInstanceId,
       a.checkpoints AND (COALESCE(h.activityWasStartedFromBeginning, 1) = 0
                          OR e.startSeconds > s.value) AS checkpoint
FROM DestinyHistoricalWeaponStats w
JOIN DestinyPostGameCarnageReportEntry e
    ON e.instanceId = w.instanceId AND e.characterId = w.characterId
JOIN v_pgcr_category c ON c.instanceId = w.instanceId
JOIN DestinyPostGameCarnageReportData h ON h.instanceId = w.instanceId
JOIN activity_category a ON a.key = c.category
JOIN v_weapon_def wd ON wd.item_hash = w.referenceId
CROSS JOIN (SELECT value FROM setting WHERE key = 'late_join_seconds') s
WHERE e.completed = 1 AND c.category IS NOT NULL AND w.itemInstanceId IS NOT NULL;
