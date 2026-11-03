-- The season each release trait marks: a weapon definition's traitIds
-- (DestinyInventoryItemDefinition.traitIds) name the release that last updated
-- it, such as 'releases.v710.season'. extract/versions.py names a split
-- weapon's pools by their earliest release's season when their sources can't
-- tell them apart. Kept by hand, in step with d2-inventory-report's copy; the
-- rows are part of the view, so a change here rebuilds the database on the
-- next run (keeping what the scans collected).
CREATE VIEW release_tag_season (traitId, season_num, season_name, season_date) AS VALUES
    -- Year 1 - Red War / Curse of Osiris / Warmind
    ('releases.v100', 1, 'Red War', '2017-09-06'),
    ('releases.v110', 2, 'Curse of Osiris', '2017-12-05'),
    ('releases.v120', 3, 'Warmind', '2018-05-08'),
    -- Base game exotics
    ('releases.v300.annual', 1, 'Red War', '2017-09-06'),
    ('releases.v310.season', 6, 'Season of the Drifter', '2019-03-05'),
    -- Warmind exotics
    ('releases.v320.season', 3, 'Warmind', '2018-05-08'),
    -- Year 2 - Forsaken / Annual Pass
    ('releases.v400.annual', 4, 'Forsaken', '2018-09-04'),
    ('releases.v400.season', 4, 'Forsaken', '2018-09-04'),
    -- Black Armory
    ('releases.v410.season', 5, 'Season of the Forge', '2018-12-04'),
    -- NOTE: verify — unusual mapping
    ('releases.v420.season', 10, 'Season of the Worthy', '2020-03-10'),
    -- Year 3 - Shadowkeep / Seasons 8-11
    ('releases.v450.season', 7, 'Season of Opulence', '2019-06-04'),
    ('releases.v460.season', 8, 'Shadowkeep', '2019-10-01'),
    ('releases.v470.season', 9, 'Season of Dawn', '2019-12-10'),
    ('releases.v480.season', 10, 'Season of the Worthy', '2020-03-10'),
    -- Year 4 - Beyond Light / Seasons 12-15
    ('releases.v490.season', 11, 'Season of Arrivals', '2020-06-09'),
    ('releases.v500.annual', 12, 'Beyond Light', '2020-11-10'),
    ('releases.v500.season', 12, 'Beyond Light', '2020-11-10'),
    ('releases.v510.season', 13, 'Season of the Chosen', '2021-02-09'),
    ('releases.v520.season', 14, 'Season of the Splicer', '2021-05-11'),
    ('releases.v530.season', 15, 'Season of the Lost', '2021-08-24'),
    -- Year 5 - Witch Queen / Seasons 16-19
    ('releases.v540.season', 15, '30th Anniversary', '2021-12-07'),
    ('releases.v600.annual', 16, 'Witch Queen', '2022-02-22'),
    ('releases.v600.season', 16, 'Witch Queen', '2022-02-22'),
    ('releases.v610.season', 17, 'Season of the Haunted', '2022-05-24'),
    ('releases.v620.season', 18, 'Season of Plunder', '2022-08-23'),
    -- Year 6 - Lightfall / Seasons 20-23
    ('releases.v630.season', 19, 'Season of the Seraph', '2022-12-06'),
    ('releases.v700.annual', 20, 'Lightfall', '2023-02-28'),
    ('releases.v700.season', 20, 'Lightfall', '2023-02-28'),
    ('releases.v710.season', 21, 'Season of the Deep', '2023-05-23'),
    ('releases.v720.season', 22, 'Season of the Witch', '2023-08-22'),
    -- Year 7 - The Final Shape / Episodes (official names from DestinySeasonDefinition)
    ('releases.v730.season', 23, 'Season of the Wish', '2023-11-28'),
    ('releases.v800.annual', 24, 'The Final Shape', '2024-06-04'),
    ('releases.v800.season', 24, 'Episode: Echoes', '2024-06-04'),
    ('releases.v810.season', 25, 'Episode: Revenant', '2024-10-08'),
    ('releases.v820.season', 26, 'Episode: Heresy', '2025-02-04'),
    -- v9xx - World loot pool updates
    ('releases.v830.season', 27, 'Reclamation', '2025-07-15'),
    ('releases.v900.core', 24, 'Echoes Core', '2024-06-04'),
    ('releases.v900.dlc', 24, 'Echoes Core', '2024-06-04'),
    ('releases.v910', 25, 'Revenant Core', '2024-10-08'),
    ('releases.v910.core', 25, 'Revenant Core', '2024-10-08'),
    ('releases.v950', 28, 'Lawless', '2025-12-02'),
    ('releases.v950.core', 28, 'Lawless', '2025-12-02'),
    ('releases.v950.dlc', 28, 'Lawless', '2025-12-02'),
    ('releases.v960.core', 28, 'Lawless', '2025-12-02'),
    ('releases.v970.core', 28, 'Monument of Triumph', '2025-12-02');
