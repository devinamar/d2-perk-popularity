# Running and deploying

## Running it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
echo 'BUNGIE_API_KEY=...' > .env                    # a Bungie app's API key; no OAuth needed
.venv/bin/python main.py --scan 3000 --crawl 0 --per-category 67 --catch-up 3000   # the service's report crawl
.venv/bin/python main.py --scan 0 --crawl 1000      # a player crawl, by hand
.venv/bin/python main.py --scan 0 --crawl 0 --publish   # export and publish (needs GITHUB_TOKEN, GITHUB_REPO)
.venv/bin/python -m pytest -q                       # tests (offline)
docker build --target test .                        # the tests, inside the app's image
```

Every run ends by purging to the window. What a run writes (the database, the manifest cache, the
lock, the export) goes to the repo root, or to `D2_PERKS_DATA` when set, where `.env` is read from
too. `D2_PERKS_DB=path` points a run at another database, such as a copy made with
`scripts/snapshot.py`. The score views are there for audits: `v_weapon_score`,
`v_roll_score`, and its two sides `v_pve_roll_score` and `v_pvp_roll_score`; `weapon_version`
holds the weapon each version is scored as.

## Running it as a service

Any machine with Docker runs it with `compose.yaml`: the app's own image, built from the
`Dockerfile` on `python:3.13-slim`, with Python, the pinned packages (`requirements.txt`) and the
code. It runs as an unprivileged user (uid 568) on a read-only filesystem, with `/tmp` in memory.
Its one mount is `./data`: the database, the manifest cache, `.env`, and SQLite's temporary files
(`tmp/`, `SQLITE_TMPDIR`), so a big query spills to disk rather than memory.

```bash
mkdir -p data/tmp
printf 'BUNGIE_API_KEY=...\n' > data/.env      # add GITHUB_TOKEN and GITHUB_REPO to publish
sudo chown -R 568:568 data && sudo chmod 600 data/.env
docker compose up -d --build
```

`GITHUB_TOKEN` is a fine-grained token with Contents read and write on `GITHUB_REPO` only; the
scores go to that repo's `data` branch.

The image runs the scheduler, `service.py`, which runs `main.py` as a process of its own for each
job, one at a time. Each job runs every so many minutes; when more than one is due, the one due
longest goes first, so a long run makes the next one late rather than skipped:

| Every | Run |
| --- | --- |
| 5 minutes | the report crawl, `--scan 3000 --crawl 0 --per-category 67 --catch-up 3000` |
| week, Mondays from 08:30 UTC | publish, `--scan 0 --crawl 0 --publish`, after the run going then |

A run that hits a Bungie or network error stops collecting, still purges, and exits 1; the next one
starts as usual.

```bash
docker compose logs -f app                                        # the log (Docker keeps 3 × 10 MB)
docker compose exec app python scripts/snapshot.py /data/copy.db  # a consistent copy of the database
git pull && docker compose up -d --build                          # update; an older commit rolls back
```

A run never overlaps another, so to publish by hand, stop the service around it:

```bash
docker compose stop && docker compose run --rm app python main.py --scan 0 --crawl 0 --publish; docker compose start
```

## Structure

| Path | What it does |
| --- | --- |
| `main.py` | One run: collect, purge, and publish when asked |
| `service.py` | The app's scheduler: runs `main.py` on the timetable |
| `paths.py` | Where every file lives |
| `db/` | The SQLite database: one `.sql` file per table or view under `schema/`, rebuilt when they change (keeping `schema/collected/`) |
| `sources/bungie/` | The Bungie API client and manifest download |
| `sources/github.py` | Publishing a file to the repo |
| `extract/` | The manifest ingest, with each version's weapon (`versions.py`), the report crawl and player crawl (`scan.py`), and the votes' window (`votes.py`) |
| `publish/` | The JSON export |
| `Dockerfile`, `.dockerignore` | The app's image, and what stays out of it |
| `docs/` | The method, and running and deploying the app |
| `compose.yaml` | Running it as a service with Docker |
| `scripts/snapshot.py` | A consistent copy of the database while it runs |
| `tests/` | Offline tests |
| `.github/workflows/` | The tests on every push to main |
