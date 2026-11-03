# PGCR scan and crawl. A PGCR (post-game carnage report) is Bungie's record of
# one finished activity: who played it and the weapons each got kills with.
# The live scan finds the newest PGCR and walks back through the ones before
# it, a random sample of what is played now; the crawl reads the recent
# histories of players seen in the data, hard content first. Both keep the
# PGCRs v_pgcr_category sorts into a category (every hard one, basic ones up to
# a cap per category each run), match each finished player's weapons to their
# copies (matching_copy), and fold those uses into the votes the roll scores
# count (extract/votes.py).
import collections
import concurrent.futures
import datetime
import itertools
import json
import sys

from extract import votes
from sources.bungie.api import SYSTEM_DISABLED, BungieError

WORKERS = 24  # requests in flight; the API client keeps the pace
# PGCR ids fetched together, then written. A batch waits for its slowest
# request, so smaller ones leave the workers idle: 200 measured 18.6 requests
# a second against the client's pace of 20, 50 only 12.
BATCH = 200
# The profile components a loadout needs: 205 CharacterEquipment (what each
# character has equipped), 305 ItemSockets (the plugs in those items), and 102
# ProfileInventories (the vault) and 201 CharacterInventories, which come back
# empty unless the player makes their inventory public (few do).
LOADOUT_COMPONENTS = [102, 201, 205, 305]


# The Bungie errors fetch() passed over this run, by ErrorCode, for the run's
# summary: missing PGCRs and private profiles are expected; anything else in
# number is worth a look.
FAILED = collections.Counter()


def fetch(call, *args):
    # call(*args), or None when Bungie answers with an error (a missing PGCR,
    # a private profile and the like), tallied in FAILED. Maintenance still
    # stops the run.
    try:
        return call(*args)
    except BungieError as e:
        if e.code == SYSTEM_DISABLED:
            raise
        FAILED[e.code] += 1
        return None


def progress(text: str, final: bool = False) -> None:
    # A progress line: on a terminal redrawn in place, ending with the final
    # one; in a log (the service's) each line once, the final one being the last.
    if sys.stdout.isatty():
        print(f"\r  {text}", end='\n' if final else '', flush=True)
    elif not final:
        print(f"  {text}", flush=True)


# Finding the newest PGCR


def anchor_id(conn, api, known) -> int:
    # Where the search for the newest PGCR starts: the newest one stored, else
    # the latest activity of the first of the known players (dicts of
    # membershipId and membershipType) with a public history.
    (newest,) = conn.execute(
        "SELECT MAX(instanceId) FROM DestinyPostGameCarnageReportData"
    ).fetchone()
    if newest:
        return newest
    for player in known:
        membership = (player['membershipType'], player['membershipId'])
        profile = fetch(api.get_profile, *membership, [100]) or {}
        ids = []
        for character_id in ((profile.get('profile') or {}).get('data') or {}).get(
            'characterIds'
        ) or []:
            latest = fetch(api.get_activity_history, *membership, character_id) or {}
            ids += [int(a['activityDetails']['instanceId']) for a in latest.get('activities', [])]
        if ids:
            return max(ids)
    raise SystemExit("No known player has a public activity history to start the scan from.")


def find_head(exists, anchor: int) -> int:
    # The newest id exists() finds a PGCR for, searching forward from anchor
    # (one it finds): the step doubles until a probe misses, then the gap
    # between the last hit and the miss is halved down to one. A probe also
    # tries the next two ids, since ids have gaps.
    # ponytail: in-progress activities thin out the ids near the head, so this
    # can stop a little short of it and the walk starts slightly older
    def probe(i):
        return exists(i) or exists(i + 1) or exists(i + 2)

    hit, step = anchor, 1
    while probe(hit + step):
        hit += step
        step *= 2
    miss = hit + step
    while miss - hit > 1:
        mid = (hit + miss) // 2
        if probe(mid):
            hit = mid
        else:
            miss = mid
    return hit


# Reading a PGCR


def pgcr_header(pgcr: dict) -> tuple:
    # A DestinyPostGameCarnageReportData row, in its column order.
    details = pgcr['activityDetails']
    started = pgcr.get('activityWasStartedFromBeginning')
    if started is not None:
        started = int(started)
    return (
        int(details['instanceId']),
        pgcr['period'],
        details.get('referenceId'),
        details.get('directorActivityHash'),
        details.get('mode'),
        json.dumps(details.get('modes') or []),
        int(bool(details.get('isPrivate'))),
        pgcr.get('activityDifficultyTier'),
        json.dumps(pgcr.get('selectedSkullHashes') or []),
        started,
    )


