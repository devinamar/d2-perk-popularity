-- DestinyActivityDefinition: "The static data about Activities in Destiny 2.
-- Note that an Activity must be combined with an ActivityMode to know - from a
-- Gameplay perspective - what the user is "Playing"." A PGCR names the
-- activity it was (DestinyPostGameCarnageReportData.referenceId); v_pgcr_category
-- reads its name, type and difficulty tiers. Rows kept: all.
CREATE TABLE DestinyActivityDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash                          INTEGER PRIMARY KEY,
    -- displayProperties.name, such as "Salvation's Edge: Master". Bungie's
    -- documentation gives no description.
    name                          TEXT,
    -- "The hash identifier for the Activity Type of this Activity. You may use
    -- it to look up the DestinyActivityTypeDefinition for human readable info,
    -- but be forewarned: Playlists and many PVP Map Activities will map to
    -- generic Activity Types. You'll have to use your knowledge of the
    -- Activity Mode being played to get more specific information about what
    -- the user is playing."
    activityTypeHash              INTEGER,
    -- The DestinyActivityDifficultyTierCollectionDefinition holding the
    -- difficulty tiers the activity can be played at (Normal, Expert, Master,
    -- Grandmaster...). Bungie's documentation gives no description. NULL for
    -- an activity without tiers.
    difficultyTierCollectionHash  INTEGER
);
