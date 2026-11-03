# Manifest ingest: copies what the app uses from the downloaded manifest into
# the tables named after its definitions (db/schema/bungie/manifest/): every
# weapon and plug (and the Gunsmith Orders, Banshee's bounties whose icons
# picture the weapon types), the weapons' sockets, the plug sets they roll
# from, their Collections entries, buckets and damage types, and every
# activity with its type and difficulty tiers; then groups the weapons'
# versions into the weapons scored (extract/versions.py). Runs only for a new
# version.
import contextlib
import json
import sqlite3

import paths
from extract import versions

WEAPON_ITEM_TYPE = 3  # DestinyItemType.Weapon
# Banshee's bounties, one per weapon type and named after it ("Hand Cannons"):
# their icons are the only weapon type pictures in the manifest.
GUNSMITH_ORDER = 'Gunsmith Order'


def definitions(mconn, table: str):
    # Every definition in a manifest table, parsed from its JSON, one at a
    # time so the whole table is never in memory.
    for (raw,) in mconn.execute(f'SELECT json FROM {table}'):
        yield json.loads(raw)


def name(obj) -> str | None:
    # A definition's displayProperties.name.
    return (obj.get('displayProperties') or {}).get('name')


def item_row(obj) -> tuple:
    # A DestinyInventoryItemDefinition row, in its column order: the fields
    # the app reads, as the manifest has them. plugCategoryIdentifier is ''
    # for a plug without one and NULL for an item that isn't a plug.
    props = obj.get('displayProperties') or {}
    inventory = obj.get('inventory') or {}
    plug = obj.get('plug')
    if isinstance(plug, dict):
        category = plug.get('plugCategoryIdentifier') or ''
    else:
        category = None
    return (
        obj['hash'],
        props.get('name'),
        props.get('description'),
        props.get('icon'),
        obj.get('itemType'),
        obj.get('itemTypeDisplayName'),
        inventory.get('tierType'),
        inventory.get('bucketTypeHash'),
        (obj.get('equippingBlock') or {}).get('ammoType'),
        obj.get('defaultDamageTypeHash'),
        obj.get('iconWatermark'),
        obj.get('collectibleHash'),
        json.dumps(obj.get('traitIds') or []),
        category,
    )


def replace_rows(conn, table: str, rows: list) -> None:
    # Replace every row of a table. Nothing points at the manifest tables, so
    # each is rewritten whole.
    conn.execute(f"DELETE FROM {table}")
    if rows:
        conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(rows[0]))})", rows)