def stat(values: dict | None, key: str) -> int:
    # A PGCR stat's value (values[key].basic.value), 0 when it's absent.
    return int(((values or {}).get(key) or {}).get('basic', {}).get('value', 0))


def pgcr_players(pgcr: dict) -> tuple[list, list]:
    # (entries, weapons): a DestinyPostGameCarnageReportEntry row per
    # player's character, and an (instanceId, characterId, referenceId,
    # kills) row per weapon they got kills with.
    instance_id = int(pgcr['activityDetails']['instanceId'])
    entries, weapons = [], []
    for e in pgcr.get('entries') or []:
        user = e['player']['destinyUserInfo']
        membership_type = user.get('crossSaveOverride') or user['membershipType']
        completed = stat(e.get('values'), 'completed')
        start = stat(e.get('values'), 'startSeconds')
        entries.append(
            (instance_id, e['characterId'], user['membershipId'], membership_type, completed, start)
        )
        for w in (e.get('extended') or {}).get('weapons') or []:
            kills = stat(w.get('values'), 'uniqueWeaponKills')
            weapons.append((instance_id, e['characterId'], w['referenceId'], kills))
    return entries, weapons


# Matching weapons to loadouts


# A loadout's key for the versions a player has one copy of (loadout()).
ANYWHERE = 'anywhere'


def loadout(profile: dict) -> dict:
    # What a profile shows of a player's copies, each a copy (itemInstanceId,
    # [(socketIndex, plugHash)]) with its plugged sockets: {characterId:
    # {itemHash: copy}} for what each character has equipped, and under
    # ANYWHERE {itemHash: copy} for each version the profile shows one copy
    # of, equipped on any character or, for a player who makes them public,
    # in their inventories and vault. Empty when the profile hides them all.
    sockets = ((profile.get('itemComponents') or {}).get('sockets') or {}).get('data') or {}
    copies = collections.defaultdict(list)

    def add(item):
        # The item's copy, listed under its version; None when not instanced.
        copy_id = item.get('itemInstanceId')
        if not copy_id:
            return None
        plugged = (sockets.get(copy_id) or {}).get('sockets') or []
        copy = (
            copy_id,
            [(idx, s['plugHash']) for idx, s in enumerate(plugged) if s.get('plugHash')],
        )
        copies[item['itemHash']].append(copy)
        return copy

    found = {}
    equipment = (profile.get('characterEquipment') or {}).get('data') or {}
    for character_id, character in equipment.items():
        found[character_id] = {}
        for item in character.get('items') or []:
            if copy := add(item):
                found[character_id][item['itemHash']] = copy
    inventories = ((profile.get('characterInventories') or {}).get('data') or {}).values()
    vault = ((profile.get('profileInventory') or {}).get('data') or {}).get('items') or []
    for item in itertools.chain(vault, *(i.get('items') or [] for i in inventories)):
        add(item)
    if copies:
        found[ANYWHERE] = {h: c[0] for h, c in copies.items() if len(c) == 1}
    return found


def matching_copy(found: dict, character_id: str, item_hash: int):
    # The copy a weapon use matches: the one equipped on that character, else
    # the player's only copy of that version their profile shows (moved to
    # another character, or in a public vault). None when there's none, or
    # more than one, since either could be the one used.
    # ponytail: a private vault may hold the copy used, another copy's vote then
    # counts in its place; a public vault settles it.
    return found.get(character_id, {}).get(item_hash) or found.get(ANYWHERE, {}).get(item_hash)


def platform(api, membership_type: int, membership_id: str) -> int | None:
    # The membership type to read a player's profile with: the one their PGCR
    # entry gave, or when it gave none (0, as a few entries do), the one
    # Bungie's memberships list has for that id, cross-save first. None when
    # it can't be found.
    if membership_type:
        return membership_type
    found = fetch(api.get_memberships, membership_id) or {}
    for m in found.get('destinyMemberships') or []:
        if m.get('membershipId') == membership_id:
            return m.get('crossSaveOverride') or m.get('membershipType')
    return None


