# The views the scan, the crawl and the scores read: each PGCR's category
# (v_pgcr_category), the activities a crawl fetches (v_crawl_activity), the
# weapon uses the votes fold (v_weapon_use), and how each weapon is used
# (v_weapon_score) and its perks score (v_roll_score) per side.
import math

import pytest
from conftest import (
    BARREL_A,
    BARREL_B,
    CUTTHROAT,
    DUNGEON,
    DUNGEON_MASTER,
    EMPTY_FEAT,
    FRAME,
    LAWLESS,
    MISSION,
    OLD_RAID,
    ORIGIN,
    ORIGIN_B,
    PATROL,
    PORTAL_OPS,
    RAID,
    RAID_EPIC,
    RAID_MASTER,
    TOKEN_LIMIT,
    TRAIT_A,
    TRAIT_B,
    TRAIT_C,
    TRAIT_SET,
    VANGUARD_ALERT,
    WEAPON,
    WEAPON_ADEPT,
    add_pgcr,
    add_use,
    add_weapon,
)

from extract import votes

CATEGORIES = [
    # (activity, modes, isPrivate, activityDifficultyTier, skulls, category)
    (RAID, [], 0, 1, [EMPTY_FEAT, CUTTHROAT, EMPTY_FEAT], 'raid_master'),  # Cutthroat
    (RAID, [], 0, 1, [TOKEN_LIMIT, EMPTY_FEAT, EMPTY_FEAT], 'raid'),
    (RAID_MASTER, [4, 7], 0, None, [], 'raid_master'),
    (RAID_EPIC, [], 0, None, [], 'raid_master'),
    (PORTAL_OPS, [3, 18, 7], 0, 2, [], 'gm'),
    (PORTAL_OPS, [3, 18, 7], 0, 3, [], 'gm'),
    (VANGUARD_ALERT, [3, 18, 7], 0, 0, [], 'gm'),
    (VANGUARD_ALERT, [3, 18, 7], 0, -1, [], 'gm'),  # no tier recorded: it only has Grandmaster
    (MISSION, [3, 18, 7], 0, 2, [], 'portal'),  # Grandmaster, but not a Vanguard Alert
    (LAWLESS, [7, 93], 0, 2, [], None),
    (DUNGEON_MASTER, [82, 7], 0, None, [], 'dungeon_master'),
    (RAID, [4, 7], 0, 0, [], 'raid'),
    (DUNGEON, [82, 7], 0, None, [], 'dungeon'),
    (PORTAL_OPS, [3, 18, 7], 0, 1, [], 'portal'),
    (0, [84, 5], 0, None, [], 'trials'),
    (0, [37, 69, 5], 0, None, [], 'competitive'),
    (0, [63, 7], 0, None, [], 'gambit'),
    (0, [19, 5], 0, None, [], 'quickplay'),
    (0, [69, 5], 1, None, [], None),
    (0, [5, 94], 0, None, [], None),
    (PATROL, [6, 7], 0, None, [], None),
]


@pytest.mark.parametrize('activity, modes, private, tier, skulls, category', CATEGORIES)
def test_pgcr_category(conn, activity, modes, private, tier, skulls, category):
    add_pgcr(conn, 1, activity, modes, private, tier, skulls)
    assert conn.execute("SELECT category FROM v_pgcr_category").fetchone()[0] == category


def test_weapon_use_counts_finished_matched_uses_of_kept_pgcrs(conn):
    add_pgcr(conn, 1, RAID_MASTER)
    add_use(conn, 1, 'a', {3: TRAIT_A}, item_hash=WEAPON_ADEPT)  # counts, as the base weapon
    add_use(conn, 1, 'b', {3: TRAIT_A}, completed=0)  # left before the end
    add_use(conn, 1, 'c', {}, matched=False)  # no longer equipped
    add_pgcr(conn, 2, PATROL, [6, 7])
    add_use(conn, 2, 'a', {3: TRAIT_A})  # not a category the scan keeps
    rows = conn.execute(
        "SELECT instanceId, characterId, weapon, side, weight FROM v_weapon_use"
    ).fetchall()
    assert [tuple(r) for r in rows] == [(1, 'a', 'Test Cannon', 'pve', 32)]


