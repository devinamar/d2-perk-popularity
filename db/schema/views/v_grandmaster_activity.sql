-- The Grandmaster Vanguard Alerts, once called Grandmaster Nightfalls: the
-- Portal's weekly strikes that can be played only at Grandmaster or Ultimate,
-- filed as missions named "<strike>: Customize". Known by their tier
-- collection, every tier of which is Grandmaster or Ultimate; on 2026-10-20
-- those were exactly the six activities the fireteam finder lists under
-- "Grandmaster Vanguard Alert".
CREATE VIEW v_grandmaster_activity AS
SELECT a.hash
FROM DestinyActivityDefinition a
JOIN DestinyActivityDifficultyTierDefinition d ON d.collectionHash = a.difficultyTierCollectionHash
GROUP BY a.hash
HAVING SUM(d.name LIKE '%Grandmaster%' OR d.name = 'Ultimate') = COUNT(*);
