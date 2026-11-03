# Keeps the database in step with db/schema/, where each file holds one table
# (with its indexes) or view and is named after it. When the files change, the
# database is rebuilt from them, carrying over the tables in
# db/schema/collected/: the scanned PGCRs and matched loadouts, which can't be
# fetched again. The manifest tables refill on the next run.
import datetime
import os
import pathlib
import sqlite3

SCHEMA_DIR = pathlib.Path(__file__).with_name('schema')
KEPT_DIR = SCHEMA_DIR / 'collected'


def is_empty(conn) -> bool:
    # True for a new database with no tables yet.
    return conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone() is None


def create_tables(conn) -> None:
    # Run every file in db/schema/ against conn, a new, empty database.
    for path in sorted(SCHEMA_DIR.rglob('*.sql')):
        conn.executescript(path.read_text(encoding='utf-8'))


def schema_objects(conn) -> dict:
    # {name: sql} for every table, index and view. SQLite's internal tables
    # and the indexes it makes itself for PRIMARY KEY and UNIQUE are left
    # out; the latter have no sql.
    return {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
        )
    }


def matches_schema(conn) -> bool:
    # True when conn's tables, indexes and views are exactly the ones
    # db/schema/ creates. SQLite stores each CREATE statement as written, so
    # any edit to a file counts, even to a comment inside a table.
    blank = sqlite3.connect(':memory:')
    create_tables(blank)
    from_files = schema_objects(blank)
    blank.close()
    return schema_objects(conn) == from_files


def columns(conn, db_name: str, table: str) -> list:
    # Column names of db_name.table, in order; [] when the table doesn't exist.
    return [r[1] for r in conn.execute(f'PRAGMA {db_name}.table_info("{table}")')]


def rebuild(path) -> None:
    # Replace the database file at path with one built from db/schema/,
    # copying over the kept tables' rows (the columns both versions share).
    # The old file becomes the backup, and older backups are deleted. Raises
    # when the kept rows don't fit the new tables (for example a new NOT NULL
    # column without a default); the old file then stays in place, unchanged.
    path = pathlib.Path(path)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = path.with_name(f'{path.stem}.{stamp}.bak')
    new_db = path.with_name(f'{path.name}.new')
    new_db.unlink(missing_ok=True)

    kept_tables, dropped_columns = [], []
    conn = sqlite3.connect(new_db)
    try:
        create_tables(conn)
        conn.execute('ATTACH DATABASE ? AS old', (str(path),))
        for table in sorted(p.stem for p in KEPT_DIR.glob('*.sql')):
            new_cols, old_cols = columns(conn, 'main', table), columns(conn, 'old', table)
            shared = [c for c in new_cols if c in old_cols]
            if shared:
                names = ', '.join(f'"{c}"' for c in shared)
                conn.execute(
                    f'INSERT INTO main."{table}" ({names}) SELECT {names} FROM old."{table}"'
                )
                kept_tables.append(table)
            dropped_columns += [f'{table}.{c}' for c in old_cols if c not in new_cols]
        conn.commit()
    except BaseException:
        conn.close()
        new_db.unlink(missing_ok=True)
        raise
    conn.close()

    # Swap the files only once the new database is complete.
    os.replace(path, backup)
    os.replace(new_db, path)
    for old_backup in path.parent.glob(f'{path.stem}.????????-??????.bak'):
        if old_backup != backup:
            old_backup.unlink()
    print(
        f"  Database: the schema changed; rebuilt it keeping {', '.join(kept_tables) or 'nothing'}"
    )
    print(f"  Database: the old one is saved as {backup.name}")
    if dropped_columns:
        print(f"  Database: dropped column {', '.join(dropped_columns)} (still in the backup)")
