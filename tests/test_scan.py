# The PGCR scan and crawl against a stand-in API: finding the newest PGCR,
# reading a report, what a scan keeps and matches, and what a crawl reads,
# fetches and keeps.
from conftest import (
    BARREL_A,
    CUTTHROAT,
    DUNGEON_MASTER,
    FRAME,
    OLD_RAID,
    PATROL,
    RAID,
    RAID_MASTER,
    TRAIT_A,
    WEAPON,
    WEAPON_ADEPT,
    add_pgcr,
    add_use,
)

from extract import scan, votes
from sources.bungie.api import BungieError


def pgcr(instance_id, activity, modes, players):
    # A PGCR as Bungie sends it, trimmed to what the scan reads. players are
    # (membershipId, characterId, [weapon hashes]); each finished, cross-saved
    # from Xbox (1) to Steam (3), with 12 kills per weapon.
    return {
        'period': '2099-01-01T00:00:00Z',
        'activityDifficultyTier': 1,
        'selectedSkullHashes': [],
        'activityDetails': {
            'referenceId': activity,
            'directorActivityHash': activity,
            'instanceId': str(instance_id),
            'mode': modes[0],
            'modes': modes,
            'isPrivate': False,
        },
        'entries': [
            {
                'player': {
                    'destinyUserInfo': {
                        'membershipId': membership_id,
                        'membershipType': 1,
                        'crossSaveOverride': 3,
                    }
                },
                'characterId': character_id,
                'values': {'completed': {'basic': {'value': 1.0, 'displayValue': 'Yes'}}},
                'extended': {
                    'weapons': [
                        {
                            'referenceId': h,
                            'values': {'uniqueWeaponKills': {'basic': {'value': 12.0}}},
                        }
                        for h in weapons
                    ]
                },
            }
            for membership_id, character_id, weapons in players
        ],
    }


def profile(character_id, item_hash, copy_id, plugs):
    # A profile's equipment (component 205) and sockets (305) for one equipped
    # copy, plugs being its sockets' plugs in order (None for an empty one).
    return {
        'characterEquipment': {
            'data': {character_id: {'items': [{'itemHash': item_hash, 'itemInstanceId': copy_id}]}}
        },
        'itemComponents': {
            'sockets': {
                'data': {copy_id: {'sockets': [{'plugHash': p} if p else {} for p in plugs]}}
            }
        },
    }


def activity(
    instance_id, activity_hash, modes, completed=1, period='2099-01-01T00:00:00Z', private=False
):
    # A history entry as Bungie sends it, trimmed to what the crawl reads.
    return {
        'period': period,
        'activityDetails': {
            'instanceId': str(instance_id),
            'referenceId': activity_hash,
            'modes': list(modes),
            'isPrivate': private,
        },
        'values': {'completed': {'basic': {'value': float(completed)}}},
    }


class FakeAPI:
    # Answers from pgcrs ({id: PGCR}), profiles ({membershipId: loadout
    # profile}; every player has one character, 'c-<membershipId>') and
    # histories ({membershipId: [activity], newest first}, its character last
    # played as last_played says, else now); anything else raises as Bungie
    # does. Records the PGCRs, loadouts and history pages read.
    def __init__(self, pgcrs, profiles, histories=None, last_played=None):
        self.pgcrs, self.profiles, self.histories = pgcrs, profiles, histories or {}
        self.last_played = last_played or {}
        self.pgcr_reads, self.profile_reads, self.history_reads = [], [], []
        self.membership_reads = []

    def get_memberships(self, membership_id):
        # Every account here is on Steam, with no cross save.
        self.membership_reads.append(membership_id)
        return {
            'destinyMemberships': [
                {'membershipId': membership_id, 'membershipType': 3, 'crossSaveOverride': 0}
            ]
        }

    def get_pgcr(self, instance_id):
        self.pgcr_reads.append(instance_id)
        if instance_id not in self.pgcrs:
            raise BungieError(1653, 'DestinyPGCRNotFound')
        return self.pgcrs[instance_id]

    def get_profile(self, membership_type, membership_id, components):
        assert membership_type == 3
        if components == [100]:
            return {'profile': {'data': {'characterIds': [f'c-{membership_id}']}}}
        if components == [200]:
            played = self.last_played.get(membership_id, votes.ago(0))
            return {'characters': {'data': {f'c-{membership_id}': {'dateLastPlayed': played}}}}
        assert components == scan.LOADOUT_COMPONENTS
        self.profile_reads.append(membership_id)
        if membership_id not in self.profiles:
            raise BungieError(1665, 'DestinyPrivacyRestriction')
        return self.profiles[membership_id]

    def get_activity_history(
        self, membership_type, membership_id, character_id, count=1, mode=None, page=0
    ):
        # The crawl reads every mode.
        assert (membership_type, character_id, mode) == (3, f'c-{membership_id}', None)
        self.history_reads.append((membership_id, page))
        found = self.histories.get(membership_id, [])
        return {'activities': found[page * count : (page + 1) * count]}