def ingest_manifest(conn, manifest_path, version: str) -> bool:
    # Copy what the app uses from the manifest at manifest_path, unless this
    # version was already ingested. Reads the manifest read-only, one
    # definition at a time. Returns True when the tables were rewritten.
    if conn.execute("SELECT 1 FROM manifest_version WHERE version = ?", (version,)).fetchone():
        return False

    uri = f"file:{manifest_path}?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as mconn:
        # Weapons, plugs and Gunsmith Orders, and the weapons' sockets.
        item_rows, socket_rows, bucket_hashes, collectible_hashes = [], [], set(), set()
        for obj in definitions(mconn, 'DestinyInventoryItemDefinition'):
            is_weapon = obj.get('itemType') == WEAPON_ITEM_TYPE
            is_plug = isinstance(obj.get('plug'), dict)
            is_order = obj.get('itemTypeDisplayName') == GUNSMITH_ORDER
            if not (is_weapon or is_plug or is_order):
                continue
            item_rows.append(item_row(obj))
            if is_weapon:
                bucket_hashes.add((obj.get('inventory') or {}).get('bucketTypeHash'))
                collectible_hashes.add(obj.get('collectibleHash'))
                for idx, se in enumerate((obj.get('sockets') or {}).get('socketEntries') or []):
                    socket_rows.append(
                        (
                            obj['hash'],
                            idx,
                            se.get('singleInitialItemHash') or None,
                            se.get('randomizedPlugSetHash') or None,
                            se.get('reusablePlugSetHash') or None,
                        )
                    )

        # The plugs of the plug sets the sockets name. An entry whose plug
        # isn't a stored plug is skipped.
        plug_hashes = {r[0] for r in item_rows if r[-1] is not None}
        named_sets = {h for r in socket_rows for h in r[3:5] if h}
        plug_set_rows = []
        for o in definitions(mconn, 'DestinyPlugSetDefinition'):
            if o['hash'] not in named_sets:
                continue
            for position, p in enumerate(o.get('reusablePlugItems') or []):
                if p.get('plugItemHash') in plug_hashes:
                    can_roll = p.get('currentlyCanRoll')
                    if can_roll is not None:
                        can_roll = int(can_roll)
                    plug_set_rows.append((o['hash'], position, p['plugItemHash'], can_roll))

        bucket_rows = [
            (o['hash'], name(o), o.get('bucketOrder'))
            for o in definitions(mconn, 'DestinyInventoryBucketDefinition')
            if o['hash'] in bucket_hashes
        ]
        damage_rows = [
            (o['hash'], name(o), (o.get('displayProperties') or {}).get('icon'))
            for o in definitions(mconn, 'DestinyDamageTypeDefinition')
        ]
        # The weapons' Collections entries, for the source each names.
        collectible_rows = [
            (o['hash'], o.get('sourceString'))
            for o in definitions(mconn, 'DestinyCollectibleDefinition')
            if o['hash'] in collectible_hashes
        ]

        # Every activity, its type and the tiers of its difficulty.
        activity_rows = [
            (o['hash'], name(o), o.get('activityTypeHash'), o.get('difficultyTierCollectionHash'))
            for o in definitions(mconn, 'DestinyActivityDefinition')
        ]
        type_rows = [
            (o['hash'], name(o)) for o in definitions(mconn, 'DestinyActivityTypeDefinition')
        ]
        tier_rows = [
            (o['hash'], idx, name(t))
            for o in definitions(mconn, 'DestinyActivityDifficultyTierCollectionDefinition')
            for idx, t in enumerate(o.get('difficultyTiers') or [])
        ]

    with conn:
        replace_rows(conn, 'DestinyInventoryItemDefinition', item_rows)
        replace_rows(conn, 'DestinyItemSocketEntryDefinition', socket_rows)
        replace_rows(conn, 'DestinyItemSocketEntryPlugItemRandomizedDefinition', plug_set_rows)
        replace_rows(conn, 'DestinyInventoryBucketDefinition', bucket_rows)
        replace_rows(conn, 'DestinyDamageTypeDefinition', damage_rows)
        replace_rows(conn, 'DestinyActivityDefinition', activity_rows)
        replace_rows(conn, 'DestinyActivityTypeDefinition', type_rows)
        replace_rows(conn, 'DestinyActivityDifficultyTierDefinition', tier_rows)
        replace_rows(conn, 'DestinyCollectibleDefinition', collectible_rows)
        scored = versions.group(conn)
        conn.execute("INSERT INTO manifest_version VALUES (?)", (version,))
    weapons = sum(1 for r in item_rows if r[4] == WEAPON_ITEM_TYPE)
    print(
        f"  Database: ingested manifest {version} ({weapons:,} weapons as {scored:,} scored, "
        f"{len(plug_hashes):,} plugs, {len(activity_rows):,} activities)"
    )
    return True


def ingest_cached(conn) -> bool:
    # Make sure the manifest tables are filled without the network: when a
    # schema change emptied them, ingest the cached manifest download. False
    # when there is nothing stored or cached.
    if conn.execute("SELECT 1 FROM manifest_version").fetchone():
        return True
    cached = sorted(paths.MANIFEST_CACHE_DIR.glob('*.sqlite'))
    if not cached:
        return False
    return ingest_manifest(conn, cached[-1], cached[-1].stem)
