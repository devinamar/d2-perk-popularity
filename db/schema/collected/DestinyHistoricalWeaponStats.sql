-- DestinyHistoricalWeaponStats: a weapon a player got kills with in a PGCR,
-- from the entry's extended.weapons ("List of weapons and their perspective
-- values."). Rows: every weapon each kept PGCR's players used. itemInstanceId
-- is the app's own: the copy the player had equipped on that character when
-- the scan fetched their profile, which is how a use gets its perks.
CREATE TABLE DestinyHistoricalWeaponStats (
    -- The PGCR and character this weapon was used in and by.
    instanceId         INTEGER NOT NULL,
    characterId        TEXT NOT NULL,
    -- "The hash ID of the item definition that describes the weapon."
    referenceId        INTEGER NOT NULL,
    -- values.uniqueWeaponKills.basic.value: the kills the player got with it.
    uniqueWeaponKills  INTEGER,
    -- The copy of the weapon still equipped on the character after the match
    -- (DestinyItemComponent.itemInstanceId: "If the item is instanced, it will
    -- have an instance ID."); its plugs are in DestinyItemSocketsComponent.
    -- NULL when the player no longer had it equipped, or hides their profile.
    itemInstanceId     TEXT,
    PRIMARY KEY (instanceId, characterId, referenceId),
    FOREIGN KEY (instanceId, characterId)
        REFERENCES DestinyPostGameCarnageReportEntry(instanceId, characterId)
);
