-- DestinyItemSocketsComponent (component 305): "Instanced items can have
-- sockets, which are slots on the item where plugs can be inserted." Rows: the
-- plugged sockets of each weapon copy a PGCR use matched
-- (DestinyHistoricalWeaponStats.itemInstanceId), from the profile fetched
-- after the match. A copy seen again replaces its rows.
CREATE TABLE DestinyItemSocketsComponent (
    -- The copy this socket belongs to.
    itemInstanceId  TEXT NOT NULL,
    -- The socket's position in sockets, from 0; it matches the definition's
    -- DestinyItemSocketEntryDefinition rows.
    socketIndex     INTEGER NOT NULL,
    -- "The currently active plug, if any. Note that, because all plugs are
    -- statically defined, its effect on stats and perks can be statically
    -- determined using the plug item's definition."
    plugHash        INTEGER NOT NULL,
    PRIMARY KEY (itemInstanceId, socketIndex)
);
