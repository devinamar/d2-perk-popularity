# The votes' rolling window (extract/votes.py): a copy still in use keeps only
# its recent uses, each weapon keeps its newest copies up to the floor, and raw
# PGCR rows go once they're old.
import datetime

from conftest import BARREL_A, RAID, RAID_MASTER, WEAPON, WEAPON_ADEPT, add_pgcr, add_use

from extract import votes


def copies(conn, side):
    return {
        r[0] for r in conn.execute("SELECT itemInstanceId FROM v_roll_unit WHERE side = ?", (side,))
    }


def test_purge_rolls_the_window_and_keeps_each_weapons_newest_copies(conn):
    # a1: a Master raid 40 days ago and a raid 2 days ago. It's still in use,
    # so it keeps the raid alone and weighs 4.
    add_pgcr(conn, 1, RAID_MASTER, period=votes.ago(40))
    add_use(conn, 1, 'a', {1: BARREL_A}, copy_id='a1')
    add_pgcr(conn, 2, RAID, period=votes.ago(2))
    add_use(conn, 2, 'a', {1: BARREL_A}, copy_id='a1')
    # Two more copies used this month, and 110 last used 31 to 140 days ago:
    # the floor of 100 keeps the 97 newest of those, however old.
    for i in range(2):
        add_pgcr(conn, 10 + i, RAID, period=votes.ago(5))
        add_use(conn, 10 + i, f'new{i}', {1: BARREL_A}, copy_id=f'new{i}')
    for i in range(110):
        add_pgcr(conn, 100 + i, RAID, period=votes.ago(31 + i))
        add_use(conn, 100 + i, f'old{i}', {1: BARREL_A}, copy_id=f'old{i}')
    # PvP: four Trials copies, all 35 days old.
    for i in range(4):
        add_pgcr(conn, 40 + i, 0, [84, 5], period=votes.ago(35))
        add_use(conn, 40 + i, f'pvp{i}', {1: BARREL_A}, copy_id=f'pvp{i}')
    votes.fold(conn)
    votes.purge(conn)

    assert copies(conn, 'pve') == {'a1', 'new0', 'new1'} | {f'old{i}' for i in range(97)}
    a1 = "WHERE itemInstanceId = 'a1'"
    assert [r[0] for r in conn.execute(f"SELECT category FROM copy_use {a1}")] == ['raid']
    assert conn.execute(f"SELECT weight FROM v_roll_unit {a1}").fetchone()[0] == 4
    # PvP: all four kept, the weapon stale: no carnage entries in 30 days.
    assert copies(conn, 'pvp') == {f'pvp{i}' for i in range(4)}
    scores = {
        r['side']: (r['players'], r['active_players'], r['stale'])
        for r in conn.execute("SELECT * FROM v_weapon_score")
    }
    assert scores == {'pve': (100, 3, 0), 'pvp': (4, 0, 1)}

    # Raw rows older than 14 days are gone; the kept copies keep their plugs.
    def ids(table, column='instanceId'):
        return {r[0] for r in conn.execute(f"SELECT DISTINCT {column} FROM {table}")}

    assert ids('DestinyPostGameCarnageReportData') == {2, 10, 11}
    assert ids('DestinyPostGameCarnageReportEntry') == {2, 10, 11}
    assert ids('DestinyHistoricalWeaponStats') == {2, 10, 11}
    assert ids('DestinyItemSocketsComponent', 'itemInstanceId') == copies(conn, 'pve') | copies(
        conn, 'pvp'
    )


def test_purge_keeps_the_floor_for_each_weapon_of_a_split_family(conn):
    # One family in two trait pools (weapon_version): each weapon keeps its own
    # 100 newest copies, not 100 between them.
    conn.executemany(
        "INSERT INTO weapon_version VALUES (?, ?)",
        [(WEAPON, 'Test Cannon (Test Raid)'), (WEAPON_ADEPT, 'Test Cannon (Pantheon)')],
    )
    for i in range(102):
        for k, item_hash in enumerate((WEAPON, WEAPON_ADEPT)):
            instance = 100 + 2 * i + k
            add_pgcr(conn, instance, RAID, period=votes.ago(100 + i))
            add_use(conn, instance, f'p{instance}', {1: BARREL_A}, item_hash=item_hash)
    votes.fold(conn)
    votes.purge(conn)

    kept = dict(conn.execute("SELECT weapon, COUNT(*) FROM v_roll_unit GROUP BY weapon"))
    assert kept == {'Test Cannon (Test Raid)': 100, 'Test Cannon (Pantheon)': 100}


def test_copies_in_use_stay_past_the_floor(conn):
    # 101 copies used this month all stay; with the floor full of them, the 5
    # last used 40 days ago go.
    for i in range(101):
        add_pgcr(conn, 10 + i, RAID, period=votes.ago(3))
        add_use(conn, 10 + i, f'new{i}', {1: BARREL_A}, copy_id=f'new{i}')
    for i in range(5):
        add_pgcr(conn, 200 + i, RAID, period=votes.ago(40))
        add_use(conn, 200 + i, f'old{i}', {1: BARREL_A}, copy_id=f'old{i}')
    votes.fold(conn)
    votes.purge(conn)

    assert copies(conn, 'pve') == {f'new{i}' for i in range(101)}


def test_purge_drops_raw_pgcrs_in_batches_against_one_cutoff(conn, monkeypatch):
    # A purge takes minutes on a slow host. Here each clock reading is an hour
    # later than the last; a PGCR that ages past the raw cutoff mid-purge must
    # keep its header, entries and weapons together (taking the cutoff per
    # table broke a foreign key), and the old PGCRs go two at a time.
    fmt, real_ago, reads = '%Y-%m-%dT%H:%M:%SZ', votes.ago, []

    def running_clock(days):
        reads.append(days)
        moment = datetime.datetime.strptime(real_ago(days), fmt)
        return (moment + datetime.timedelta(hours=len(reads))).strftime(fmt)

    for i in range(5):
        add_pgcr(conn, 50 + i, RAID, period=real_ago(20 + i))
        add_use(conn, 50 + i, f'c{i}', {1: BARREL_A}, copy_id=f'c{i}')
    edge = datetime.datetime.strptime(real_ago(14), fmt) + datetime.timedelta(hours=3.5)
    add_pgcr(conn, 60, RAID, period=edge.strftime(fmt))
    add_use(conn, 60, 'edge', {1: BARREL_A}, copy_id='edge')
    votes.fold(conn)
    monkeypatch.setattr(votes, 'ago', running_clock)
    monkeypatch.setattr(votes, 'RAW_BATCH', 2)
    votes.purge(conn)

    for table in ('DestinyPostGameCarnageReportData', 'DestinyPostGameCarnageReportEntry',
                  'DestinyHistoricalWeaponStats'):
        assert {r[0] for r in conn.execute(f"SELECT DISTINCT instanceId FROM {table}")} == {60}
