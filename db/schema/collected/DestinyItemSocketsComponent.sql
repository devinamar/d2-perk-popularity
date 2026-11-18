-- DestinyItemSocketsComponent (component 305): "Instanced items can have
-- sockets, which are slots on the item where plugs can be inserted." Rows:
-- each copy a PGCR use matched (DestinyHistoricalWeaponStats.itemInstanceId),
-- from the profile fetched after the match, its sockets as Bungie lists them,
-- down to their plugs. A copy seen again replaces its row. One row per copy:
-- the scores read a copy's whole roll, never one socket of it.
CREATE TABLE DestinyItemSocketsComponent (
    -- The copy these sockets belong to.
    itemInstanceId  TEXT PRIMARY KEY,
    -- Each socket's plugHash ("The currently active plug, if any. Note that,
    -- because all plugs are statically defined, its effect on stats and perks
    -- can be statically determined using the plug item's definition."), in
    -- socket order: a JSON list, null for a socket without one, so a plug's
    -- place is its socketIndex in the definition's
    -- DestinyItemSocketEntryDefinition rows.
    plugHashes      TEXT NOT NULL
) WITHOUT ROWID;
