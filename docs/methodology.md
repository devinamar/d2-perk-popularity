# Methodology

Each score answers one question: across the copies of a weapon that players finished activities
with in the last 30 days, how often does each perk appear, with copies from harder content counting
for more? This is how the app gets there, and where it has to compromise.

## The data

Bungie's **post-game carnage report** (PGCR) for an activity lists each player, whether they
finished it, and the weapons they got kills with. Each weapon is listed only by its item definition
(`referenceId`, which tells the version, such as Adept or a reissue) and its kill counts. The report
has no instance id for the copy used, no perks and no loadout, and a weapon that got no kills isn't
listed at all.

The copy and its perks come from the player's **profile**, read through the API after the match:
what each character has equipped at that moment, with the perks plugged into each item. A player's
bags and vault show only when they've made their inventory public, which almost no one does (none
of 86 profiles sampled on 2026-10-23).

## Collecting

Collection is tuned for recency: the sooner a profile is read after a match, the likelier the player
still has the weapons they used equipped.

- **The report crawl (`--scan`), every 5 minutes.** PGCRs are numbered in order as activities end,
  about 20 a second. Each run finds the newest and walks back through the 3,000 before it, about
  half of what the game creates, reading each PGCR and sorting it into a category as it goes: an id
  doesn't say what activity it was. Hard content is always kept; normal content is sampled, up to 67
  PGCRs per category per run (`--per-category`), about 200 every 15 minutes. The players in a kept
  PGCR have their profiles read right away, minutes after the match.
- **The player crawl, by hand.** `--crawl N` reads players' activity histories (the well-known
  players in `extract/known_players.toml` first, then players seen in the data, hard content
  first) back to their last crawl or 7 days, and fetches the PGCRs they list. It reaches older
  matches, whose weapons match less often. The well-known players are the top of public
  leaderboards: RaidHub's world-first rankings (PvE), and Destiny Tracker's Trials of Osiris Elo
  and Warmind's flawless tickets (PvP); each entry in the file names its source.

A PGCR is kept when it falls into one of the categories below and at least one player finished it
with a weapon kill. Private matches, Sparrow Racing, patrols, story missions, lost sectors and The
Lawless Frontier aren't kept. Only players who finished count; in PvP, that means they were there
at the end.

| Category | Side | Weight | Hard |
| --- | --- | --- | --- |
| Master raid (Epic for The Desert Perpetual), or any raid run with Cutthroat Combat (Pantheon too) | PvE | 32 | yes |
| Grandmaster Vanguard Alert (the weekly fixed-difficulty Grandmaster strikes) | PvE | 16 | yes |
| Master dungeon | PvE | 8 | yes |
| Raid | PvE | 4 | |
| Dungeon | PvE | 2 | |
| Strikes and Portal (missions and Solo Ops at any tier among them) | PvE | 1 | |
| Trials of Osiris | PvP | 8 | yes |
| Competitive | PvP | 4 | yes |
| Regular playlist (Quickplay, Iron Banner and other public PvP) | PvP | 2 | |
| Gambit | PvP | 1 | |

The weight doubles with each step in difficulty. The steps are a judgment call, not something
measured from the data. The rules are in `db/schema/views/v_pgcr_category.sql`, the weights in
`db/schema/app/activity_category.sql`.

## Matching a weapon to its copy

For each player who finished, the app reads the profile once per run and matches each weapon they
used to a copy of the same version:

1. the copy equipped on the character that used it;
2. otherwise, the only copy of that version the profile shows: on another character, or in public
   bags or vault.

With two or more visible copies and none on that character, the use stays unmatched, since any of
them could be the one used.

**The accuracy compromise.** What gets scored is the copy the player has when the profile is read,
not a copy the report proves they used. Measured on 2026-10-23 over 162,854 weapon uses by players
who finished, with a once-a-day crawl and matching only the copy equipped on that character:

| Outcome | Share |
| --- | --- |
| Matched to a copy, so counted | 44% |
| Lost: the weapon was no longer equipped when the profile was read | 35% |
| Lost: the profile showed nothing (hidden or unreadable) | 21% |

Timing decides most of it. Reading the newest PGCRs catches minutes-old matches and matches about
70% of weapons; the once-a-day player crawl matched about 30%, and 27% in Trials and Master raids,
which came mostly from it. That's why collection now reads the newest PGCRs every 5 minutes. Reading
faster doesn't raise the rate further: an hour of nonstop scanning (2026-10-23) still matched 72%,
the rest being hidden profiles and players who changed loadout right after the match.

What this means for the scores:

- **Lost uses are dropped, not guessed.** Players who swap loadouts often, or hide their profiles,
  count for less than players who keep a loadout on.
- **The copy can be the wrong one.** With the vault private, the only visible copy of a version may
  not be the one used. The vote then goes to another copy the same player has equipped.
- **Perks are read, not reported.** Where a column offers two perks, the one recorded is the one
  plugged when the profile is read, which the player may have switched since the match.
- **Kills only.** A weapon used without a kill (only for boss damage, say) isn't in the report, so
  weapons in damage or support roles count for less.

## Votes

Each side has two groups, scored apart and then merged: **hard** (the categories marked hard above)
and **normal** (the rest). That makes four: hard PvE, normal PvE, hard PvP and normal PvP. Keeping
them apart stops normal content, which the report crawl samples far more of, from outvoting hard
content by sheer numbers.

- **One vote per copy, per group.** A copy counts once however many matches it was seen in, so ten
  Master raid clears with one copy are one vote. A copy used in both hard and normal content votes
  in each group. In practice that's one vote per player: extra copies of the same weapon hold under
  1% of the votes.
- **Weighted by the hardest content.** A vote weighs what the hardest category the copy was
  finished in weighs within its group, in the window.
- **Full clears count more.** In raids and dungeons, a copy used only in clears its player didn't
  make from the start (the run started from a checkpoint, or they joined more than 30 seconds in)
  weighs a third of its category's weight: full clears count three times as much, 75 to 25. A
  fireteam there from the start loads in within about 5 seconds; a late joiner shows up half a
  minute or more in. PGCRs stored before the scan read how their run started are read again,
  3,000 a run (`--catch-up N`), until none is left.
- **A rolling window, with a floor.** A copy counts while it was used in the last 30 days. Each
  weapon also keeps its 100 newest copies, however old: a weapon that drops out of use keeps its
  last known scores, flagged **stale** (no carnage entries in 30 days), and a rarely used one
  collects every copy seen, up to 100.

## Scores

Per weapon, column and group, then merged per side:

- **Columns.** Barrels (and scopes, tubes, bowstrings, blades, hafts), magazines (and batteries,
  arrows, guards), stocks, grips and origin traits are each scored on their own. The two trait
  columns are scored together, as a combo such as "Rewind Rounds + Elemental Honing" (kind
  `traits`), and each trait is also scored on its own (`trait1`, `trait2`, in socket order), for
  showing or ordering the traits singly. A column is scored only where the weapon offers a choice,
  so the intrinsic frame and fixed exotic perks aren't, and most exotics have no columns. A
  fixed-roll copy of a weapon that otherwise rolls (a quest or curated version) still counts: its
  player chose to run it. Where a weapon's versions split by traits (see Grouping), a fixed version
  that didn't come out with one of the pools is a weapon of its own.
- **A group's score.** A perk's share is its part of the column's weighted votes in the group.
  Unequal weights make a sample worth less than its count, so each column gets an effective sample
  size, Kish's n_eff = (Σw)² / Σw², and from it a credibility score, n_eff / (n_eff + 30): 0.25 at
  10 effective votes, 0.5 at 30, 0.77 at 100.