def test_find_head_steps_over_gaps():
    have = set(range(1000, 50_001)) - {1001, 1002, 30_000, 30_001}
    assert scan.find_head(have.__contains__, 1000) == 50_000


def test_pgcr_rows():
    # A raid run from a checkpoint, its player joining 45 seconds in.
    report = pgcr(7, RAID, [4, 7], [('m1', 'c1', [WEAPON])])
    report['selectedSkullHashes'] = [CUTTHROAT]
    report['activityWasStartedFromBeginning'] = False
    report['entries'][0]['values']['startSeconds'] = {'basic': {'value': 45.0}}
    assert scan.pgcr_header(report) == (
        7,
        '2099-01-01T00:00:00Z',
        RAID,
        RAID,
        4,
        '[4, 7]',
        0,
        1,
        f'[{CUTTHROAT}]',
        0,
    )
    assert scan.pgcr_players(report) == ([(7, 'c1', 'm1', 3, 1, 45)], [(7, 'c1', WEAPON, 12)])


def test_a_player_whose_pgcr_gives_no_membership_type_is_looked_up():
    # A few PGCR entries give membershipType 0, which the profile endpoint
    # refuses; the account's memberships say which to use.
    api = FakeAPI(pgcrs={}, profiles={'m1': profile('c1', WEAPON, 'copy1', [FRAME])})
    copy = ('copy1', [(0, FRAME)])
    assert scan.fetch_loadout(api, 0, 'm1') == {'c1': {WEAPON: copy}, scan.ANYWHERE: {WEAPON: copy}}
    assert api.membership_reads == ['m1']
    scan.fetch_loadout(api, 3, 'm1')  # one it gave isn't looked up
    assert api.membership_reads == ['m1']


def test_a_use_matches_the_only_copy_the_profile_shows():
    # A weapon used on one character may be on another by the time the
    # profile is read, or in a vault its player makes public: it matches the
    # one copy of that version the profile shows. With two, either could be
    # the one used, so only a copy equipped on that character matches.
    other, third = 102, 103

    def items(*copies):
        return {'items': [{'itemHash': h, 'itemInstanceId': i} for h, i in copies]}

    found = scan.loadout(
        {
            'characterEquipment': {
                'data': {
                    'c1': items((WEAPON, 'w-c1')),
                    'c2': items((WEAPON_ADEPT, 'adept-c2'), (other, 'other-c2')),
                }
            },
            'characterInventories': {'data': {'c2': {'items': [{'itemHash': 999}]}}},
            'profileInventory': {'data': items((other, 'other-vault'), (third, 'third-vault'))},
            'itemComponents': {
                'sockets': {'data': {'adept-c2': {'sockets': [{'plugHash': FRAME}, {}]}}}
            },
        }
    )

    def match(character_id, item_hash):
        copy = scan.matching_copy(found, character_id, item_hash)
        return copy and copy[0]

    assert match('c1', WEAPON) == 'w-c1'  # equipped on that character
    assert match('c2', WEAPON) == 'w-c1'  # moved to another
    assert scan.matching_copy(found, 'c1', WEAPON_ADEPT) == ('adept-c2', [(0, FRAME)])
    assert match('c1', third) == 'third-vault'  # in a public vault
    assert match('c2', other) == 'other-c2'  # two copies: the one equipped there
    assert match('c1', other) is None  # two copies, neither on c1
    assert match('c1', 999) is None  # not instanced
    assert scan.loadout({}) == {}  # a profile that shows nothing


