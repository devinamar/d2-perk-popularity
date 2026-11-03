# The published scores, perk_scores.json: per side, every weapon with votes in
# rank order (v_weapon_score), each with its scored columns in socket order and
# their perks by share (v_roll_score: the side's hard and normal groups merged),
# plus the settings and categories they were scored under. Aggregates only: no
# player or copy ids leave the database.
import datetime
import json

import paths
from extract import votes

# Each weapon with its numbers, its family, every version scored as it, and
# the version most of its copies are.
WEAPONS = """
SELECT w.side, w.weapon AS name, d.family_name AS family, d.wtype AS type, v.item_hash,
       h.item_hashes, w.weapon_rank AS rank, w.players, w.active_players, w.hard,
       w.hard_weight, w.hard_copies, w.hard_n_eff, w.normal_copies, w.normal_n_eff,
       w.last_seen, w.stale
FROM v_weapon_score w
JOIN (
    SELECT side, weapon, item_hash,
           ROW_NUMBER() OVER (PARTITION BY side, weapon
                              ORDER BY COUNT(DISTINCT itemInstanceId) DESC, item_hash) AS n
    FROM v_roll_unit
    GROUP BY side, weapon, item_hash
) v ON v.side = w.side AND v.weapon = w.weapon AND v.n = 1
JOIN v_weapon_def d ON d.item_hash = v.item_hash
JOIN (
    SELECT weapon, json_group_array(item_hash ORDER BY item_hash) AS item_hashes
    FROM v_weapon_def
    GROUP BY weapon
) h ON h.weapon = w.weapon
ORDER BY w.side, w.weapon_rank, w.weapon
"""

# Each weapon's perks, a column at a time in socket order, by share.
PERKS = """
SELECT side, weapon, kind, n_eff, credibility, confidence, hard_n_eff, hard_credibility,
       normal_n_eff, normal_credibility, perk, share, low, high,
       hard_share AS hard, normal_share AS normal
FROM v_roll_score
ORDER BY side, weapon, socket, kind != 'traits', kind, rank, perk
"""

PERK_FIELDS = ('perk', 'share', 'low', 'high', 'hard', 'normal')

# The file's format, raised on any change a consumer has to handle: a key
# renamed, removed or given a new meaning. Adding a key doesn't raise it.
SCHEMA_VERSION = 1


def group(n_eff, credibility) -> dict | None:
    # A group's measure of a column, or None when it has no votes there.
    return None if n_eff is None else {'n_eff': n_eff, 'credibility': credibility}


def build(conn) -> dict:
    # The scores as the published JSON holds them.
    scores = {
        'schema_version': SCHEMA_VERSION,
        'generated_at': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'settings': votes.settings(conn),
        'categories': [
            {**dict(r), 'hard': bool(r['hard'])}
            for r in conn.execute("SELECT key, label, side, weight, hard FROM activity_category")
        ],
        'pve': [],
        'pvp': [],
    }
    weapons = {}
    for r in conn.execute(WEAPONS):
        weapon = {
            k: r[k] for k in ('name', 'type', 'item_hash', 'rank', 'players', 'active_players')
        }
        weapon.update(
            family=r['family'],
            item_hashes=json.loads(r['item_hashes']),
            hard=bool(r['hard']),
            hard_weight=r['hard_weight'],
            groups={
                'hard': {'copies': r['hard_copies'], 'n_eff': r['hard_n_eff']},
                'normal': {'copies': r['normal_copies'], 'n_eff': r['normal_n_eff']},
            },
            last_seen=r['last_seen'],
            stale=bool(r['stale']),
            columns=[],
        )
        scores[r['side']].append(weapon)
        weapons[(r['side'], r['name'])] = weapon
    for r in conn.execute(PERKS):
        columns = weapons[(r['side'], r['weapon'])]['columns']
        if not columns or columns[-1]['kind'] != r['kind']:
            columns.append(
                {
                    'kind': r['kind'],
                    'n_eff': r['n_eff'],
                    'credibility': r['credibility'],
                    'confidence': r['confidence'],
                    'hard': group(r['hard_n_eff'], r['hard_credibility']),
                    'normal': group(r['normal_n_eff'], r['normal_credibility']),
                    'perks': [],
                }
            )
        columns[-1]['perks'].append({k: r[k] for k in PERK_FIELDS})
    return scores


def write(conn) -> bytes | None:
    # Build the scores, write them to paths.EXPORT_FILE and return its bytes;
    # None when no weapon has votes (nothing collected, or the manifest
    # tables are empty), which isn't worth publishing.
    scores = build(conn)
    if not scores['pve'] and not scores['pvp']:
        return None
    content = json.dumps(scores, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    paths.EXPORT_FILE.write_bytes(content)
    return content
