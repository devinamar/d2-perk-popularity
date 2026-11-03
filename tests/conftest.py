# Shared fixtures: an in-memory db holding a few definitions (one weapon in two
# versions, its perks, and an activity of each kind), and helpers that store
# PGCRs and weapon uses, so tests need no network or real manifest.
import json

import pytest

from db import connection

# Fake hashes. Each plug has a real plugCategoryIdentifier, since v_plug sorts
# plugs into perk kinds by category.
WEAPON = 100  # "Test Cannon"
WEAPON_ADEPT = 101  # "Test Cannon (Adept)"
FRAME = 200  # "Adaptive Frame", the intrinsic in socket 0
BARREL_A, BARREL_B = 201, 202  # socket 1
TRAIT_A, TRAIT_B, TRAIT_C = 301, 302, 303  # socket 3
ORIGIN = 401  # socket 8, its only perk
ORIGIN_B = 402  # an origin socket 8's set doesn't list
BARREL_SET, TRAIT_SET, ORIGIN_SET = 901, 902, 903
KINETIC = 1498876634  # the Kinetic Weapons bucket
KINETIC_DAMAGE = 3373582085

PLUGS = {
    FRAME: ('Adaptive Frame', 'intrinsics'),
    BARREL_A: ('Arrowhead Brake', 'barrels'),
    BARREL_B: ('Smallbore', 'barrels'),
    TRAIT_A: ('Rampage', 'frames'),
    TRAIT_B: ('Kill Clip', 'frames'),
    TRAIT_C: ('Outlaw', 'frames'),
    ORIGIN: ('Veist Stinger', 'origins'),
    ORIGIN_B: ('Nano Mania', 'origins'),
}
PLUG_SETS = {
    BARREL_SET: [BARREL_A, BARREL_B],
    TRAIT_SET: [TRAIT_A, TRAIT_B, TRAIT_C],
    ORIGIN_SET: [ORIGIN],
}

# Activities, their types and tiers, named as the live manifest names them.
TYPES = {
    11: 'Raid',
    12: 'Dungeon',
    13: 'Nightfall',
    14: 'Explore',
    15: 'Mission',
    16: 'The Lawless Frontier',
}
RAID_TYPE, DUNGEON_TYPE, NIGHTFALL_TYPE, EXPLORE_TYPE, MISSION_TYPE, LAWLESS_TYPE = TYPES
(
    RAID,
    RAID_MASTER,
    RAID_EPIC,
    DUNGEON,
    DUNGEON_MASTER,
    PORTAL_OPS,
    PATROL,
    MISSION,
    LAWLESS,
    OLD_RAID,
    VANGUARD_ALERT,
) = range(21, 32)
RAID_TIERS, PORTAL_TIERS, GM_TIERS = 41, 42, 43
ACTIVITIES = [
    (VANGUARD_ALERT, 'Exodus Crash: Customize', MISSION_TYPE, GM_TIERS),
    (RAID, 'Test Raid: Standard', RAID_TYPE, RAID_TIERS),
    (OLD_RAID, 'Old Raid: Standard', RAID_TYPE, None),
    (RAID_MASTER, 'Old Raid: Master', RAID_TYPE, None),
    (RAID_EPIC, 'Test Raid (Epic): Standard', RAID_TYPE, None),
    (DUNGEON, 'Test Dungeon: Standard', DUNGEON_TYPE, None),
    (DUNGEON_MASTER, 'Test Dungeon: Master', DUNGEON_TYPE, None),
    (PORTAL_OPS, 'Fireteam Ops (Epic)', NIGHTFALL_TYPE, PORTAL_TIERS),
    (PATROL, 'The Pale Heart', EXPLORE_TYPE, None),
    (MISSION, 'Ultimate Conquest: Lightblade: Customize', MISSION_TYPE, PORTAL_TIERS),
    (LAWLESS, 'Invasion', LAWLESS_TYPE, PORTAL_TIERS),
]
TIERS = [
    (RAID_TIERS, 0, 'Normal'),
    (RAID_TIERS, 1, 'Custom'),
    (PORTAL_TIERS, 0, 'Expert'),
    (PORTAL_TIERS, 1, 'Master'),
    (PORTAL_TIERS, 2, 'Grandmaster'),
    (PORTAL_TIERS, 3, 'Ultimate'),
    (GM_TIERS, 0, 'Grandmaster'),
    (GM_TIERS, 1, 'Ultimate'),
]
# Feats as a PGCR lists them, by skullIdentifierHash.
CUTTHROAT = 2673088233  # Feat: Cutthroat Combat
TOKEN_LIMIT = 3123804375  # Feat: Token Limit
EMPTY_FEAT = 790421403


