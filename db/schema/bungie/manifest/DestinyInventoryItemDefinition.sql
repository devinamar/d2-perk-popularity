-- DestinyInventoryItemDefinition: "So much of what you see in Destiny is
-- actually an Item used in a new and creative way. This is the definition for
-- Items in Destiny, which started off as just entities that could exist in
-- your Inventory but ended up being the backing data for so much more: quests,
-- reward previews, slots, and subclasses. In practice, you will want to
-- associate this data with "live" item data from a Bungie.Net Platform call:
-- these definitions describe the item in generic, non-instanced terms: but an
-- actual instance of an item can vary widely from these generic definitions."
-- Rows kept: weapons (itemType 3), every plug (an item with a plug block) and
-- the Gunsmith Orders, whose icons picture the weapon types (v_weapon_def).
CREATE TABLE DestinyInventoryItemDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash                    INTEGER PRIMARY KEY,
    -- displayProperties.name: The name shown in game. Bungie's documentation
    -- gives no description.
    name                    TEXT,
    -- displayProperties.description: the description shown in game, with
    -- Bungie's inline icon tokens such as [Arc]. Bungie's documentation gives
    -- no description.
    description             TEXT,
    -- displayProperties.icon: "Note that "icon" is sometimes misleading, and
    -- should be interpreted in the context of the entity. For instance, in
    -- Destiny 1 the DestinyRecordBookDefinition's icon was a big picture of a
    -- book. But usually, it will be a small square image that you can use
    -- as... well, an icon. They are currently represented as 96px x 96px
    -- images." A path on www.bungie.net.
    icon                    TEXT,
    -- "A value indicating the "base" the of the item. This enum is a useful
    -- but dramatic oversimplification of what it means for an item to have a
    -- "Type". Still, it's handy in many situations. itemCategoryHashes are the
    -- preferred way of identifying types, we have retained this enum for its
    -- convenience." Destiny.DestinyItemType: 3 Weapon.
    itemType                INTEGER,
    -- "The localized title/name of the item's type. This can be whatever the
    -- designers want, and has no guarantee of consistency between items." For
    -- example 'Hand Cannon'.
    itemTypeDisplayName     TEXT,
    -- inventory.tierType: "The enumeration matching the tier type of the item
    -- to known values, again for convenience sake." Destiny.TierType: 4 Rare,
    -- 5 Superior (the game's Legendary), 6 Exotic.
    tierType                INTEGER,
    -- inventory.bucketTypeHash: "The hash identifier for the
    -- DestinyInventoryBucketDefinition to which this item belongs. I should
    -- have named this "bucketHash", but too many things refer to it now.
    -- Sigh."
    bucketTypeHash          INTEGER,
    -- equippingBlock.ammoType: "Ammo type used by a weapon is no longer
    -- determined by the bucket in which it is contained. If the item has an
    -- ammo type - i.e. if it is a weapon - this will be the type of ammunition
    -- expected." Destiny.DestinyAmmunitionType: 1 Primary, 2 Special, 3 Heavy.
    ammoType                INTEGER,
    -- "Similar to defaultDamageType, but represented as the hash identifier
    -- for a DestinyDamageTypeDefinition. I will likely regret leaving in the
    -- enumeration versions of these properties, but for now they're very
    -- convenient."
    defaultDamageTypeHash   INTEGER,
    -- "If available, this is the original 'active' release watermark overlay
    -- for the icon. If the item has different versions, this can be overridden
    -- by the 'display version watermark icon' from the 'quality' block.
    -- Alternatively, if there is no watermark for the version, and the item
    -- version has a power cap below the current season power cap, this can be
    -- overridden by the iconWatermarkShelved property." A path on
    -- www.bungie.net.
    iconWatermark           TEXT,
    -- "If this item has a collectible related to it, this is the hash
    -- identifier of that collectible entry." Not a foreign key: only the
    -- weapons' collectibles are stored.
    collectibleHash         INTEGER,
    -- "Traits are metadata tags applied to this item. For example: armor slot,
    -- weapon type, foundry, faction, etc. These IDs come from the game and
    -- don't map to any content, but should still be useful." A JSON array,
    -- such as ["releases.v710.season"]; [] for an item without traits.
    traitIds                TEXT,
    -- plug.plugCategoryIdentifier: "The string identifier for the plug's
    -- category. Use the socket's DestinySocketTypeDefinition.plugWhitelist to
    -- determine whether this plug can be inserted into the socket." NULL for
    -- an item that isn't a plug.
    plugCategoryIdentifier  TEXT
);