def fetch_loadout(api, membership_type: int, membership_id: str) -> dict:
    # A player's loadout(), or {} when their profile can't be read.
    membership_type = platform(api, membership_type, membership_id)
    if not membership_type:
        return {}
    profile = fetch(api.get_profile, membership_type, membership_id, LOADOUT_COMPONENTS)
    if profile is None:
        return {}
    return loadout(profile)


def save(conn, entries: list, weapons: list, loadouts: dict) -> int:
    # Store kept PGCRs' players and the weapons they used, each weapon with
    # its matching_copy() in its player's loadout now (NULL when none, or
    # when their loadout wasn't read), and the plugs of those copies.
    # A character listed twice in one PGCR (a rejoin) keeps one entry,
    # finished if either was, joined when it first did. Returns how many
    # weapons matched.
    conn.executemany(
        "INSERT INTO DestinyPostGameCarnageReportEntry VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (instanceId, characterId) "
        "DO UPDATE SET completed = MAX(completed, excluded.completed), "
        "startSeconds = MIN(startSeconds, excluded.startSeconds)",
        entries,
    )
    owner = {(e[0], e[1]): e[2] for e in entries}
    rows, plugs = [], {}
    for instance_id, character_id, item_hash, kills in weapons:
        found = loadouts.get(owner[(instance_id, character_id)], {})
        copy = matching_copy(found, character_id, item_hash)
        copy_id = None
        if copy:
            copy_id, plugs[copy_id] = copy
        rows.append((instance_id, character_id, item_hash, kills, copy_id))
    conn.executemany(
        "INSERT OR IGNORE INTO DestinyHistoricalWeaponStats VALUES (?, ?, ?, ?, ?)", rows
    )
    for copy_id, sockets in plugs.items():
        conn.execute("DELETE FROM DestinyItemSocketsComponent WHERE itemInstanceId = ?", (copy_id,))
        conn.executemany(
            "INSERT INTO DestinyItemSocketsComponent VALUES (?, ?, ?)",
            [(copy_id, idx, plug) for idx, plug in sockets],
        )
    return sum(1 for r in rows if r[4])


# Keeping PGCRs: what the live scan and the crawl share


class Run:
    # What one run's scan and crawl share: the cap on PGCRs kept per category,
    # how many each category has kept, the hard categories, the loadouts read
    # (membershipId -> loadout(), each player once a run), and the tallies
    # the progress lines print.
    def __init__(self, conn, per_category: int):
        self.per_category = per_category
        self.kept, self.hard = {}, set()
        for key, hard in conn.execute("SELECT key, hard FROM activity_category"):
            self.kept[key] = 0
            if hard:
                self.hard.add(key)
        self.loadouts = {}
        self.found = self.used = self.matched = 0

    def room(self, category: str) -> bool:
        # Whether a PGCR of category is still kept this run: a hard one always,
        # a basic one under the cap.
        return category in self.hard or self.kept[category] < self.per_category

    def full(self) -> bool:
        # True once every basic category is at the cap.
        return all(self.kept[c] >= self.per_category for c in self.kept if c not in self.hard)

    def tallies(self) -> str:
        return (
            f"{self.found:,} PGCRs, {sum(self.kept.values()):,} kept, "
            f"{len(self.loadouts):,} loadouts, {self.matched:,} of {self.used:,} weapons matched"
        )


def process(conn, api, pool, run: Run, ids: list) -> None:
    # Fetch the PGCRs of ids and store each; keep those that fall in a category
    # with room (run.room) and have a finished player who used a weapon, read
    # those players' loadouts (once a run), save the matches and fold them
    # into the votes. Commits.
    entries, weapons = [], []
    for pgcr in pool.map(lambda i: fetch(api.get_pgcr, i), ids):
        if pgcr is None:
            continue
        run.found += 1
        header = pgcr_header(pgcr)
        conn.execute(
            f"INSERT INTO DestinyPostGameCarnageReportData VALUES ({', '.join('?' * 10)})", header
        )
        (category,) = conn.execute(
            "SELECT category FROM v_pgcr_category WHERE instanceId = ?", (header[0],)
        ).fetchone()
        if category is None or not run.room(category):
            continue
        # Only the weapons of players who finished count: a PGCR with none (a
        # raid left early, a solo load-in) isn't kept.
        pgcr_entries, pgcr_weapons = pgcr_players(pgcr)
        finished = {e[1] for e in pgcr_entries if e[4]}
        if not any(w[1] in finished for w in pgcr_weapons):
            continue
        run.kept[category] += 1
        entries += pgcr_entries
        weapons += pgcr_weapons
    players = list({(e[2], e[3]) for e in entries if e[4] and e[2] not in run.loadouts})
    fetched = pool.map(lambda p: fetch_loadout(api, p[1], p[0]), players)
    for (membership_id, _), loadout in zip(players, fetched, strict=True):
        run.loadouts[membership_id] = loadout
    run.matched += save(conn, entries, weapons, run.loadouts)
    run.used += len(weapons)
    votes.fold(conn, {e[0] for e in entries})
    conn.commit()