@pytest.fixture
def conn():
    # A new in-memory db with the definitions above.
    c = connection.open_db(':memory:')
    items = [
        (h, name, '', f'/p{h}.png', 19, 'Trait', 2, None, None, None, None, None, '[]', category)
        for h, (name, category) in PLUGS.items()
    ]
    for h, name in ((WEAPON, 'Test Cannon'), (WEAPON_ADEPT, 'Test Cannon (Adept)')):
        items.append(
            (h, name, '', f'/w{h}.png', 3, 'Hand Cannon', 5, KINETIC, 1, KINETIC_DAMAGE, '')
            + (None, '[]', None)
        )
    c.executemany(
        f"INSERT INTO DestinyInventoryItemDefinition VALUES ({', '.join('?' * 14)})", items
    )
    c.executemany(
        "INSERT INTO DestinyItemSocketEntryDefinition VALUES (?, ?, ?, ?, ?)",
        [
            row
            for w in (WEAPON, WEAPON_ADEPT)
            for row in (
                (w, 0, FRAME, None, None),
                (w, 1, None, BARREL_SET, None),
                (w, 3, None, TRAIT_SET, None),
                (w, 8, None, None, ORIGIN_SET),
            )
        ],
    )
    c.executemany(
        "INSERT INTO DestinyItemSocketEntryPlugItemRandomizedDefinition VALUES (?, ?, ?, 1)",
        [(s, i, p) for s, plugs in PLUG_SETS.items() for i, p in enumerate(plugs)],
    )
    c.execute(
        "INSERT INTO DestinyInventoryBucketDefinition VALUES (?, 'Kinetic Weapons', 1)", (KINETIC,)
    )
    c.execute(
        "INSERT INTO DestinyDamageTypeDefinition VALUES (?, 'Kinetic', '/k.png')", (KINETIC_DAMAGE,)
    )
    c.executemany("INSERT INTO DestinyActivityTypeDefinition VALUES (?, ?)", TYPES.items())
    c.executemany("INSERT INTO DestinyActivityDefinition VALUES (?, ?, ?, ?)", ACTIVITIES)
    c.executemany("INSERT INTO DestinyActivityDifficultyTierDefinition VALUES (?, ?, ?)", TIERS)
    yield c
    c.close()


def add_weapon(conn, item_hash, name, sockets, release=None, source=None):
    # Store another version of a weapon: its definition, its random sockets
    # ({socketIndex: plug set}), its release trait, and, given a source, its
    # Collections entry (a collectible numbered after it) naming that source.
    collectible = None
    if source is not None:
        collectible = item_hash + 50000
        conn.execute(
            "INSERT INTO DestinyCollectibleDefinition VALUES (?, ?)", (collectible, source)
        )
    traits = json.dumps([release] if release else [])
    conn.execute(
        f"INSERT INTO DestinyInventoryItemDefinition VALUES ({', '.join('?' * 14)})",
        (item_hash, name, '', f'/w{item_hash}.png', 3, 'Hand Cannon', 5, KINETIC, 1)
        + (KINETIC_DAMAGE, '', collectible, traits, None),
    )
    conn.executemany(
        "INSERT INTO DestinyItemSocketEntryDefinition VALUES (?, ?, NULL, ?, NULL)",
        [(item_hash, idx, plug_set) for idx, plug_set in sockets.items()],
    )


def add_pgcr(
    conn,
    instance_id,
    activity=0,
    modes=(),
    private=0,
    tier=None,
    skulls=(),
    period='2099-01-01T00:00:00Z',
    started=None,
):
    # Store a PGCR's header: what was played, how, when, and whether the run
    # started from the beginning (started: 1, 0 for a checkpoint, None).
    conn.execute(
        "INSERT INTO DestinyPostGameCarnageReportData VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            instance_id,
            period,
            activity,
            activity,
            (list(modes) or [0])[0],
            json.dumps(list(modes)),
            private,
            tier,
            json.dumps(list(skulls)),
            started,
        ),
    )


def add_use(
    conn,
    instance_id,
    character_id,
    plugs,
    item_hash=WEAPON,
    completed=1,
    matched=True,
    copy_id=None,
    start_seconds=0,
):
    # Store a character's entry in a stored PGCR, joined start_seconds in, and
    # one weapon they used there; when matched, the copy they had equipped
    # (its own, unless copy_id names one used before), with plugs
    # ({socketIndex: plugHash}).
    if not matched:
        copy_id = None
    elif copy_id is None:
        copy_id = f'copy-{instance_id}-{character_id}'
    conn.execute(
        "INSERT INTO DestinyPostGameCarnageReportEntry VALUES (?, ?, ?, 3, ?, ?)",
        (instance_id, character_id, f'player-{character_id}', completed, start_seconds),
    )
    conn.execute(
        "INSERT INTO DestinyHistoricalWeaponStats VALUES (?, ?, ?, 10, ?)",
        (instance_id, character_id, item_hash, copy_id),
    )
    if copy_id:
        conn.executemany(
            "INSERT OR REPLACE INTO DestinyItemSocketsComponent VALUES (?, ?, ?)",
            [(copy_id, idx, plug) for idx, plug in plugs.items()],
        )
