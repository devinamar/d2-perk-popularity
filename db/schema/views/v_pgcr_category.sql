-- Each stored PGCR with the activity category the scan keeps it under
-- (activity_category), or NULL for one it doesn't keep: a private match, a
-- Sparrow Racing League race (mode 94, filed as PvP but without weapons), a
-- patrol, a story mission, a lost sector and the like. The first rule that
-- matches wins. PvP is known by its modes. Raids and dungeons are known by
-- their activity type, since newer ones have no modes. A Master raid is one
-- named Master (The Desert Perpetual's harder version is called Epic) or one
-- run with Cutthroat Combat, about as hard: that feat is among its selected
-- skulls, which a PGCR lists by skullIdentifierHash ("Feat: Cutthroat Combat"
-- is 2673088233, or 3747452238 in one skull collection; an unfilled slot is
-- 790421403, "Empty Feat"). tier is the name of the difficulty tier the
-- PGCR was played at, from its activity's tier collection; a Grandmaster is a
-- Grandmaster Vanguard Alert (v_grandmaster_activity, the weekly strikes once
-- called Grandmaster Nightfalls) or a Nightfall-type activity (Fireteam and
-- Pinnacle Ops) at Grandmaster or Ultimate, above it. The rest of the Portal,
-- other missions and Solo Ops at any tier among them, is known by its type or
-- its strike modes. activity_type and tier are there to check the rules
-- against.
CREATE VIEW v_pgcr_category AS
SELECT p.instanceId, p.period, t.name AS activity_type, d.name AS tier,
       c.key AS category, c.side, c.weight
FROM DestinyPostGameCarnageReportData p
LEFT JOIN DestinyActivityDefinition a ON a.hash = p.referenceId
LEFT JOIN DestinyActivityTypeDefinition t ON t.hash = a.activityTypeHash
LEFT JOIN DestinyActivityDifficultyTierDefinition d
    ON d.collectionHash = a.difficultyTierCollectionHash
   AND d.tierIndex = p.activityDifficultyTier
LEFT JOIN activity_category c ON c.key = CASE
    WHEN p.isPrivate OR EXISTS (SELECT 1 FROM json_each(p.modes) WHERE value = 94) THEN NULL
    WHEN EXISTS (SELECT 1 FROM json_each(p.modes) WHERE value = 84) THEN 'trials'
    WHEN EXISTS (SELECT 1 FROM json_each(p.modes) WHERE value = 69) THEN 'competitive'
    WHEN EXISTS (SELECT 1 FROM json_each(p.modes) WHERE value IN (63, 75)) THEN 'gambit'
    WHEN EXISTS (SELECT 1 FROM json_each(p.modes) WHERE value = 5) THEN 'quickplay'
    WHEN t.name = 'Raid' AND (
        a.name LIKE '%: Master%' OR a.name LIKE '%(Epic)%'
        OR EXISTS (SELECT 1 FROM json_each(p.selectedSkullHashes)
                   WHERE value IN (2673088233, 3747452238)))
        THEN 'raid_master'
    WHEN p.referenceId IN (SELECT hash FROM v_grandmaster_activity)
         OR (t.name = 'Nightfall'
             AND (d.name LIKE '%Grandmaster%' OR d.name = 'Ultimate'
                  OR a.name LIKE '%Grandmaster%'))
        THEN 'gm'
    WHEN t.name = 'Dungeon' AND (a.name LIKE '%: Master%' OR d.name = 'Master')
        THEN 'dungeon_master'
    WHEN t.name = 'Raid' THEN 'raid'
    WHEN t.name = 'Dungeon' THEN 'dungeon'
    WHEN t.name IN ('Strike', 'Nightfall', 'Solo Ops', 'Onslaught', 'Crawl', 'Seasonal Arena')
        OR EXISTS (SELECT 1 FROM json_each(p.modes) WHERE value IN (3, 18, 46))
        THEN 'portal'
END;