def print_summary(run: Run) -> None:
    # What the run kept, by category, and the Bungie errors it passed over.
    print("  Kept this run: " + ', '.join(f"{key} {n}" for key, n in run.kept.items()))
    if FAILED:
        errors = ', '.join(f"{code} x{n:,}" for code, n in FAILED.most_common())
        print(f"  Bungie errors passed over (ErrorCode x count): {errors}")


# Walking back


def unstored(conn, head: int):
    # Ids from head down, skipping the PGCRs already stored.
    top = head
    while top > 0:
        low = max(top - 1000, 0)
        stored = {
            r[0]
            for r in conn.execute(
                "SELECT instanceId FROM DestinyPostGameCarnageReportData "
                "WHERE instanceId > ? AND instanceId <= ?",
                (low, top),
            )
        }
        yield from (i for i in range(top, low, -1) if i not in stored)
        top = low


def scan(conn, api, run: Run, head: int, count: int) -> None:
    # Walk back from head through count ids not stored yet, deciding each
    # PGCR's category as it's read: hard content is always kept, so the walk
    # goes on once every basic category is full. Newest first, so a player's
    # loadout is read right after their latest match. Each batch is committed,
    # so a stop midway keeps what was done.
    ids = unstored(conn, head)
    scanned = 0
    print(f"Scanning back from PGCR {head:,}...")
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        while scanned < count:
            batch = list(itertools.islice(ids, min(BATCH, count - scanned)))
            if not batch:
                break
            scanned += len(batch)
            process(conn, api, pool, run, batch)
            progress(f"{scanned:,} ids: {run.tallies()}")
    progress(f"{scanned:,} ids: {run.tallies()}", final=True)


# Crawling: the recent activity histories of players seen in the data

# A history's activities worth fetching are those whose PGCRs can fall in a
# category: PvE by its definition (v_crawl_activity), PvP by its modes, each
# PvP mode's PGCRs falling in one category, in v_pgcr_category's order. Missions
# played as strikes are known by their strike modes; private matches and
# Sparrow Racing (94) never count.
PVP_MODES = {84: 'trials', 69: 'competitive', 63: 'gambit', 75: 'gambit', 5: 'quickplay'}
STRIKE_MODES = {3, 18, 46}
SPARROW_RACING = 94
HISTORY_PAGE = 250  # the most activities a history page holds
SEEDS_PER_ROUND = 50  # players whose histories one round reads
# The crawl is run by hand (the service runs the live scan): how far back it
# reads a history at most, a new player's or one not read for longer, and how
# long before it reads a player's history again.
FIRST_LOOKBACK_DAYS = 7
RECRAWL_HOURS = 20
# A history entry's period is when the activity started, so one under way at
# the last crawl starts before it: a crawl reads this much further back (the
# PGCRs already stored are skipped).
OVERLAP_HOURS = 6

# Players seen finishing categorized content in the stored PGCRs, each
# category's most recent first, taken a pass at a time across the categories:
# hard ones first in each pass, then by weight. A player is listed once per
# category they finished, with whether it is hard content.
SEEDS = """
WITH seen AS (
    SELECT e.membershipId, e.membershipType, c.category, c.weight, a.hard,
           MAX(c.period) AS last
    FROM DestinyPostGameCarnageReportEntry e
    JOIN v_pgcr_category c ON c.instanceId = e.instanceId
    JOIN activity_category a ON a.key = c.category
    WHERE e.completed = 1
    GROUP BY e.membershipId, c.category
)
SELECT membershipId, membershipType, hard
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY last DESC) AS n FROM seen)
ORDER BY n, hard DESC, weight DESC
"""


