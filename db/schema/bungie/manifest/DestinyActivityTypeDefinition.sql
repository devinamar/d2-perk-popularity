-- DestinyActivityTypeDefinition: "In Destiny 2, an Activity Type represents a
-- conceptual categorization of Activities. These are most commonly used in the
-- game for the subtitle under Activities, but BNet uses them extensively to
-- identify and group activities by their common properties." Raids and
-- dungeons are known by their type, since newer ones have no activity modes.
-- Rows kept: all.
CREATE TABLE DestinyActivityTypeDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash  INTEGER PRIMARY KEY,
    -- displayProperties.name, such as 'Raid' or 'Dungeon'. Bungie's
    -- documentation gives no description.
    name  TEXT
);
