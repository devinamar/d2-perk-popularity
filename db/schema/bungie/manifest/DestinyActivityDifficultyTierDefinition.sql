-- DestinyActivityDifficultyTierDefinition: one difficulty tier of an
-- activity, from DestinyActivityDifficultyTierCollectionDefinition's
-- difficultyTiers. Bungie's documentation describes neither type. A PGCR's
-- activityDifficultyTier is a tier's position in its activity's collection.
-- Rows: every collection's tiers, in order.
CREATE TABLE DestinyActivityDifficultyTierDefinition (
    -- The DestinyActivityDifficultyTierCollectionDefinition whose
    -- difficultyTiers this tier is in.
    collectionHash  INTEGER NOT NULL,
    -- The tier's position in difficultyTiers, from 0.
    tierIndex       INTEGER NOT NULL,
    -- displayProperties.name, such as 'Master', 'Grandmaster' or 'Custom'.
    name            TEXT,
    PRIMARY KEY (collectionHash, tierIndex)
);