def iso(moment: datetime.datetime) -> str:
    # A UTC time as Bungie writes it, like '2026-10-20T13:45:12Z'.
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def history(api, membership_type: int, membership_id: str, since: str) -> list:
    # (instanceId, activity hash, modes) of each public activity the player
    # finished since since (ISO 8601), every mode, read page by page (newest
    # first) on each character played since then (component 200 Characters
    # gives when each was last played), so a player who hasn't played costs
    # one request. Empty when their profile or history is private.
    membership_type = platform(api, membership_type, membership_id)
    if not membership_type:
        return []
    profile = fetch(api.get_profile, membership_type, membership_id, [200])
    characters = ((profile or {}).get('characters') or {}).get('data') or {}
    found = []
    for character_id, character in characters.items():
        if character.get('dateLastPlayed', since) < since:
            continue
        for page in itertools.count():
            reply = fetch(
                api.get_activity_history,
                membership_type,
                membership_id,
                character_id,
                HISTORY_PAGE,
                None,
                page,
            )
            activities = (reply or {}).get('activities') or []
            for a in activities:
                details = a['activityDetails']
                if (
                    a['period'] >= since
                    and stat(a.get('values'), 'completed')
                    and not details.get('isPrivate')
                ):
                    modes = set(details.get('modes') or [])
                    found.append((int(details['instanceId']), details['referenceId'], modes))
            if len(activities) < HISTORY_PAGE or activities[-1]['period'] < since:
                break
    return found


def category_of(activity: int, modes: set, crawlable: dict) -> str | None:
    # The category a history entry's PGCR can fall in (for PvE the best one
    # its definition allows), or None when it can't fall in one.
    if SPARROW_RACING in modes:
        return None
    for mode, category in PVP_MODES.items():
        if mode in modes:
            return category
    if activity in crawlable:
        return crawlable[activity]
    return 'portal' if modes & STRIKE_MODES else None


def crawl(conn, api, run: Run, count: int, known=()) -> None:
    # Read the recent histories of up to count players due a crawl (never
    # read, or not for RECRAWL_HOURS): the known players first (each a dict of
    # membershipId, membershipType; extract/known_players.toml), then those the
    # stored PGCRs show finishing categorized content, hard categories first
    # in each pass across them (SEEDS); once basic content has no room this
    # run (--per-category 0), only those seen in hard content. A history is
    # read back to its last crawl (less OVERLAP_HOURS), at most
    # FIRST_LOOKBACK_DAYS, so the loadouts read are close to the matches
    # they're matched to. A round's players count as crawled once its PGCRs
    # are. Of each round's activities, the PGCRs that could be hard content
    # are fetched first, then the rest, newest first; hard content is always
    # kept, basic content up to the cap, and isn't fetched once its category
    # is full.
    now = datetime.datetime.now(datetime.UTC)
    due = iso(now - datetime.timedelta(hours=RECRAWL_HOURS))
    first = iso(now - datetime.timedelta(days=FIRST_LOOKBACK_DAYS))
    crawled_at = dict(conn.execute("SELECT membershipId, crawled_at FROM crawled_player"))
    crawlable = dict(conn.execute("SELECT hash, category FROM v_crawl_activity"))
    players, listed = [], set()
    for p in itertools.chain(known, conn.execute(SEEDS)):
        membership_id = p['membershipId']
        last = crawled_at.get(membership_id)
        if membership_id in listed or (last and last >= due):
            continue
        if run.full() and not dict(p).get('hard', 1):
            continue
        listed.add(membership_id)
        since = first
        if last:
            back = datetime.datetime.fromisoformat(last) - datetime.timedelta(hours=OVERLAP_HOURS)
            since = max(iso(back), first)
        players.append((p['membershipType'], membership_id, since))
        if len(players) == count:
            break
    print(f"Crawling {len(players):,} players' recent histories...")
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        for start in range(0, len(players), SEEDS_PER_ROUND):
            seeds = players[start : start + SEEDS_PER_ROUND]
            histories = pool.map(lambda s: history(api, *s), seeds)
            wanted = {}
            for instance_id, activity, modes in itertools.chain.from_iterable(histories):
                category = category_of(activity, modes, crawlable)
                if category:
                    wanted[instance_id] = category
            ids = sorted(wanted, key=lambda i: (wanted[i] not in run.hard, -i))
            for batch_start in range(0, len(ids), BATCH):
                batch = [i for i in ids[batch_start : batch_start + BATCH] if run.room(wanted[i])]
                if not batch:
                    continue
                stored = {
                    r[0]
                    for r in conn.execute(
                        "SELECT instanceId FROM DestinyPostGameCarnageReportData "
                        f"WHERE instanceId IN ({', '.join('?' * len(batch))})",
                        batch,
                    )
                }
                process(conn, api, pool, run, [i for i in batch if i not in stored])
            conn.executemany(
                "INSERT INTO crawled_player VALUES (?, ?) "
                "ON CONFLICT (membershipId) DO UPDATE SET crawled_at = excluded.crawled_at",
                [(membership_id, iso(now)) for _, membership_id, _ in seeds],
            )
            conn.commit()
            progress(f"{start + len(seeds):,} players: {run.tallies()}")
    progress(f"{len(players):,} players: {run.tallies()}", final=True)


