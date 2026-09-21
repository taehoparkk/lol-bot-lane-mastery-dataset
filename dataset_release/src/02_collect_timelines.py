"""Step 2: download the match timeline (event-by-event log) for every
match in data/raw/matches_raw.jsonl and save it as
data/raw/timelines/{matchId}.json.

Usage:
    export RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    python src/02_collect_timelines.py
"""
import json
import os

from tqdm import tqdm

from common import REGIONAL_ROUTING, RAW_MATCHES_FILE, RAW_TIMELINE_DIR, make_headers, safe_request


def iter_match_ids():
    with open(RAW_MATCHES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)["metadata"]["matchId"]


def get_timeline(match_id: str, headers: dict):
    url = f"https://{REGIONAL_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    return safe_request(url, headers)


def main():
    headers = make_headers()
    os.makedirs(RAW_TIMELINE_DIR, exist_ok=True)

    match_ids = list(iter_match_ids())
    for match_id in tqdm(match_ids, desc="timelines"):
        out_path = os.path.join(RAW_TIMELINE_DIR, f"{match_id}.json")
        if os.path.exists(out_path):
            continue

        timeline = get_timeline(match_id, headers)
        if timeline is None:
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False)

    print(f"[done] timelines saved under {RAW_TIMELINE_DIR}/")


if __name__ == "__main__":
    main()
