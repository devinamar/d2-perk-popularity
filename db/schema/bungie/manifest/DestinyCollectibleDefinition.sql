-- DestinyCollectibleDefinition: Bungie's description reads only "Defines a". A
-- collectible is an item's Collections entry. Rows kept: the collectibles the
-- stored weapons name.
CREATE TABLE DestinyCollectibleDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash          INTEGER PRIMARY KEY,
    -- "A human readable string for a hint about how to acquire the item."
    sourceString  TEXT
);
