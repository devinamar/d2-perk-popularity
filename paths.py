# Where the app keeps its files. The code is the repo; what it writes lives in
# DATA_DIR: the repo root in a local checkout, the data volume in the service
# (D2_PERKS_DATA=/data, compose.yaml). All of it is gitignored.
import os
import pathlib

ROOT = pathlib.Path(__file__).parent

DATA_DIR = pathlib.Path(os.environ.get('D2_PERKS_DATA') or ROOT)

# The secrets, as KEY=value lines: BUNGIE_API_KEY, and for --publish
# GITHUB_TOKEN and GITHUB_REPO.
ENV_FILE = DATA_DIR / '.env'

# The manifest download, one SQLite file per game version.
MANIFEST_CACHE_DIR = DATA_DIR / '.cache' / 'manifest'

# The SQLite database every phase reads and writes. D2_PERKS_DB points a run
# at another one, such as a copy made with scripts/snapshot.py.
DB_FILE = pathlib.Path(os.environ.get('D2_PERKS_DB') or DATA_DIR / 'perk_popularity.db')

# Held by a running main.py, so a run never overlaps another.
LOCK_FILE = DATA_DIR / '.lock'

# The scores --publish exports, also kept here.
EXPORT_FILE = DATA_DIR / 'perk_scores.json'

# The well-known high-end players the history crawl reads first.
KNOWN_PLAYERS_FILE = ROOT / 'extract' / 'known_players.toml'
