# The published scores (publish/export.py), and how they reach GitHub
# (sources/github.py) against a stand-in session.
import json

from conftest import (
    BARREL_A,
    BARREL_B,
    BARREL_SET,
    RAID,
    RAID_MASTER,
    TRAIT_A,
    TRAIT_B,
    TRAIT_SET,
    WEAPON,
    WEAPON_ADEPT,
    add_pgcr,
    add_use,
    add_weapon,
)

from extract import votes
from publish import export
from sources import github


def test_export_lists_each_weapon_with_its_columns(conn):
    add_pgcr(conn, 1, RAID_MASTER)  # hard content, weight 32
    add_use(conn, 1, 'a', {1: BARREL_A, 3: TRAIT_A})
    add_pgcr(conn, 2, RAID)  # normal content, weight 4
    add_use(conn, 2, 'b', {1: BARREL_B, 3: TRAIT_B})
    votes.fold(conn)

    scores = export.build(conn)
    assert scores['schema_version'] == export.SCHEMA_VERSION
    assert scores['pvp'] == []
    (weapon,) = scores['pve']
    columns = weapon.pop('columns')
    # One vote in each group: equally credible, so they split hard_weight to
    # the rest.
    assert weapon == {
        'name': 'Test Cannon',
        'family': 'Test Cannon',
        'type': 'Hand Cannon',
        'item_hash': WEAPON,
        'item_hashes': [WEAPON, WEAPON_ADEPT],
        'rank': 1,
        'players': 2,
        'active_players': 2,
        'hard': True,
        'hard_weight': 0.75,
        'groups': {'hard': {'copies': 1, 'n_eff': 1.0}, 'normal': {'copies': 1, 'n_eff': 1.0}},
        'last_seen': '2099-01-01T00:00:00Z',
        'stale': False,
    }
    # The columns in socket order, each's perks by share, the trait pair before
    # each trait on its own (one trait column here). The one-perk origin socket
    # isn't scored.
    assert [(c['kind'], [p['perk'] for p in c['perks']]) for c in columns] == [
        ('barrel', ['Arrowhead Brake', 'Smallbore']),
        ('traits', ['Rampage', 'Kill Clip']),
        ('trait1', ['Rampage', 'Kill Clip']),
    ]
    barrel = columns[0]
    assert barrel['hard'] == barrel['normal'] == {'n_eff': 1.0, 'credibility': 0.03}
    assert (barrel['n_eff'], barrel['confidence']) == (1.6, 'very low')  # 1 / (0.75² + 0.25²)
    top = barrel['perks'][0]
    assert (top['perk'], top['share'], top['hard'], top['normal']) == (
        'Arrowhead Brake',
        0.75,
        1.0,
        0.0,
    )
    # Aggregates only: no player or copy ids.
    text = json.dumps(scores)
    assert 'player-' not in text and 'copy-' not in text


def test_each_pool_of_a_family_exports_as_its_own_weapon(conn):
    # The two versions roll different trait pools (weapon_version as the
    # manifest ingest fills it): two weapons of one family, each with its own
    # versions.
    conn.executemany(
        "INSERT INTO weapon_version VALUES (?, ?)",
        [(WEAPON, 'Test Cannon (Test Raid)'), (WEAPON_ADEPT, 'Test Cannon (Pantheon)')],
    )
    add_pgcr(conn, 1, RAID)
    add_use(conn, 1, 'a', {1: BARREL_A})
    add_pgcr(conn, 2, RAID)
    add_use(conn, 2, 'b', {1: BARREL_B}, item_hash=WEAPON_ADEPT)
    votes.fold(conn)

    weapons = {
        w['name']: (w['family'], w['item_hash'], w['item_hashes'])
        for w in export.build(conn)['pve']
    }
    assert weapons == {
        'Test Cannon (Test Raid)': ('Test Cannon', WEAPON, [WEAPON]),
        'Test Cannon (Pantheon)': ('Test Cannon', WEAPON_ADEPT, [WEAPON_ADEPT]),
    }


def test_each_column_lists_once_when_versions_place_it_apart(conn):
    # A version with its traits a socket later: its Master raid copy votes at
    # socket 4, the base's Raid copy at socket 3, yet each column is listed
    # once, at its first socket.
    add_weapon(conn, 102, 'Test Cannon', {1: BARREL_SET, 4: TRAIT_SET})
    add_pgcr(conn, 1, RAID_MASTER)
    add_use(conn, 1, 'a', {1: BARREL_A, 4: TRAIT_A}, item_hash=102)
    add_pgcr(conn, 2, RAID)
    add_use(conn, 2, 'b', {1: BARREL_B, 3: TRAIT_B})
    votes.fold(conn)

    (weapon,) = export.build(conn)['pve']
    assert [c['kind'] for c in weapon['columns']] == ['barrel', 'traits', 'trait1']


class Reply:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f'HTTP {self.status_code}')


class Session:
    # A stand-in requests session: the file's lookup answers status (with its
    # sha when found); the PUT commits. Records both.
    def __init__(self, status):
        self.status, self.calls = status, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Reply(self.status, {'sha': 'old-sha'})

    def put(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Reply(201, {'commit': {'html_url': 'https://github.com/o/r/commit/1'}})


def test_put_file_replaces_the_file_or_creates_it():
    for status, sha in ((200, {'sha': 'old-sha'}), (404, {})):
        session = Session(status)
        url = github.put_file('t', 'o/r', 'data', 'perk_scores.json', b'{}', 'msg', session)
        assert url == 'https://github.com/o/r/commit/1'
        (get_url, get), (put_url, put) = session.calls
        assert get_url == put_url == 'https://api.github.com/repos/o/r/contents/perk_scores.json'
        assert get['params'] == {'ref': 'data'}
        assert put['headers']['Authorization'] == 'Bearer t'
        assert put['json'] == {'message': 'msg', 'content': 'e30=', 'branch': 'data', **sha}
