-- DestinyInventoryBucketDefinition: "An Inventory (be it Character or Profile
-- level) is comprised of many Buckets. An example of a bucket is "Primary
-- Weapons", where all of the primary weapons on a character are gathered
-- together into a single visual element in the UI: a subset of the inventory
-- that has a limited number of slots, and in this case also has an associated
-- Equipment Slot for equipping an item in the bucket. Item definitions declare
-- what their "default" bucket is
-- (DestinyInventoryItemDefinition.inventory.bucketTypeHash), and Item
-- instances will tell you which bucket they are currently residing in
-- (DestinyItemComponent.bucketHash)." Rows kept: the buckets the stored
-- weapons belong to.
CREATE TABLE DestinyInventoryBucketDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash         INTEGER PRIMARY KEY,
    -- displayProperties.name, such as 'Kinetic Weapons'. Bungie's
    -- documentation gives no description.
    name         TEXT,
    -- "Use this property to provide a quick-and-dirty recommended ordering for
    -- buckets in the UI. Most UIs will likely want to forsake this for
    -- something more custom and manual."
    bucketOrder  INTEGER
);