def test_a_raid_clear_not_made_from_the_start_votes_a_third(conn):
    # Raid clears (weight 4): a fresh run joined at the start counts in full;
    # a run from a checkpoint, or one joined 45 seconds in, counts a third; a
    # report that doesn't say counts in full, and so does a copy with a clear
    # of each kind. A Portal run from a checkpoint isn't a raid: in full.
    runs = [
        (1, 'full', 1, 0),
        (2, 'checkpoint', 0, 0),
        (3, 'late', 1, 45),
        (4, 'unknown', None, 0),
        (5, 'both', 0, 0),
        (6, 'both', 1, 3),
    ]
    for instance, copy, started, start in runs:
        add_pgcr(conn, instance, RAID, [4, 7], tier=0, started=started)
        add_use(conn, instance, f'c{instance}', {3: TRAIT_A}, copy_id=copy, start_seconds=start)
    add_pgcr(conn, 7, PORTAL_OPS, [3, 18, 7], tier=1, started=0)
    add_use(conn, 7, 'c7', {3: TRAIT_A}, copy_id='portal')
    votes.fold(conn)
    weights = dict(conn.execute("SELECT itemInstanceId, round(weight, 4) FROM v_roll_unit"))
    assert weights == {
        'full': 4,
        'checkpoint': 1.3333,
        'late': 1.3333,
        'unknown': 4,
        'both': 4,
        'portal': 1,
    }


def test_crawl_activities_are_those_that_can_be_categorized(conn):
    # By the best category a PGCR can get. Hard: a Master or Epic raid, a raid
    # with a Custom tier (feats), a Master dungeon, a Grandmaster Vanguard
    # Alert, a Nightfall with Grandmaster tiers. Basic: a raid without either,
    # a plain dungeon. Not another mission that can be played at Grandmaster
    # (the crawl knows strikes by their modes), nor a patrol or the Lawless
    # Frontier.
    assert dict(conn.execute("SELECT hash, category FROM v_crawl_activity")) == {
        RAID: 'raid_master',
        RAID_MASTER: 'raid_master',
        RAID_EPIC: 'raid_master',
        DUNGEON_MASTER: 'dungeon_master',
        VANGUARD_ALERT: 'gm',
        PORTAL_OPS: 'gm',
        OLD_RAID: 'raid',
        DUNGEON: 'dungeon',
    }


def test_grandmaster_activities_offer_only_grandmaster_tiers(conn):
    assert [r[0] for r in conn.execute("SELECT hash FROM v_grandmaster_activity")] == [
        VANGUARD_ALERT
    ]


def credibility(n_eff):
    # A group's credibility, with setting's credibility_k.
    return n_eff / (n_eff + 30)


def hard_part(n_hard, n_normal):
    # Hard content's part of a merged score: setting's hard_weight times its
    # credibility, against the rest times normal's.
    hard, normal = 0.75 * credibility(n_hard), 0.25 * credibility(n_normal)
    return hard / (hard + normal)


def wilson(p, n, z=1.96):
    mid, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((mid - half) / (1 + z * z / n), 3), round((mid + half) / (1 + z * z / n), 3)