def test_scan_keeps_up_to_the_cap_and_matches_equipped_copies(conn, monkeypatch):
    monkeypatch.setattr(scan, 'BATCH', 2)
    raid = pgcr(
        5,
        RAID,
        [4, 7],
        [('m1', 'c1', [WEAPON, WEAPON_ADEPT]), ('m2', 'c2', [WEAPON]), ('m5', 'c5', [WEAPON])],
    )
    raid['entries'][2]['values']['completed']['basic']['value'] = 0.0  # m5 left early
    # The newest raid: its only player left early, so it isn't kept and the
    # raid cap is still free for the next one.
    abandoned = pgcr(6, RAID, [4, 7], [('m6', 'c6', [WEAPON])])
    abandoned['entries'][0]['values']['completed']['basic']['value'] = 0.0
    api = FakeAPI(
        pgcrs={
            6: abandoned,
            5: raid,
            4: pgcr(4, RAID, [4, 7], [('m3', 'c3', [WEAPON])]),  # over the raid cap
            3: pgcr(3, PATROL, [6, 7], [('m4', 'c4', [WEAPON])]),  # not a category
            1: pgcr(1, 0, [84, 5], [('m1', 'c1', [WEAPON])]),  # Trials; 2 has no PGCR
        },
        # m1 has the base weapon equipped, not the Adept; m2's profile is private.
        profiles={'m1': profile('c1', WEAPON, 'copy1', [FRAME, BARREL_A, None, TRAIT_A])},
    )
    scan.scan(conn, api, scan.Run(conn, per_category=1), head=6, count=100)

    def rows(sql):
        return [tuple(r) for r in conn.execute(sql)]

    assert rows("SELECT instanceId FROM DestinyPostGameCarnageReportData ORDER BY 1") == [
        (1,),
        (3,),
        (4,),
        (5,),
        (6,),
    ]
    assert rows(
        "SELECT instanceId, characterId, referenceId, itemInstanceId "
        "FROM DestinyHistoricalWeaponStats ORDER BY 1, 2, 3"
    ) == [
        (1, 'c1', WEAPON, 'copy1'),
        (5, 'c1', WEAPON, 'copy1'),
        (5, 'c1', WEAPON_ADEPT, None),
        (5, 'c2', WEAPON, None),
        (5, 'c5', WEAPON, None),
    ]
    assert rows("SELECT socketIndex, plugHash FROM DestinyItemSocketsComponent ORDER BY 1") == [
        (0, FRAME),
        (1, BARREL_A),
        (3, TRAIT_A),
    ]
    # Each finished player's profile is read once a run, though m1 played
    # twice; m5 and m6, who left, aren't read.
    assert sorted(api.profile_reads) == ['m1', 'm2']


