# Rebuilding the database when db/schema/ changes (db/migrate.py), here the
# one-off conversion of plugs kept a row per socket into a list per copy.
import sqlite3

from db import migrate


def test_rebuild_folds_plugs_kept_a_row_per_socket(tmp_path):
    path = tmp_path / 'perk_popularity.db'
    conn = sqlite3.connect(path)
    migrate.create_tables(conn)
    conn.executescript("""
        DROP TABLE DestinyItemSocketsComponent;
        CREATE TABLE DestinyItemSocketsComponent (
            itemInstanceId TEXT NOT NULL, socketIndex INTEGER NOT NULL,
            plugHash INTEGER NOT NULL, PRIMARY KEY (itemInstanceId, socketIndex));
        INSERT INTO DestinyItemSocketsComponent VALUES
            ('a', 0, 10), ('a', 1, 11), ('a', 3, 13), ('b', 2, 22);
    """)
    conn.commit()
    conn.close()

    migrate.rebuild(path)
    conn = sqlite3.connect(path)
    assert migrate.matches_schema(conn)
    assert conn.execute("SELECT * FROM DestinyItemSocketsComponent ORDER BY 1").fetchall() == [
        ('a', '[10,11,null,13]'),
        ('b', '[null,null,22]'),
    ]
