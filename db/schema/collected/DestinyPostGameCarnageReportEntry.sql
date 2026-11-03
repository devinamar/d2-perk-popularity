-- DestinyPostGameCarnageReportEntry: one player's character in a PGCR, from its
-- entries ("Collection of players and their data for this activity."). Rows:
-- the players of every PGCR the scan kept.
CREATE TABLE DestinyPostGameCarnageReportEntry (
    -- The PGCR this entry is in.
    instanceId      INTEGER NOT NULL REFERENCES DestinyPostGameCarnageReportData(instanceId),
    -- "ID of the player's character used in the activity." A large number
    -- sent as text.
    characterId     TEXT NOT NULL,
    -- player.destinyUserInfo.membershipId: "Membership ID as they user is
    -- known in the Accounts service".
    membershipId    TEXT NOT NULL,
    -- player.destinyUserInfo.crossSaveOverride ("If there is a cross save
    -- override in effect, this value will tell you the type that is
    -- overridding this one."), else its membershipType: the platform the
    -- profile endpoint knows the player by. BungieMembershipType: 1 Xbox, 2
    -- PSN, 3 Steam, and so on.
    membershipType  INTEGER NOT NULL,
    -- values.completed.basic.value: 1 when the player finished the activity,
    -- else 0. Only finished players' weapons count.
    completed       INTEGER NOT NULL DEFAULT 0,
    -- values.startSeconds.basic.value: how many seconds into the activity the
    -- player joined, 0 to 5 for a fireteam there from the start (they load in
    -- a few seconds apart); 0 when absent, and for entries stored before it
    -- was kept.
    startSeconds    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (instanceId, characterId)
);
