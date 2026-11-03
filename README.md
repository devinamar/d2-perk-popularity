# Destiny 2 Perk Popularity

Which perks Destiny 2 players actually use, scored per weapon for PvE and PvP, with harder content
counting for more. Published every Monday as `perk_scores.json` on this repo's
[`data` branch](https://github.com/devinamar/d2-perk-popularity/tree/data), free to use:

```bash
curl -fsSLO https://raw.githubusercontent.com/devinamar/d2-perk-popularity/data/perk_scores.json
```

## How it works

- **Collecting.** Bungie's match reports say who finished and which weapons got kills, but not their
  perks, so the app reads each player's equipped loadout minutes after the match. Every 5 minutes it
  reads the newest 3,000 reports, keeping all hard content and a sample of the rest. About 70% of
  weapon uses match a copy; the rest are dropped, not guessed.
- **Votes.** Each copy votes once per group (hard or normal, per side), weighted by the hardest
  content it finished in 30 days: from 1 (strikes, Gambit) to 32 (Master raids). Full raid and
  dungeon clears count three times a checkpoint clear. A weapon keeps its 100 newest copies, so one
  that falls out of use keeps its last scores, marked stale.
- **Scores.** A perk's share is its part of a column's weighted votes. Hard and normal content are
  scored apart and merged by credibility, about 75/25 when both are well measured. Every share has a
  95% Wilson range and a confidence grade; most weapons have few copies, so read the range too.

Full method, compromises and settings: [docs/methodology.md](docs/methodology.md).

## The data

One JSON object, aggregates only (no player or copy ids):

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-26T08:31:00Z",
  "settings": {"window_days": 30, "rescue_copies": 100, "raw_days": 14, "full_clear_weight": 0.75, "late_join_seconds": 30, "hard_weight": 0.75, "credibility_k": 30},
  "categories": [{"key": "raid_master", "label": "Master raid", "side": "pve", "weight": 32, "hard": true}],
  "pve": [],
  "pvp": [
    {"name": "Found Verdict (Episode: Heresy)", "type": "Shotgun", "item_hash": 694500607, "rank": 48,
     "players": 157, "active_players": 157, "family": "Found Verdict",
     "item_hashes": [694500607, 851296754], "hard": true, "hard_weight": 0.699,
     "groups": {"hard": {"copies": 47, "n_eff": 46.5}, "normal": {"copies": 113, "n_eff": 109.9}},
     "last_seen": "2026-10-23T22:13:09Z", "stale": false,
     "columns": [
       {"kind": "magazine", "n_eff": 88.3, "credibility": 0.75, "confidence": "medium",
        "hard": {"n_eff": 46.5, "credibility": 0.61}, "normal": {"n_eff": 109.9, "credibility": 0.79},
        "perks": [
          {"perk": "Accurized Rounds", "share": 0.786, "low": 0.69, "high": 0.859, "hard": 0.815, "normal": 0.718},
          {"perk": "Assault Mag", "share": 0.082, "low": 0.041, "high": 0.159, "hard": 0.065, "normal": 0.122}]}]}
  ]
}
```

| Key | Meaning |
| --- | --- |
| `schema_version` | Goes up when a key is renamed, removed or changes meaning |
| `settings`, `categories` | The policy and activity categories (`weight`, `hard`) behind the scores |
| `pve`, `pvp` | Weapons in rank order |
| `players`, `active_players` | Copies counted; those used in the last 30 days |
| `groups`, `hard_weight` | Each group's `copies` and `n_eff`; hard content's part of the scores |
| `family`, `item_hash`, `item_hashes` | Shared name; the version most copies are; every version scored |
| `stale` | No carnage entries in 30 days |
| `columns` | Socket order. `kind`: `barrel`, `magazine`, `stock`, `grip`, `origin`, `traits`, `trait1`, `trait2`. Most exotics have none |
| column `confidence`, `hard`, `normal` | `high` / `medium` / `low` / `very low`; each group's `n_eff` and `credibility` (null if no votes) |
| `perks` | `share`, its 95% range `low`–`high`, and its share in each group, `hard` and `normal` |

## Running it

Local runs, running it as a service with Docker, and the code layout:
[docs/deployment.md](docs/deployment.md).

## License

MIT; see [LICENSE](LICENSE).