- **The merge.** Hard's part of a column is 0.75 times its credibility, normal's 0.25 times its
  own, the two then scaled to add up to 1, and the merged share is each group's share times its
  part. Two well-measured groups so split a score about 75/25, while a thin group counts for
  little: a single Master raid copy can't outvote 200 normal players. This is credibility
  weighting, as insurers use to blend a small sample with a large one.
- **Range and confidence.** The merged score's effective sample size is 1 / Σ (part² / the group's
  n_eff). Its 95% Wilson range (`low` to `high`), credibility and grade (high from 100, medium from
  30, low from 10, very low below) come from it.
- **Hard flag.** A weapon is flagged hard when hard content holds at least half of its merged
  scores, so they're mostly hard content's. A weapon seen only in hard content is flagged however
  few its copies, so read the flag with the confidence.
- **Rank.** Weapons rank by popularity: 0.75 times their share of the side's hard-content votes,
  plus 0.25 times their share of its normal votes, over active copies, then all copies.
- **Grouping.** A weapon's versions (Adept, Timelost, Harrowed, reissued) count as one weapon while
  they roll the same traits: the same perks in both trait columns, by name, or the same release and
  source (an Adept a perk off its base). An enhanced perk counts with its base perk. Where two or
  more versions roll different traits, each pool is a weapon of its own, named after its source, as
  "Zaouli's Bane (King's Fall)" and "Zaouli's Bane (Pantheon)", or after its season when the
  sources don't tell the pools apart, with a number when a name would repeat. A fixed-roll version
  never splits a weapon on its own. Each manifest ingest redoes the grouping (`extract/versions.py`).

For example, Found Verdict (Episode: Heresy)'s PvP magazine in the data of 2026-10-23:

| | Effective votes | Credibility | Part | Accurized Rounds |
| --- | --- | --- | --- | --- |
| Hard (Trials, Competitive) | 46.5 | 0.61 | 0.70 | 0.815 |
| Normal (Quickplay, Gambit) | 109.9 | 0.79 | 0.30 | 0.718 |
| Merged | 88.3 | 0.75 | | **0.786** (0.690 to 0.859) |

A thin group, from the same data: Mint Retrograde (Echoes Core)'s PvP barrel had one Trials copy,
with Countermass, against 95 normal copies led by Volatile Launch at 0.333. That single copy's
credibility is 0.03, so hard gets 11% of the column, and Volatile Launch still leads, at 0.295 to
Countermass's 0.201.

## Other limits

- **A sample, not a census.** The report crawl reads about half of all PGCRs, at random, so it sees
  each kind of play roughly in proportion, but it counts only players who finished, with a profile
  that shows the weapon. The weights rank content by difficulty; they don't correct for who gets
  sampled.
- **The groups overlap.** A copy used in both hard and normal content votes in each, so the merged
  range is a little narrower than it should be.
- **Thin data.** Most weapons have few copies: in the 2026-10-22 file, 1,701 of 1,972 PvE columns
  were graded very low. Read a share with its range and confidence.
- **New activities.** Categories come from rules on an activity's type, modes, difficulty tier and
  feats. An activity the rules don't recognize isn't kept until they're updated.

## Settings

The policy is in `db/schema/app/setting.sql`:

| Setting | Value | Meaning |
| --- | --- | --- |
| `window_days` | 30 | a copy is active while used in this many days |
| `rescue_copies` | 100 | each weapon keeps its newest copies up to this many, however old |
| `raw_days` | 14 | raw PGCR rows are kept this long (votes are folded first) |
| `full_clear_weight` | 0.75 | a full clear's part against a checkpoint clear's in raids and dungeons |
| `late_join_seconds` | 30 | a player who joins a run later than this didn't clear it from the start |
| `hard_weight` | 0.75 | hard content's part of a side's scores when both groups are well measured |
| `credibility_k` | 30 | a group's credibility is n_eff / (n_eff + this): its part shrinks with it |
