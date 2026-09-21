# data/raw/

Raw Riot API responses are not included in this repository due to their size (excluded via `.gitignore`).

| File/folder | Description | Approx. size |
|---|---|---|
| `matches_raw.jsonl` | Raw match JSON collected by `src/01_collect_matches.py` (one match per line) | ~420MB / 5,000 games |
| `timelines/{matchId}.json` | Raw per-match timeline collected by `src/02_collect_timelines.py` | a few hundred KB per match, 4,997 files total |
| `versions.json` | Snapshot of [Data Dragon versions.json](https://ddragon.leagueoflegends.com/api/versions.json), used to determine the target patch (N-1) | a few KB |

## Reproducing this data

```bash
export RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
curl -o data/raw/versions.json https://ddragon.leagueoflegends.com/api/versions.json

python src/01_collect_matches.py     # -> data/raw/matches_raw.jsonl
python src/02_collect_timelines.py   # -> data/raw/timelines/*.json
```

See the root `README.md` for how to turn this into the `data/interim/` and `data/processed/` tables.
