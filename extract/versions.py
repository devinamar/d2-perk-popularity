# Which weapon each version is scored as. A family (v_weapon_def's family_name)
# is one weapon unless two or more of its versions roll different trait pools;
# then each pool is a weapon of its own, named after its source, or its season
# when the sources can't tell the pools apart. Reads the manifest tables and
# rewrites weapon_version; a change to the rule must bump the rule number in
# weapon_version.sql, which rebuilds the database and so re-ingests the
# manifest.
import itertools
import json
import re
from collections import defaultdict

# A collectible's sourceString that names no source.
NO_SOURCE = 'Random Perks:'
# ponytail: a longer source is a sentence of directions, not a name; the
# season names those pools.
LABEL_MAX = 30


def label(source: str) -> str:
    # A source's name for a pool: the quoted activity of 'Source: "King's Fall"
    # Raid', else the text after 'Source: ', without a trailing period; '' when
    # that runs past LABEL_MAX characters.
    quoted = re.match(r'Source: "([^"]+)"', source)
    if quoted:
        text = quoted.group(1)
    else:
        text = source.removeprefix('Source: ')
    text = text.rstrip('.')
    if len(text) > LABEL_MAX:
        return ''
    return text


def pools(conn) -> dict:
    # Each version's trait pool: the perks its first and second trait columns
    # roll, by name, so an enhanced perk counts with its base. A version
    # without trait columns has none.
    sockets = defaultdict(lambda: defaultdict(set))
    for item_hash, socket_idx, perk in conn.execute(
        "SELECT item_hash, socket_idx, perk FROM v_weapon_pool WHERE kind = 'trait'"
    ):
        sockets[item_hash][socket_idx].add(perk)
    return {h: tuple(frozenset(s[i]) for i in sorted(s)[:2]) for h, s in sockets.items()}


def rolls(pool: tuple) -> bool:
    # True when a trait column of the pool offers a choice.
    return any(len(column) > 1 for column in pool)


def group(conn) -> int:
    # Rewrite weapon_version: each named version's weapon. Two versions of a
    # family share a weapon when they roll the same trait pool, or come from
    # the same release and source (an Adept a perk off its base); a family
    # splits only when two or more of its groups roll traits, so a fixed
    # version alone never splits it. Groups go by earliest release, then
    # lowest hash, so names never depend on scan order. Returns the number of
    # weapons; the caller commits.
    pool = pools(conn)
    seasons = dict(conn.execute("SELECT traitId, season_name FROM release_tag_season"))
    release, source, families = {}, {}, defaultdict(list)
    for item_hash, family, trait_ids, text in conn.execute(
        "SELECT d.item_hash, d.family_name, i.traitIds, COALESCE(c.sourceString, '') "
        "FROM v_weapon_def d "
        "JOIN DestinyInventoryItemDefinition i ON i.hash = d.item_hash "
        "LEFT JOIN DestinyCollectibleDefinition c ON c.hash = i.collectibleHash "
        "WHERE d.name <> '' ORDER BY d.item_hash"
    ):
        traits = json.loads(trait_ids or '[]')
        release[item_hash] = next((t for t in traits if t.startswith('releases.')), '')
        if text.startswith(NO_SOURCE):
            text = ''
        source[item_hash] = text
        families[family].append(item_hash)

    rows, taken = [], set(families)
    for family, hashes in families.items():
        linked = {h: frozenset([h]) for h in hashes}
        for a, b in itertools.combinations(hashes, 2):
            same_pool = pool.get(a, ()) == pool.get(b, ())
            same_release = release[a] == release[b] and source[a] and source[a] == source[b]
            if same_pool or same_release:
                merged = linked[a] | linked[b]
                for h in merged:
                    linked[h] = merged
        groups = sorted(set(linked.values()), key=lambda g: (min(release[h] for h in g), min(g)))
        if sum(any(rolls(pool.get(h, ())) for h in g) for g in groups) < 2:
            rows += [(h, family) for h in hashes]
            continue

        # The label of each group: its first source by release, when every
        # group has one of its own; else each group's earliest release's
        # season.
        labels = []
        for g in groups:
            sources = [source[h] for h in sorted(g, key=lambda h: (release[h], h)) if source[h]]
            if sources:
                labels.append(label(sources[0]))
            else:
                labels.append('')
        if not all(labels) or len(set(labels)) < len(labels):
            labels = []
            for i, g in enumerate(groups, 1):
                first = min(release[h] for h in g)
                labels.append(seasons.get(first) or first.removeprefix('releases.') or str(i))
        for g, text in zip(groups, labels, strict=True):
            name, n = f'{family} ({text})', 1
            while name in taken:
                n += 1
                name = f'{family} ({text} {n})'
            taken.add(name)
            rows += [(h, name) for h in g]

    conn.execute("DELETE FROM weapon_version")
    conn.executemany("INSERT INTO weapon_version VALUES (?, ?)", rows)
    return len({weapon for _, weapon in rows})