def test_crawl_fetches_hard_content_first_and_caps_only_basic(conn, monkeypatch):
    monkeypatch.setattr(scan, 'BATCH', 1)  # one PGCR at a time, so the reads keep their order
    # The seeds: a player who finished a stored Master dungeon and one who
    # finished a Regular playlist match.
    add_pgcr(conn, 1, DUNGEON_MASTER)
    add_use(conn, 1, 'a', {3: TRAIT_A})
    add_pgcr(conn, 2, 0, [70, 5])
    add_use(conn, 2, 'b', {3: TRAIT_A})
    cutthroat = pgcr(10, RAID, [4, 7], [('m10', 'c10', [WEAPON])])
    cutthroat['selectedSkullHashes'] = [CUTTHROAT]
    api = FakeAPI(
        pgcrs={
            14: pgcr(14, OLD_RAID, [4, 7], [('m14', 'c14', [WEAPON])]),
            13: pgcr(13, RAID_MASTER, [4, 7], [('m13', 'c13', [WEAPON])]),
            12: pgcr(12, OLD_RAID, [4, 7], [('m12', 'c12', [WEAPON])]),
            10: cutthroat,
            20: pgcr(20, 0, [84, 5], [('m20', 'c20', [WEAPON])]),
            21: pgcr(21, 0, [70, 5], [('m21', 'c21', [WEAPON])]),
        },
        profiles={},
        histories={
            'player-a': [
                activity(14, OLD_RAID, [4, 7]),  # a raid: basic
                activity(13, RAID_MASTER, [4, 7]),  # hard
                activity(12, OLD_RAID, [4, 7]),  # basic, over the raid cap
                activity(11, RAID, [4, 7], completed=0),  # not finished
                activity(10, RAID, [4, 7]),  # a Custom tier: maybe Cutthroat, so hard
                activity(9, PATROL, [6, 7]),  # no category
                activity(8, 0, [84, 5], private=True),
            ],
            'player-b': [
                activity(21, 0, [70, 5]),  # Regular playlist: basic
                activity(20, 0, [84, 5]),  # Trials: hard
                activity(19, 0, [5, 94]),  # Sparrow Racing
                activity(18, 0, [84, 5], period='2000-01-01T00:00:00Z'),  # before the lookback
            ],
        },
    )
    run = scan.Run(conn, per_category=1)
    scan.crawl(conn, api, run, count=2)

    # Hard content first, then basic, each newest first. Every hard PGCR is
    # kept (the Cutthroat run counts as a Master raid); basic ones up to the
    # cap, so the older raid (12) isn't fetched once a raid is kept.
    assert api.pgcr_reads == [20, 13, 10, 21, 14]
    kept = {key: n for key, n in run.kept.items() if n}
    assert kept == {'raid_master': 2, 'trials': 1, 'raid': 1, 'quickplay': 1}
    crawled = {r[0] for r in conn.execute("SELECT membershipId FROM crawled_player")}
    assert crawled == {'player-a', 'player-b'}

    # The next crawl leaves those two until they're due again and reads the
    # players the kept PGCRs brought in.
    api.history_reads.clear()
    scan.crawl(conn, api, run, count=10)
    assert {m for m, _ in api.history_reads} == {'m10', 'm13', 'm14', 'm20', 'm21'}


def test_crawl_reads_histories_back_to_the_last_crawl(conn, monkeypatch):
    monkeypatch.setattr(scan, 'HISTORY_PAGE', 2)
    add_pgcr(conn, 1, DUNGEON_MASTER)
    add_use(conn, 1, 'a', {3: TRAIT_A})
    conn.execute("INSERT INTO crawled_player VALUES ('player-a', ?)", (votes.ago(30 / 24),))
    api = FakeAPI(
        pgcrs={},
        profiles={},
        histories={
            'player-a': [
                activity(i, RAID_MASTER, [4, 7], period=votes.ago(hours / 24))
                for i, hours in ((30, 10), (29, 20), (26, 33), (28, 40), (27, 50))
            ]
        },
    )
    scan.crawl(conn, api, scan.Run(conn, per_category=5), count=1)
    # Back to its last crawl, 30 hours ago, and 6 hours more, for an activity
    # that started before that crawl and ended after it (26). The second page
    # ends before that, so it's the last read.
    assert sorted(api.pgcr_reads) == [26, 29, 30]
    assert api.history_reads == [('player-a', 0), ('player-a', 1)]


def test_crawl_reads_known_players_first(conn):
    add_pgcr(conn, 1, DUNGEON_MASTER)
    add_use(conn, 1, 'a', {3: TRAIT_A})  # player-a, a seed from the data
    api = FakeAPI(pgcrs={}, profiles={})
    known = [{'membershipId': 'known', 'membershipType': 3}]
    scan.crawl(conn, api, scan.Run(conn, per_category=5), count=1, known=known)
    assert {m for m, _ in api.history_reads} == {'known'}
    # Not due again yet: the next crawl moves on to the players in the data.
    api.history_reads.clear()
    scan.crawl(conn, api, scan.Run(conn, per_category=5), count=1, known=known)
    assert {m for m, _ in api.history_reads} == {'player-a'}