def test_roll_score_merges_each_sides_hard_and_normal_groups(conn):
    # A second trait column, so a copy's traits make a pair.
    conn.execute(
        "INSERT INTO DestinyItemSocketEntryDefinition VALUES (?, 4, NULL, ?, NULL)",
        (WEAPON, TRAIT_SET),
    )
    roll_a = {1: BARREL_A, 3: TRAIT_A, 4: TRAIT_B, 8: ORIGIN}
    add_pgcr(conn, 1, RAID_MASTER)  # hard, weight 32
    add_use(conn, 1, 'a', roll_a, copy_id='a1')
    add_pgcr(conn, 2, RAID)  # normal, weight 4: a's copy again, which votes in both groups
    add_use(conn, 2, 'a', roll_a, copy_id='a1')
    add_use(conn, 2, 'b', {1: BARREL_B, 3: TRAIT_C, 4: TRAIT_A, 8: ORIGIN_B})
    add_pgcr(conn, 3, 0, [84, 5])  # Trials: PvP's hard group, weight 8
    add_use(conn, 3, 'c', {0: FRAME, 1: BARREL_B, 3: TRAIT_A, 4: TRAIT_B, 8: ORIGIN})
    votes.fold(conn)

    # Each group scores its own votes, a copy once per group at its weight
    # there; n_eff for the normal group: 8² / (4² + 4²).
    groups = [
        tuple(r)
        for r in conn.execute(
            "SELECT side, tier, perk, players, votes, share, n_eff FROM v_group_score "
            "WHERE kind = 'barrel' ORDER BY side, tier, perk"
        )
    ]
    assert groups == [
        ('pve', 'hard', 'Arrowhead Brake', 1, 32, 1.0, 1.0),
        ('pve', 'normal', 'Arrowhead Brake', 1, 4, 0.5, 2.0),
        ('pve', 'normal', 'Smallbore', 1, 4, 0.5, 2.0),
        ('pvp', 'hard', 'Smallbore', 1, 8, 1.0, 1.0),
    ]

    # The merge: hard's part shrinks with its single vote's credibility.
    rows = {
        side: [
            tuple(r)
            for r in conn.execute(
                f"SELECT kind, rank, perk, share, hard_share, normal_share, hard_part, n_eff, "
                f"confidence FROM v_{side}_roll_score"
            )
        ]
        for side in ('pve', 'pvp')
    }
    a = hard_part(1, 2)
    n_eff = 1 / (a * a / 1 + (1 - a) ** 2 / 2)
    first, second = round(a + (1 - a) / 2, 3), round((1 - a) / 2, 3)
    pve = [
        (kind, rank, perk, share, hard, normal, round(a, 3), round(n_eff, 1), 'very low')
        for kind, (top, other) in (
            ('barrel', ('Arrowhead Brake', 'Smallbore')),
            ('traits', ('Rampage + Kill Clip', 'Outlaw + Rampage')),
            ('trait1', ('Rampage', 'Outlaw')),
            ('trait2', ('Kill Clip', 'Rampage')),
            ('origin', ('Veist Stinger', 'Nano Mania')),
        )
        for rank, perk, share, hard, normal in (
            (1, top, first, 1.0, 0.5),
            (2, other, second, 0.0, 0.5),
        )
    ]
    assert rows['pve'] == pve
    # PvP has only its hard group: it is the whole score.
    assert rows['pvp'] == [
        ('barrel', 1, 'Smallbore', 1.0, 1.0, None, 1.0, 1.0, 'very low'),
        ('traits', 1, 'Rampage + Kill Clip', 1.0, 1.0, None, 1.0, 1.0, 'very low'),
        ('trait1', 1, 'Rampage', 1.0, 1.0, None, 1.0, 1.0, 'very low'),
        ('trait2', 1, 'Kill Clip', 1.0, 1.0, None, 1.0, 1.0, 'very low'),
        ('origin', 1, 'Veist Stinger', 1.0, 1.0, None, 1.0, 1.0, 'very low'),
    ]
    # The 95% Wilson interval, with the merged n_eff as its n.
    low_high = conn.execute(
        "SELECT low, high FROM v_pve_roll_score WHERE perk = 'Arrowhead Brake'"
    ).fetchone()
    assert tuple(low_high) == wilson(a + (1 - a) / 2, n_eff)


def test_weapon_score_flags_weapons_hard_content_decides(conn):
    # One Master raid copy against 40 Portal copies: one hard vote is worth
    # too little credibility to carry hard content's weight.
    add_pgcr(conn, 1, RAID_MASTER)
    add_use(conn, 1, 'master-0', {1: BARREL_A})
    for i in range(40):
        add_pgcr(conn, 100 + i, PORTAL_OPS, [3, 18, 7], tier=1)
        add_use(conn, 100 + i, f'portal-{i}', {1: BARREL_B})
    votes.fold(conn)

    def score():
        return tuple(
            conn.execute(
                "SELECT weapon_rank, players, active_players, hard_copies, normal_copies, "
                "hard_n_eff, normal_n_eff, hard_weight, hard, stale "
                "FROM v_weapon_score WHERE side = 'pve'"
            ).fetchone()
        )

    assert score() == (1, 41, 41, 1, 40, 1.0, 40.0, round(hard_part(1, 40), 3), 0, 0)
    # 20 Master raid copies: now hard content holds most of the scores.
    for i in range(1, 20):
        add_pgcr(conn, 1 + i, RAID_MASTER)
        add_use(conn, 1 + i, f'master-{i}', {1: BARREL_A})
    votes.fold(conn)
    assert score() == (1, 60, 60, 20, 40, 20.0, 40.0, round(hard_part(20, 40), 3), 1, 0)


def test_weapon_rank_leans_toward_hard_content(conn):
    # A weapon with one Master raid copy outranks one with 30 Portal copies:
    # its share of the side's hard votes counts for hard_weight.
    other = 102
    add_weapon(conn, other, 'Other Gun', {})
    add_pgcr(conn, 1, RAID_MASTER)
    add_use(conn, 1, 'master', {1: BARREL_A})
    for i in range(30):
        add_pgcr(conn, 100 + i, PORTAL_OPS, [3, 18, 7], tier=1)
        add_use(conn, 100 + i, f'portal-{i}', {1: BARREL_B}, item_hash=other)
    votes.fold(conn)
    ranks = dict(conn.execute("SELECT weapon, weapon_rank FROM v_weapon_score"))
    assert ranks == {'Test Cannon': 1, 'Other Gun': 2}