# Catching up: how the stored raid and dungeon runs started

# The kept PGCRs of categories with checkpoints that don't say how their run
# started, newest first: stored before the scan read it.
UNFLAGGED = """
WITH kept AS (SELECT DISTINCT instanceId FROM DestinyPostGameCarnageReportEntry)
SELECT k.instanceId
FROM kept k
JOIN DestinyPostGameCarnageReportData p ON p.instanceId = k.instanceId
JOIN v_pgcr_category c ON c.instanceId = k.instanceId
JOIN activity_category a ON a.key = c.category
WHERE p.activityWasStartedFromBeginning IS NULL AND a.checkpoints
ORDER BY k.instanceId DESC
LIMIT ?
"""

# Each copy and category with a use in the PGCRs {marks} takes its checkpoint
# again from all its stored uses, as a fold of them would.
RECHECK = """
WITH touched AS MATERIALIZED (
    SELECT DISTINCT itemInstanceId, category FROM v_weapon_use WHERE instanceId IN ({marks})
),
uses AS (
    SELECT u.itemInstanceId, u.category, MIN(u.checkpoint) AS checkpoint
    FROM touched t
    CROSS JOIN v_weapon_use u ON u.itemInstanceId = t.itemInstanceId AND u.category = t.category
    GROUP BY u.itemInstanceId, u.category
)
UPDATE copy_use SET checkpoint = uses.checkpoint
FROM uses
WHERE copy_use.itemInstanceId = uses.itemInstanceId AND copy_use.category = uses.category
"""


def catch_up(conn, api, count: int) -> None:
    # Read again up to count UNFLAGGED PGCRs, store how each run started and
    # when each player joined, and redo the checkpoint of the copies used in
    # them. Commits once, at the end: the recheck costs seconds a call, so it
    # runs once for all of them, and a stop midway leaves them all to the next
    # run. A PGCR Bungie doesn't return stays as it is, to be tried again.
    ids = [r[0] for r in conn.execute(UNFLAGGED, (count,))]
    if not ids:
        return
    print(f"Reading again {len(ids):,} raid and dungeon PGCRs stored before their start...")
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        for start in range(0, len(ids), BATCH):
            batch = ids[start : start + BATCH]
            for pgcr in pool.map(lambda i: fetch(api.get_pgcr, i), batch):
                if pgcr is None:
                    continue
                header = pgcr_header(pgcr)
                conn.execute(
                    "UPDATE DestinyPostGameCarnageReportData "
                    "SET activityWasStartedFromBeginning = ? WHERE instanceId = ?",
                    (header[9], header[0]),
                )
                # A character listed twice (a rejoin) joined when it first did.
                joined = {}
                for e in pgcr_players(pgcr)[0]:
                    joined[e[:2]] = min(joined.get(e[:2], e[5]), e[5])
                conn.executemany(
                    "UPDATE DestinyPostGameCarnageReportEntry SET startSeconds = ? "
                    "WHERE instanceId = ? AND characterId = ?",
                    [(seconds, i, c) for (i, c), seconds in joined.items()],
                )
            progress(f"{start + len(batch):,} of {len(ids):,} read again")
    progress(f"{len(ids):,} of {len(ids):,} read again", final=True)
    conn.execute(RECHECK.format(marks=', '.join('?' * len(ids))), ids)
    conn.commit()