def test_a_hard_content_crawl_reads_only_players_seen_in_it_who_have_played(conn):
    # With no room for basic content (--per-category 0), the crawl passes over
    # the players seen only there, and one whose character hasn't been played
    # since the lookback costs a profile request, not a history read.
    add_pgcr(conn, 1, DUNGEON_MASTER)
    add_use(conn, 1, 'a', {3: TRAIT_A})
    add_pgcr(conn, 2, DUNGEON_MASTER)
    add_use(conn, 2, 'c', {3: TRAIT_A})
    add_pgcr(conn, 3, 0, [70, 5])  # a Regular playlist match: basic
    add_use(conn, 3, 'b', {3: TRAIT_A})
    api = FakeAPI(pgcrs={}, profiles={}, last_played={'player-c': '2000-01-01T00:00:00Z'})
    scan.crawl(conn, api, scan.Run(conn, per_category=0), count=10)
    assert {m for m, _ in api.history_reads} == {'player-a'}
    crawled = {r[0] for r in conn.execute("SELECT membershipId FROM crawled_player")}
    assert crawled == {'player-a', 'player-c'}


def test_scan_reads_on_for_hard_content_once_basic_content_is_full(conn):
    # With no room for basic content (--per-category 0), the walk still reads
    # every PGCR, keeping the hard ones.
    api = FakeAPI(
        pgcrs={
            3: pgcr(3, 0, [70, 5], [('m3', 'c3', [WEAPON])]),  # a Regular playlist match
            2: pgcr(2, RAID_MASTER, [4, 7], [('m2', 'c2', [WEAPON])]),
            1: pgcr(1, 0, [70, 5], [('m1', 'c1', [WEAPON])]),
        },
        profiles={},
    )
    run = scan.Run(conn, per_category=0)
    scan.scan(conn, api, run, head=3, count=10)
    assert sorted(api.pgcr_reads) == [1, 2, 3]
    assert {key: n for key, n in run.kept.items() if n} == {'raid_master': 1}


def test_catch_up_reads_again_how_stored_raid_runs_started(conn):
    # Raids stored before the scan read how their run started, read again
    # newest first: copy 1's run started from a checkpoint and copy 2's player
    # joined 45 seconds in, so their clears count a third; copy 3's player
    # joined at the start (and again later, a rejoin), copy 4's run is Trials,
    # which has no checkpoints and isn't read again. Once read, a run isn't
    # read again.
    def report(instance, started, *joined):
        r = pgcr(instance, RAID, [4, 7], [(f'player-c{instance}', f'c{instance}', [WEAPON])])
        r['activityWasStartedFromBeginning'] = started
        entry = r['entries'].pop()
        for seconds in joined:
            r['entries'].append(
                {
                    **entry,
                    'values': {
                        **entry['values'],
                        'startSeconds': {'basic': {'value': float(seconds)}},
                    },
                }
            )
        return r

    for instance in (1, 2, 3):
        add_pgcr(conn, instance, RAID, [4, 7])
        add_use(conn, instance, f'c{instance}', {3: TRAIT_A})
    add_pgcr(conn, 4, 0, [84, 5])
    add_use(conn, 4, 'c4', {3: TRAIT_A})
    votes.fold(conn)
    api = FakeAPI(
        pgcrs={1: report(1, False, 0), 2: report(2, True, 45), 3: report(3, True, 0, 300)},
        profiles={},
    )
    scan.catch_up(conn, api, 2)
    assert sorted(api.pgcr_reads) == [2, 3]
    scan.catch_up(conn, api, 10)
    scan.catch_up(conn, api, 10)
    assert sorted(api.pgcr_reads) == [1, 2, 3]
    assert dict(conn.execute("SELECT itemInstanceId, checkpoint FROM copy_use")) == {
        'copy-1-c1': 1,
        'copy-2-c2': 1,
        'copy-3-c3': 0,
        'copy-4-c4': 0,
    }
