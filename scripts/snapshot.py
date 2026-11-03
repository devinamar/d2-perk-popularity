# A consistent copy of the database, made with SQLite's backup (safe while a
# run writes to it), run in the app's container:
# docker compose exec app python scripts/snapshot.py /data/copy.db
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import paths  # noqa: E402 (after the path it needs)

source, target = sqlite3.connect(paths.DB_FILE), sqlite3.connect(sys.argv[1])
with target:
    source.backup(target)
