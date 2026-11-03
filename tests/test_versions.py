# Which weapon each version is scored as (extract/versions.py): versions of a
# family split by trait pool, Adept-style versions stay with their base, a
# fixed version alone never splits a family, and split pools are named by
# source, else by season, numbered when names would repeat.
import pytest
from conftest import add_weapon

from extract import versions

# Trait pools: the perks of each of the two trait columns. The same name in
# another plug set is another hash, as with an enhanced perk.
RAID_POOL = (['Rampage', 'Kill Clip'], ['Outlaw', 'Frenzy'])
REISSUE_POOL = (['Rampage', 'Demolitionist'], ['Outlaw', 'Firefly'])
ADEPT_POOL = (['Rampage', 'Kill Clip', 'Explosive Payload'], ['Outlaw', 'Frenzy'])
FIXED = (['Rampage'], ['Outlaw'])
KINGS_FALL = 'Source: "King\'s Fall" Raid'
GARDEN = 'Source: "Garden of Salvation" Raid'
CROTA = 'Source: "Crota\'s End" Raid'
NO_SOURCE = 'Random Perks: This item cannot be reacquired from Collections.'


def add_version(conn, item_hash, name, pool, release, source):
    # A version whose trait columns (sockets 3 and 4) roll pool, each from a
    # plug set of its own.
    sockets = {}
    for column, perks in enumerate(pool):
        plug_set = item_hash * 10 + column
        for position, perk in enumerate(perks):
            plug = plug_set * 10 + position
            conn.execute(
                f"INSERT INTO DestinyInventoryItemDefinition VALUES ({', '.join('?' * 14)})",
                (plug, perk, '', '', 19, 'Trait', 2, None, None, None, None, None, '[]', 'frames'),
            )
            conn.execute(
                "INSERT INTO DestinyItemSocketEntryPlugItemRandomizedDefinition "
                "VALUES (?, ?, ?, 1)",
                (plug_set, position, plug),
            )
        sockets[3 + column] = plug_set
    add_weapon(conn, item_hash, name, sockets, release, source)


@pytest.mark.parametrize(
    'version_rows, expected',
    [
        pytest.param(
            [
                (1001, "Zaouli's Bane", RAID_POOL, 'releases.v620.season', KINGS_FALL),
                (1002, "Zaouli's Bane (Harrowed)", RAID_POOL, 'releases.v620.season', KINGS_FALL),
                (1003, "Zaouli's Bane", REISSUE_POOL, 'releases.v970.core', 'Source: Pantheon'),
                (1004, "Zaouli's Bane", REISSUE_POOL, 'releases.v970.core', None),
            ],
            {
                1001: "Zaouli's Bane (King's Fall)",
                1002: "Zaouli's Bane (King's Fall)",
                1003: "Zaouli's Bane (Pantheon)",
                1004: "Zaouli's Bane (Pantheon)",
            },
            id='a reissue with its own pool splits off, named by source',
        ),
        pytest.param(
            [
                (2001, 'Abyss Defiant', RAID_POOL, 'releases.v730.season', CROTA),
                (2002, 'Abyss Defiant (Adept)', ADEPT_POOL, 'releases.v730.season', CROTA),
            ],
            {2001: 'Abyss Defiant', 2002: 'Abyss Defiant'},
            id='an Adept a perk off its base stays with it',
        ),
        pytest.param(
            [
                (3001, 'Accrued Redemption', RAID_POOL, 'releases.v460.season', GARDEN),
                (3002, 'Accrued Redemption', REISSUE_POOL, 'releases.v810.season', GARDEN),
            ],
            {
                3001: 'Accrued Redemption (Shadowkeep)',
                3002: 'Accrued Redemption (Episode: Revenant)',
            },
            id='pools from one source are named by season',
        ),
        pytest.param(
            [
                (4001, 'Gun', RAID_POOL, 'releases.v400.season', NO_SOURCE),
                (4002, 'Gun', REISSUE_POOL, 'releases.v500.season', 'Source: Pantheon'),
            ],
            {4001: 'Gun (Forsaken)', 4002: 'Gun (Beyond Light)'},
            id='a pool without a real source names every pool by season',
        ),
        pytest.param(
            [
                (5001, 'Horror Story', RAID_POOL, 'releases.v400.season', None),
                (5002, 'Horror Story', REISSUE_POOL, 'releases.v400.season', None),
            ],
            {5001: 'Horror Story (Forsaken)', 5002: 'Horror Story (Forsaken 2)'},
            id='two pools of one season are numbered',
        ),
        pytest.param(
            [
                (6001, 'Recluse', RAID_POOL, 'releases.v400.season', 'Source: Crucible'),
                (6002, 'Recluse', FIXED, 'releases.v410.season', 'Source: Quest'),
            ],
            {6001: 'Recluse', 6002: 'Recluse'},
            id='a fixed version never splits a family on its own',
        ),
        pytest.param(
            [
                (7001, 'Luna', RAID_POOL, 'releases.v400.season', 'Source: Crucible'),
                (7002, 'Luna', REISSUE_POOL, 'releases.v500.season', 'Source: Gambit'),
                (7003, 'Luna', FIXED, 'releases.v410.season', 'Source: Quest'),
            ],
            {7001: 'Luna (Crucible)', 7002: 'Luna (Gambit)', 7003: 'Luna (Quest)'},
            id='a fixed version stands alone where its family splits',
        ),
        pytest.param(
            [
                (8001, 'Drang', RAID_POOL, 'releases.v400.season', 'Source: "Baroque"'),
                (8002, 'Drang', REISSUE_POOL, 'releases.v500.season', 'Source: Gambit'),
                (8003, 'Drang (Baroque)', RAID_POOL, 'releases.v500.season', 'Source: Lost Sector'),
            ],
            {8001: 'Drang (Baroque 2)', 8002: 'Drang (Gambit)', 8003: 'Drang (Baroque)'},
            id="a name another family has is numbered",
        ),
    ],
)
def test_versions_group_by_trait_pool(conn, version_rows, expected):
    for row in version_rows:
        add_version(conn, *row)
    versions.group(conn)
    marks = ', '.join('?' * len(expected))
    names = dict(
        conn.execute(
            f"SELECT item_hash, weapon FROM weapon_version WHERE item_hash IN ({marks})",
            list(expected),
        )
    )
    assert names == expected


@pytest.mark.parametrize(
    'source, expected',
    [
        (KINGS_FALL, "King's Fall"),
        ('Source: "Crown of Sorrow."', 'Crown of Sorrow'),
        ('Source: Pantheon', 'Pantheon'),
        ('Solo Ops', 'Solo Ops'),
        ('Source: Complete Crucible matches and earn rank-up packages from Lord Shaxx.', ''),
    ],
)
def test_label_names_a_pool_by_its_source(source, expected):
    assert versions.label(source) == expected
