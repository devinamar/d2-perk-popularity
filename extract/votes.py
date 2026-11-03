# The votes the roll scores count (v_roll_unit): each weapon copy's uses by
# category (copy_use), folded from the PGCRs the scans keep, and the purge
# that keeps them a rolling picture of what is used now, by the setting view:
# a copy used within window_days keeps its recent categories only; a copy no
# longer used is dropped unless it is one of its weapon's (per side)
# rescue_copies newest copies: a weapon that drops out of use keeps its last
# known scores, and a rarely used one collects every copy seen, up to that
# many. Raw PGCR rows go after raw_days; their uses are folded by then.
import datetime

# Upsert copy_use from the finished, matched uses (v_weapon_use) of the PGCRs
# {where} picks.
FOLD = """
INSERT INTO copy_use (itemInstanceId, category, membershipId, item_hash, last_seen, checkpoint)
SELECT u.itemInstanceId, u.category, e.membershipId, u.item_hash, MAX(u.period),
       MIN(u.checkpoint)
FROM v_weapon_use u
JOIN DestinyPostGameCarnageReportEntry e
    ON e.instanceId = u.instanceId AND e.characterId = u.characterId
WHERE {where}
GROUP BY u.itemInstanceId, u.category
ON CONFLICT (itemInstanceId, category) DO UPDATE SET
    last_seen = MAX(last_seen, excluded.last_seen),
    membershipId = excluded.membershipId,
    item_hash = excluded.item_hash,
    checkpoint = MIN(checkpoint, excluded.checkpoint)
"""

# A copy still used on a side within the window drops its uses there that are
# older, so its weight follows what it is used in now.
DROP_OLD_USES = """
DELETE FROM copy_use AS u
WHERE u.last_seen < :cutoff
  AND EXISTS (
      SELECT 1
      FROM copy_use n
      JOIN activity_category a ON a.key = n.category
      JOIN activity_category b ON b.key = u.category
      WHERE n.itemInstanceId = u.itemInstanceId AND a.side = b.side
        AND n.last_seen >= :cutoff
  )
"""

# Per weapon and side, the copies newest first: an active copy always stays,
# an inactive one only within the first :keep.
DROP_UNRESCUED = """
WITH unit AS (
    SELECT u.itemInstanceId, a.side, d.weapon, MAX(u.last_seen) AS last_seen
    FROM copy_use u
    JOIN activity_category a ON a.key = u.category
    JOIN v_weapon_def d ON d.item_hash = u.item_hash
    GROUP BY u.itemInstanceId, a.side
),
ranked AS (
    SELECT itemInstanceId, side, last_seen,
           ROW_NUMBER() OVER (PARTITION BY side, weapon ORDER BY last_seen DESC) AS n
    FROM unit
)
DELETE FROM copy_use
WHERE (itemInstanceId, (SELECT side FROM activity_category WHERE key = category)) IN (
    SELECT itemInstanceId, side FROM ranked WHERE last_seen < :cutoff AND n > :keep
)
"""

# The plugs of copies no one votes with any more.
DROP_PLUGS = (
    "DELETE FROM DestinyItemSocketsComponent "
    "WHERE itemInstanceId NOT IN (SELECT itemInstanceId FROM copy_use)"
)

# The raw PGCR rows older than a cutoff go RAW_BATCH PGCRs at a time, in id
# order (one pass over the table in all), each batch its own transaction so a
# backlog never needs one big journal on a slow host: weapons and entries before
# the headers they point at.
RAW_BATCH = 2000
NEXT_RAW = (
    "SELECT instanceId FROM DestinyPostGameCarnageReportData "
    "WHERE instanceId > ? AND period < ? ORDER BY instanceId LIMIT ?"
)
RAW_TABLES = (
    'DestinyHistoricalWeaponStats',
    'DestinyPostGameCarnageReportEntry',
    'DestinyPostGameCarnageReportData',
)


def settings(conn) -> dict:
    # The setting view as {key: value}.
    return {key: value for key, value in conn.execute("SELECT key, value FROM setting")}


def ago(days: int) -> str:
    # The UTC time days ago, as PGCR periods are written ('2026-10-20T13:45:12Z').
    moment = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def fold(conn, ids=None) -> None:
    # Fold the uses of the PGCRs ids names (every stored one when None) into
    # copy_use. Doesn't commit: the scans commit it with the batch it folds.
    if ids is None:
        conn.execute(FOLD.format(where='1'))
    elif ids:
        marks = ', '.join('?' * len(ids))
        conn.execute(FOLD.format(where=f'u.instanceId IN ({marks})'), list(ids))


def is_empty(conn) -> bool:
    # True before anything was folded: a new database, or one built before
    # copy_use, whose stored PGCRs then need a full fold.
    return conn.execute("SELECT 1 FROM copy_use LIMIT 1").fetchone() is None


def purge(conn) -> None:
    # Roll copy_use to the window, keeping each weapon's newest copies, and
    # drop what nothing needs any more. Commits. Does nothing while nothing is
    # folded (a migrated database whose first fold hasn't run), which would
    # otherwise lose every copy's plugs.
    if is_empty(conn):
        return
    s = settings(conn)
    cutoff = ago(s['window_days'])
    with conn:
        conn.execute(DROP_OLD_USES, {'cutoff': cutoff})
        conn.execute(DROP_UNRESCUED, {'cutoff': cutoff, 'keep': s['rescue_copies']})
        conn.execute(DROP_PLUGS)
    drop_raw(conn, ago(s['raw_days']))


def drop_raw(conn, cutoff: str) -> None:
    # The raw PGCR rows older than cutoff, a batch at a time. The cutoff is
    # taken once: taken per table, a PGCR that aged past it between two of them
    # (a purge takes minutes on a slow host) lost its entries but not its header,
    # or its header but not its entries, and broke a foreign key.
    last = 0
    while ids := [r[0] for r in conn.execute(NEXT_RAW, (last, cutoff, RAW_BATCH))]:
        last = ids[-1]
        marks = ', '.join('?' * len(ids))
        with conn:
            for table in RAW_TABLES:
                conn.execute(f'DELETE FROM {table} WHERE instanceId IN ({marks})', ids)
