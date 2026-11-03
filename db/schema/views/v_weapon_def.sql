-- One row per weapon definition (a version), with what a weapon card shows.
-- family_name is the name without " (Adept)", " (Timelost)" or " (Harrowed)",
-- so special editions group with the base weapon; weapon is what the version
-- is scored as (weapon_version, filled by extract/versions.py): its
-- family_name, or that with its trait pool's label when the family's versions
-- roll different trait pools. slot is the name of the weapon's bucket and
-- slot_order its bucketOrder, Bungie's order for the buckets. wtype_icon is
-- the weapon type's picture: the icon of the Gunsmith Order named after the
-- type ("Hand Cannons"; "Bows" for a Combat Bow), '' when no order has the
-- name. ammo is the weapon's ammo type (primary, special or heavy; '' when
-- unknown) and ammo_icon Bungie's badge for it. element is the weapon's
-- default damage type and frame the intrinsic in socket 0, each with its icon.
CREATE VIEW v_weapon_def AS
WITH def AS (
    SELECT *,
           CASE WHEN substr(name, -8) = ' (Adept)'
                    THEN trim(substr(name, 1, length(name) - 8))
                WHEN substr(name, -11) IN (' (Timelost)', ' (Harrowed)')
                    THEN trim(substr(name, 1, length(name) - 11))
                ELSE COALESCE(name, '') END AS family_name
    FROM DestinyInventoryItemDefinition
    WHERE itemType = 3
),
type_icon AS (
    SELECT name, MIN(icon) AS icon
    FROM DestinyInventoryItemDefinition
    WHERE itemTypeDisplayName = 'Gunsmith Order' AND icon <> ''
    GROUP BY name
)
SELECT d.hash AS item_hash, COALESCE(d.name, '') AS name, d.family_name,
       COALESCE(v.weapon, d.family_name) AS weapon,
       COALESCE(b.name, 'Unknown') AS slot, COALESCE(b.bucketOrder, 0) AS slot_order,
       COALESCE(d.itemTypeDisplayName, 'Unknown') AS wtype,
       COALESCE('https://www.bungie.net' || ti.icon, '') AS wtype_icon,
       CASE WHEN COALESCE(d.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || d.icon END AS icon,
       CASE WHEN COALESCE(d.iconWatermark, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || d.iconWatermark END AS watermark,
       CASE d.ammoType WHEN 1 THEN 'primary' WHEN 2 THEN 'special' WHEN 3 THEN 'heavy'
            ELSE '' END AS ammo,
       COALESCE('https://www.bungie.net/img/destiny_content/ammo_types/'
                || CASE d.ammoType WHEN 1 THEN 'primary' WHEN 2 THEN 'special'
                                   WHEN 3 THEN 'heavy' END || '.png', '') AS ammo_icon,
       COALESCE(dt.name, '') AS element,
       CASE WHEN COALESCE(dt.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || dt.icon END AS element_icon,
       COALESCE(f.name, '') AS frame, COALESCE(f.icon, '') AS frame_icon
FROM def d
LEFT JOIN weapon_version v ON v.item_hash = d.hash
LEFT JOIN DestinyInventoryBucketDefinition b ON b.hash = d.bucketTypeHash
LEFT JOIN type_icon ti ON ti.name = CASE d.itemTypeDisplayName
    WHEN 'Combat Bow' THEN 'Bows' ELSE d.itemTypeDisplayName || 's' END
LEFT JOIN DestinyDamageTypeDefinition dt ON dt.hash = d.defaultDamageTypeHash
LEFT JOIN DestinyItemSocketEntryDefinition s0 ON s0.itemHash = d.hash AND s0.socketIndex = 0
LEFT JOIN v_plug f ON f.hash = s0.singleInitialItemHash;
