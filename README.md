# LoL Bot-Lane Mastery & Laning-Phase Dataset

A dataset collected and processed to analyze how **ADC/Support champion mastery** and
**laning-phase (bot lane) stats** relate to game outcome in League of Legends solo-queue
matches. Collected via the official Riot Games API (MATCH-V5, LEAGUE-V4, CHAMPION-MASTERY-V4).

## Overview

- Region: KR (Korea server), Queue: Ranked Solo/Duo (`queue=420`)
- Patch: fixed to a single patch, one version behind the latest at collection time (N-1)
- Tier mix: ~60% high tiers (Challenger through Diamond) + ~40% mid/low tiers, ~5,000 games total

| Tier | Target games |
|---|---:|
| CHALLENGER | 750 |
| GRANDMASTER | 750 |
| MASTER | 750 |
| DIAMOND | 750 |
| EMERALD | 400 |
| PLATINUM | 400 |
| GOLD | 400 |
| SILVER | 300 |
| BRONZE | 300 |
| IRON | 200 |

Games shorter than 5 minutes (remakes) were excluded during collection.

## Folder structure

```
dataset_release/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                        # raw API responses (not included in the repo, see its README)
│   │   └── README.md
│   ├── interim/                    # intermediate outputs derived from raw data
│   │   ├── team_champion_mastery.csv
│   │   └── team_lane_events.csv
│   └── processed/                  # final modeling-ready table
│       └── match_team_features.csv
└── src/                             # pipeline scripts: raw -> interim -> processed
    ├── common.py
    ├── 01_collect_matches.py
    ├── 02_collect_timelines.py
    ├── 03_extract_team_mastery.py
    ├── 04_build_lane_events.py
    └── 05_build_match_team_features.py
```

## Pipeline

```
[Riot API]
   │  league-v4 (puuids per tier) + match-v5 (match ids/details)
   ▼
data/raw/matches_raw.jsonl ───────────────┐   (01_collect_matches.py)
   │  match-v5 timeline                    │
   ▼                                       │
data/raw/timelines/{matchId}.json          │   (02_collect_timelines.py)
   │                                       │
   │ champion-mastery-v4 (ADC/SUP puuid+championId)
   ▼                                       │
data/interim/team_champion_mastery.csv     │   (03_extract_team_mastery.py)
                                            │
data/interim/team_lane_events.csv  ◄───────┘   (04_build_lane_events.py, timeline event aggregation)
   │
   ▼  merge on (matchId, teamId)
data/processed/match_team_features.csv         (05_build_match_team_features.py)
```

1. **`01_collect_matches.py`** — gathers puuids per tier from league-v4, then queries match-v5 for
   those players' ranked matches, keeping only games on the target patch that lasted 5+ minutes,
   appended to `data/raw/matches_raw.jsonl`.
2. **`02_collect_timelines.py`** — calls the match-v5 timeline endpoint for each `matchId` and saves
   it to `data/raw/timelines/{matchId}.json` (kills, objectives, wards, tower kills, etc.).
3. **`03_extract_team_mastery.py`** — finds the participant with `teamPosition` `BOTTOM` (ADC) and
   `UTILITY` (Support) for each team, then looks up their champion-mastery score (points/level) for
   the champion they played via champion-mastery-v4. **puuid is used only for the lookup and is not
   written to the output file** (see the privacy section below).
4. **`04_build_lane_events.py`** — defines "end of laning phase" as the timestamp of **the first bot
   lane tower destroyed**, then aggregates kills/deaths (ADC/Support/Jungle), Support ward placements,
   and team Dragon/Horde kills up to that timestamp, per team.
5. **`05_build_match_team_features.py`** — merges the two interim tables on `(matchId, teamId)` into
   the final modeling table (`match_team_features.csv`).

> **Note**: the `src/` scripts are a reference re-implementation built from the meaning of each CSV
> column and the original collection notebook (`riot_api.ipynb`). Running them reproduces data that
> follows the same definitions, but is not guaranteed to be row-for-row identical to the original.
> The CSV files actually included under `data/interim` and `data/processed` carry the original values
> as-is (aside from the removed puuid column).

## Data files

### `data/interim/team_champion_mastery.csv`
Per-match, per-team ADC/Support champion mastery. Does not include the account identifier (puuid).

| Column | Description |
|---|---|
| `matchId` | Match ID |
| `teamId` | 100 (blue) / 200 (red) |
| `win` | Whether this team won the game |
| `adc_championName` | Champion played by the ADC |
| `adc_masteryPoints` | ADC's mastery points on that champion |
| `adc_masteryLevel` | ADC's mastery level on that champion |
| `support_championName` | Champion played by the Support |
| `support_masteryPoints` | Support's mastery points on that champion |
| `support_masteryLevel` | Support's mastery level on that champion |

### `data/interim/team_lane_events.csv`
Per-match, per-team laning-phase (bot lane) stats.

| Column | Description |
|---|---|
| `matchId` / `teamId` | Same as above |
| `laneOutcome` | `WIN`/`LOSE` — the team that destroys the first bot lane tower gets `WIN` |
| `laneEventTimestampMs` | Timestamp (ms) the first bot lane tower was destroyed |
| `laneEventTimestampMin` | Same timestamp in minutes, 2 decimal places |
| `adc_kills` / `adc_deaths` | ADC kills/deaths up to the end of the laning phase |
| `support_kills` / `support_deaths` | Support kills/deaths up to the end of the laning phase |
| `support_wardsPlaced` | Support's ward placements up to the end of the laning phase |
| `jungle_kills` / `jungle_deaths` | Jungler kills/deaths up to the end of the laning phase |
| `team_hordeKills` | Team's Void Grub (Horde) kills up to the end of the laning phase |
| `team_dragonKills` | Team's Dragon kills up to the end of the laning phase |

### `data/processed/match_team_features.csv`
Final modeling table, merging the two tables above.

`matchId, teamId, win, laneEventTimestampMs, laneOutcome, adc_kills, adc_deaths, support_kills, support_deaths, jungle_kills, jungle_deaths, support_wardsPlaced, team_hordeKills, team_dragonKills, adc_masteryPoints, support_masteryPoints`

## Privacy and usage policy

- `puuid` (Riot account identifier) is **not included** in this repository. Publicly distributing an
  identifier that can be tied back to a player account is discouraged under Riot's Developer Policies.
- No summoner names, IGNs, or other account-identifying information are included either.
- This project isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or
  anyone officially involved in producing or managing League of Legends. League of Legends and Riot
  Games are trademarks or registered trademarks of Riot Games, Inc.
  (see [Riot Games Developer Policies](https://developer.riotgames.com/policies/general))
- The original match/timeline data is subject to the Riot API Terms of Use; check the latest terms
  before redistributing anything beyond what's here. This repository only publishes derived
  statistics (`data/interim`, `data/processed`) and excludes the raw API responses.
- Code in this repository (src/) is released under the MIT License (see LICENSE); this does not extend to the dataset files below, which remain subject to the terms noted here.

## Setup

```bash
pip install -r requirements.txt
```

To re-collect the raw data yourself, get an API key from the
[Riot Developer Portal](https://developer.riotgames.com/) and set it as an environment variable
(never hardcode it in source):

```bash
export RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
