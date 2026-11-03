-- DestinyPostGameCarnageReportData: a post-game carnage report (PGCR), Bungie's
-- record of one finished activity: what was played, at what difficulty, and
-- (in DestinyPostGameCarnageReportEntry) who played it. Bungie's documentation
-- gives the type no description. Rows: every PGCR the scan fetched, kept or
-- not, so a later scan skips it; v_pgcr_category sorts each into its category.
CREATE TABLE DestinyPostGameCarnageReportData (
    -- activityDetails.instanceId: "The unique identifier for this *specific*
    -- match that was played." Sent as text; stored as a number, since the scan
    -- walks the ids in order.
    instanceId              INTEGER PRIMARY KEY,
    -- "Date and time for the activity." ISO 8601 in UTC, such as
    -- '2026-10-20T13:45:12Z'.
    period                  TEXT NOT NULL,
    -- activityDetails.referenceId: "The unique hash identifier of the
    -- DestinyActivityDefinition that was played. If I had this to do over,
    -- it'd be named activityHash. Too late now."
    referenceId             INTEGER,
    -- activityDetails.directorActivityHash: "The unique hash identifier of the
    -- DestinyActivityDefinition that was played." For a playlist, the playlist.
    directorActivityHash    INTEGER,
    -- activityDetails.mode: "Indicates the most specific game mode of the
    -- activity that we could find." Destiny.HistoricalStats.Definitions.
    -- DestinyActivityModeType, such as 84 Trials of Osiris.
    mode                    INTEGER,
    -- activityDetails.modes: "The list of all Activity Modes to which this
    -- activity applies, including aggregates." A JSON array, such as [84, 5].
    modes                   TEXT NOT NULL DEFAULT '[]',
    -- activityDetails.isPrivate: "Whether or not the match was a private
    -- match." 1 or 0.
    isPrivate               INTEGER NOT NULL DEFAULT 0,
    -- "Difficulty tier index value for the activity." The tier's position in
    -- its activity's DestinyActivityDifficultyTierDefinition rows.
    activityDifficultyTier  INTEGER,
    -- "Collection of player-selected skull hashes active for the activity." A
    -- JSON array of each skull's skullIdentifierHash (not its hash), one per
    -- slot; a raid's feats, such as Cutthroat Combat, are skulls.
    selectedSkullHashes     TEXT NOT NULL DEFAULT '[]',
    -- "True if the activity was started from the beginning, if that
    -- information is available and the activity was played post Witch Queen
    -- release." 1, or 0 for a run started from a checkpoint; NULL when the
    -- PGCR doesn't say, and for PGCRs stored before it was kept.
    activityWasStartedFromBeginning  INTEGER
);
