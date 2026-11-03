-- DestinyItemSocketEntryDefinition: "The definition information for a specific
-- socket on an item. This will determine how the socket behaves in-game."
-- Rows: the sockets.socketEntries of each weapon definition in
-- DestinyInventoryItemDefinition ("Each non-intrinsic (or mutable) socket on
-- an item is defined here."), in order. A copy has the same sockets; only its
-- plugs differ.
CREATE TABLE DestinyItemSocketEntryDefinition (
    -- The item whose sockets.socketEntries this entry is in.
    itemHash               INTEGER NOT NULL,
    -- The entry's position in sockets.socketEntries, from 0. A copy's sockets
    -- use the same index.
    socketIndex            INTEGER NOT NULL,
    -- "If a valid hash, this is the hash identifier for the
    -- DestinyInventoryItemDefinition representing the Plug that will be
    -- initially inserted into the item on item creation. Otherwise, this
    -- Socket will either start without a plug inserted, or will have one
    -- randomly inserted." NULL when the socket has none.
    singleInitialItemHash  INTEGER,
    -- "This field replaces "randomizedPlugItems" as of Shadowkeep launch. If a
    -- socket has randomized plugs, this is a pointer to the set of plugs that
    -- could be used, as defined in DestinyPlugSetDefinition. If null, the item
    -- has no randomized plugs."
    randomizedPlugSetHash  INTEGER,
    -- "If this socket's plugs come from a reusable DestinyPlugSetDefinition,
    -- this is the identifier for that set. We added this concept to reduce
    -- some major duplication that's going to come from sockets as replacements
    -- for what was once implemented as large sets of items and kiosks (like
    -- Emotes). As of Shadowkeep, these will come up much more frequently and
    -- be driven by game content rather than custom curation."
    reusablePlugSetHash    INTEGER,
    PRIMARY KEY (itemHash, socketIndex)
);
