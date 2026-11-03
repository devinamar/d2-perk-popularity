-- Every stored plug as the app shows it: its name, category, icon as a full
-- URL, its description as Bungie wrote it (inline icon tokens included), and
-- its kind: the kind of weapon perk socket its category fills. Each weapon type
-- names its barrel and magazine differently; some weapons, most of them
-- exotics, have a stock or a grip too. A plug whose category isn't a weapon
-- perk (masterworks, mods, shaders, trackers) has no kind (NULL).
CREATE VIEW v_plug AS
SELECT hash, COALESCE(name, '') AS name, plugCategoryIdentifier,
       CASE WHEN COALESCE(icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || icon END AS icon,
       COALESCE(description, '') AS description,
       CASE
           WHEN plugCategoryIdentifier IN ('barrels', 'scopes', 'tubes', 'bowstrings', 'blades', 'hafts')
               THEN 'barrel'
           WHEN plugCategoryIdentifier IN ('magazines', 'batteries', 'arrows', 'guards', 'magazines_gl')
               THEN 'magazine'
           WHEN plugCategoryIdentifier = 'stocks' THEN 'stock'
           WHEN plugCategoryIdentifier = 'grips' THEN 'grip'
           WHEN plugCategoryIdentifier = 'frames' THEN 'trait'
           WHEN plugCategoryIdentifier = 'origins' THEN 'origin'
           WHEN plugCategoryIdentifier = 'intrinsics' THEN 'intrinsic'
       END AS kind
FROM DestinyInventoryItemDefinition
WHERE plugCategoryIdentifier IS NOT NULL;
