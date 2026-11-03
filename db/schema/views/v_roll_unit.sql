-- One vote per player's copy of a weapon (v_weapon_def's weapon: its family,
-- or one trait pool of it) in each of a side's two content groups, hard and
-- normal (activity_category's hard), from its uses by category (copy_use: the
-- copies used within the rolling window, and the newest older ones each weapon
-- keeps; extract/votes.py). A copy's roll is the same in every match, so its
-- matches in a group count once together, and a copy used in both groups
-- votes in each. The vote weighs what the hardest
-- content it was used in within the group weighs (the highest category
-- weight), a raid's or dungeon's cut by setting's full_clear_weight when the
-- copy was used there only in clears its player didn't make from the start
-- (copy_use's checkpoint): to a third of a full clear's at 0.75. last_seen is
-- when the copy was last used there.
CREATE VIEW v_roll_unit AS
SELECT a.side, CASE WHEN a.hard THEN 'hard' ELSE 'normal' END AS tier, d.weapon,
       u.item_hash, u.membershipId, u.itemInstanceId,
       MAX(a.weight * CASE WHEN u.checkpoint THEN (1 - s.value) / s.value ELSE 1 END) AS weight,
       MAX(u.last_seen) AS last_seen
FROM copy_use u
JOIN activity_category a ON a.key = u.category
JOIN v_weapon_def d ON d.item_hash = u.item_hash
CROSS JOIN (SELECT value FROM setting WHERE key = 'full_clear_weight') s
GROUP BY a.side, a.hard, u.itemInstanceId;
