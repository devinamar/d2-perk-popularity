# D2 Perk Popularity: an aggregator of the weapon rolls Destiny 2 players
# use. A run scans Bungie's newest post-game carnage reports (a random sample of
# what is played now) and crawls the recent histories of players seen in the
# data, hard content first, keeping the rolls of the copies they used; then
# folds them into votes over a rolling window, which the roll-score views
# (db/schema/views/v_roll_score.sql) score per weapon for PvE and PvP; --publish
# commits those scores as JSON to the repo's data branch. The service's
# scheduler (service.py) runs it; docs/ describes the method and the service.

import argparse
import datetime
import fcntl
import os
import sys
import tomllib

import requests

import paths
from db import connection
from extract import manifest, scan, votes
from publish import export
from sources import github
from sources.bungie.api import BungieAPI, BungieError
from sources.bungie.manifest import download_manifest

# The branch --publish commits perk_scores.json to, away from the code.
DATA_BRANCH = 'data'


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='main.py',
        description='Collect the weapon rolls Destiny 2 players use, and score them.',
    )
    parser.add_argument(
        '--scan',
        type=int,
        default=4000,
        metavar='N',
        help='PGCR ids to walk back through from the newest (default 4000)',
    )
    parser.add_argument(
        '--crawl',
        type=int,
        default=1000,
        metavar='N',
        help="players whose recent histories to crawl, hard content first (default 1000)",
    )
    parser.add_argument(
        '--per-category',
        type=int,
        default=200,
        metavar='N',
        help='basic-content PGCRs to keep per category this run; hard content is never capped '
        '(default 200)',
    )
    parser.add_argument(
        '--catch-up',
        type=int,
        default=0,
        metavar='N',
        help='raid and dungeon PGCRs stored before the scan read how their run started '
        'to read again (default 0)',
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        help="then export the scores and commit them to GITHUB_REPO's data branch",
    )
    return parser.parse_args(argv)


def load_env() -> None:
    # Put .env's KEY=value lines in the environment, under what's set there.
    if paths.ENV_FILE.exists():
        for line in paths.ENV_FILE.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())


def require(name: str, what: str) -> str:
    # The environment value name, which the run can't go without.
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Put {name}=<{what}> in {paths.ENV_FILE}.")
    return value


def hold_lock():
    # Hold the run lock while the process lives, or exit when another run
    # holds it: a scheduled run that would overlap one still going is
    # skipped. Returns the open lock file, which must stay referenced.
    lock = open(paths.LOCK_FILE, 'w')  # noqa: SIM115 (held until exit)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another run is still going; skipping this one.")
        sys.exit(0)
    return lock


def known_players() -> list:
    # The well-known players the crawl reads first, as the crawl takes them.
    with open(paths.KNOWN_PLAYERS_FILE, 'rb') as f:
        players = tomllib.load(f)['players']
    return [{'membershipId': p['id'], 'membershipType': p['type']} for p in players]


def stamp(text: str) -> None:
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {text}", flush=True)


def publish(conn) -> bool:
    # Export the scores and commit them to the data branch; False when there
    # was nothing to publish or GitHub refused it.
    content = export.write(conn)
    if content is None:
        print("Nothing to publish: no weapon has votes.")
        return False
    try:
        url = github.put_file(
            require('GITHUB_TOKEN', 'a fine-grained token with Contents write on the repo'),
            require('GITHUB_REPO', 'owner/name'),
            DATA_BRANCH,
            paths.EXPORT_FILE.name,
            content,
            f"chore(data): publish perk scores {datetime.date.today():%Y-%m-%d}",
        )
    except requests.RequestException as e:
        print(f"Publishing failed: {e}")
        return False
    print(f"Published {len(content) / 1e6:.1f} MB: {url}")
    return True


def main():
    args = parse_args()
    lock = hold_lock()  # noqa: F841 (held until exit)
    stamp(f"main.py {' '.join(sys.argv[1:])}")
    load_env()
    conn = connection.open_db()
    api = BungieAPI(
        require('BUNGIE_API_KEY', 'the API key of a Bungie app, bungie.net/en/Application')
    )

    # A failure stops the collection; what was done is saved, and the purge
    # still runs on it.
    ok, run = True, None
    try:
        manifest.ingest_manifest(conn, *download_manifest(api))
        if votes.is_empty(conn):
            # A database from before the votes: fold what it stored.
            votes.fold(conn)
            conn.commit()
        run = scan.Run(conn, args.per_category)
        known = known_players()
        if args.scan:
            print("Finding the newest PGCR...")
            anchor = scan.anchor_id(conn, api, known)
            head = scan.find_head(lambda i: scan.fetch(api.get_pgcr, i) is not None, anchor)
            scan.scan(conn, api, run, head, args.scan)
        if args.crawl:
            scan.crawl(conn, api, run, args.crawl, known)
        if args.catch_up:
            scan.catch_up(conn, api, args.catch_up)
    except KeyboardInterrupt:
        conn.rollback()
        print("\nStopped; what was done is saved.")
    except (BungieError, requests.RequestException) as e:
        conn.rollback()
        ok = False
        print(f"\nStopped: {e}. What was done is saved.")
    if run:
        scan.print_summary(run)
    votes.purge(conn)
    if args.publish:
        ok = publish(conn) and ok
    stamp("done" if ok else "done, with an error")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
