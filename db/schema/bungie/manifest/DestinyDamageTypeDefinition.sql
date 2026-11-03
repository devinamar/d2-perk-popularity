-- DestinyDamageTypeDefinition: "All damage types that are possible in the game
-- are defined here, along with localized info and icons as needed." Rows kept:
-- all.
CREATE TABLE DestinyDamageTypeDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash  INTEGER PRIMARY KEY,
    -- displayProperties.name, such as 'Solar'. Bungie's documentation gives no
    -- description.
    name  TEXT,
    -- displayProperties.icon: "Note that "icon" is sometimes misleading, and
    -- should be interpreted in the context of the entity. For instance, in
    -- Destiny 1 the DestinyRecordBookDefinition's icon was a big picture of a
    -- book. But usually, it will be a small square image that you can use
    -- as... well, an icon. They are currently represented as 96px x 96px
    -- images." A path on www.bungie.net; none for Raid.
    icon  TEXT
);
