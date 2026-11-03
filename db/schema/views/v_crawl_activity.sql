-- The PvE activities whose PGCRs a crawl fetches from a player's history:
-- those v_pgcr_category can sort into a PvE category, judged from the
-- definition alone (a history entry has no tier or skulls), and the best
-- category one can get. The hard categories, which the crawl fetches first,
-- for those that can be high-end: a raid named Master or Epic, or with a
-- Custom tier (where feats such as Cutthroat Combat are picked), raid_master;
-- a dungeon named Master or with a Master tier, dungeon_master; a Grandmaster
-- Vanguard Alert (v_grandmaster_activity) or a Nightfall named Grandmaster or
-- with a Grandmaster or Ultimate tier, gm. The rest of the raids and dungeons
-- and the Portal's activity types are basic: raid, dungeon, portal. Missions
-- played as strikes, which v_pgcr_category knows by their strike modes, the
-- crawl knows by those modes too (extract/scan.py). Keep it in step with
-- v_pgcr_category's rules.
CREATE VIEW v_crawl_activity AS
SELECT a.hash,
       CASE WHEN MAX(COALESCE(
                (t.name = 'Raid'
                 AND (a.name LIKE '%: Master%' OR a.name LIKE '%(Epic)%' OR d.name = 'Custom'))
                OR (t.name = 'Dungeon' AND (a.name LIKE '%: Master%' OR d.name = 'Master'))
                OR a.hash IN (SELECT hash FROM v_grandmaster_activity)
                OR (t.name = 'Nightfall'
                    AND (a.name LIKE '%Grandmaster%' OR d.name LIKE '%Grandmaster%'
                         OR d.name = 'Ultimate')),
                0))
                THEN CASE t.name WHEN 'Raid' THEN 'raid_master' WHEN 'Dungeon' THEN 'dungeon_master'
                                 ELSE 'gm' END
            WHEN t.name = 'Raid' THEN 'raid'
            WHEN t.name = 'Dungeon' THEN 'dungeon'
            ELSE 'portal' END AS category
FROM DestinyActivityDefinition a
JOIN DestinyActivityTypeDefinition t ON t.hash = a.activityTypeHash
LEFT JOIN DestinyActivityDifficultyTierDefinition d
    ON d.collectionHash = a.difficultyTierCollectionHash
WHERE t.name IN ('Raid', 'Dungeon', 'Strike', 'Nightfall', 'Solo Ops', 'Onslaught', 'Crawl',
                 'Seasonal Arena')
   OR a.hash IN (SELECT hash FROM v_grandmaster_activity)
GROUP BY a.hash;
