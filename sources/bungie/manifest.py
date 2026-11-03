# Downloads the Destiny 2 manifest: Bungie's SQLite database of every item,
# perk and mod definition. It is cached in .cache/manifest per game version
# and downloaded again when a patch changes the version.
# extract/manifest.py reads it into the manifest tables.
import os
import pathlib
import shutil
import zipfile

import requests

import paths


def download_manifest(api) -> tuple[pathlib.Path, str]:
    # (db_path, version) of the current manifest, downloading it when this
    # version isn't cached yet. Older cached versions are then deleted.
    print("Loading manifest...")
    manifest = api.get_manifest()
    content_path = manifest['mobileWorldContentPaths']['en']
    db_url = f"https://www.bungie.net{content_path}"
    version = content_path.split('/')[-1].replace('.content', '')

    cache_dir = paths.MANIFEST_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    db_path = cache_dir / f"{version}.sqlite"

    if not db_path.exists():
        print("  Downloading...")
        # Work in .part files so a crash never leaves a half-written file at
        # db_path.
        zip_tmp = db_path.with_name(db_path.name + '.zip.part')
        sqlite_part = db_path.with_name(db_path.name + '.part')

        try:
            # Stream the zip straight to disk.
            with requests.get(db_url, timeout=120, stream=True) as response:
                response.raise_for_status()
                with zip_tmp.open('wb') as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        f.write(chunk)

            # The zip holds one file, the SQLite db. Copy it out in chunks so
            # the ~340 MB file never sits in memory.
            with (
                zipfile.ZipFile(zip_tmp) as zf,
                zf.open(zf.namelist()[0]) as src,
                sqlite_part.open('wb') as dst,
            ):
                shutil.copyfileobj(src, dst, length=65536)

            # Atomic rename, so db_path only ever holds a complete file.
            os.replace(sqlite_part, db_path)
        finally:
            # Delete the .part files either way; after a failure the next run
            # starts over.
            zip_tmp.unlink(missing_ok=True)
            sqlite_part.unlink(missing_ok=True)

        # Delete manifests from earlier patches.
        for old in cache_dir.glob("world_sql_content_*.sqlite"):
            if old != db_path:
                old.unlink()

    return db_path, version
