"""Step 1: collect raw ranked-solo match data for the previous patch.

Queries league-v4 (tier -> puuid) and match-v5 (puuid -> match ids -> match
detail), keeps only games on patch N-1 that lasted >= 5 minutes (i.e. not a
remake), and appends each raw match JSON as one line of
data/raw/matches_raw.jsonl.

This mirrors the original riot_api.ipynb collection notebook, with the
hardcoded API key replaced by the RIOT_API_KEY environment variable and
the output path pointed at data/raw/.

Usage:
    export RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    python src/01_collect_matches.py
"""
import json
import os

import requests

from common import PLATFORM_ROUTING, REGIONAL_ROUTING, RAW_MATCHES_FILE, make_headers, safe_request

LOCAL_VERSIONS_FILE = "data/raw/versions.json"  # from https://ddragon.leagueoflegends.com/api/versions.json

# ~5,000 matches total: high tiers (60%) + mid/low tiers (40%)
TIER_TARGETS = {
    "CHALLENGER": 750,
    "GRANDMASTER": 750,
    "MASTER": 750,
    "DIAMOND": 750,
    "EMERALD": 400,
    "PLATINUM": 400,
    "GOLD": 400,
    "SILVER": 300,
    "BRONZE": 300,
    "IRON": 200,
}


def get_target_patch_version(headers: dict) -> str:
    """Patch N-1 (Major.Minor) from a local Data Dragon versions.json."""
    if not os.path.exists(LOCAL_VERSIONS_FILE):
        raise FileNotFoundError(
            f"'{LOCAL_VERSIONS_FILE}' not found. Download it from "
            "https://ddragon.leagueoflegends.com/api/versions.json and place it there."
        )
    with open(LOCAL_VERSIONS_FILE, "r", encoding="utf-8") as f:
        versions = json.load(f)
    target_full = versions[1]
    return ".".join(target_full.split(".")[:2])


def get_puuids_by_tier(tier: str, headers: dict, needed_puuids: int) -> list:
    if tier in ("CHALLENGER", "GRANDMASTER", "MASTER"):
        endpoint = {
            "CHALLENGER": "challengerleagues",
            "GRANDMASTER": "grandmasterleagues",
            "MASTER": "masterleagues",
        }[tier]
        url = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/league/v4/{endpoint}/by-queue/RANKED_SOLO_5x5"
        data = safe_request(url, headers)
        entries = data.get("entries", []) if data else []
        return [e["puuid"] for e in entries if "puuid" in e][:needed_puuids]

    puuids = []
    for division in ("I", "II"):
        page = 1
        while len(puuids) < needed_puuids and page <= 10:
            url = (
                f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/league/v4/entries/"
                f"RANKED_SOLO_5x5/{tier}/{division}?page={page}"
            )
            entries = safe_request(url, headers)
            if not entries:
                break
            puuids.extend(e["puuid"] for e in entries if "puuid" in e)
            page += 1
    return puuids[:needed_puuids]


def get_match_ids_by_puuid(puuid: str, headers: dict, count: int = 25) -> list:
    url = (
        f"https://{REGIONAL_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/"
        f"{puuid}/ids?queue=420&type=ranked&start=0&count={count}"
    )
    return safe_request(url, headers) or []


def get_match_detail(match_id: str, headers: dict):
    url = f"https://{REGIONAL_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    return safe_request(url, headers)


def load_collected_ids() -> set:
    collected = set()
    if os.path.exists(RAW_MATCHES_FILE):
        with open(RAW_MATCHES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    collected.add(json.loads(line)["metadata"]["matchId"])
                except (KeyError, json.JSONDecodeError):
                    continue
    return collected


def main():
    headers = make_headers()
    target_patch = get_target_patch_version(headers)
    patch_prefix = f"{target_patch}."

    collected_ids = load_collected_ids()
    print(f"[*] {len(collected_ids)} matches already collected, resuming.")

    os.makedirs(os.path.dirname(RAW_MATCHES_FILE), exist_ok=True)
    with open(RAW_MATCHES_FILE, "a", encoding="utf-8") as out_file:
        for tier, target_count in TIER_TARGETS.items():
            tier_puuids = get_puuids_by_tier(tier, headers, needed_puuids=max(60, target_count // 5 + 30))
            tier_collected = 0

            for puuid in tier_puuids:
                if tier_collected >= target_count:
                    break
                for match_id in get_match_ids_by_puuid(puuid, headers):
                    if tier_collected >= target_count:
                        break
                    if match_id in collected_ids:
                        continue

                    detail = get_match_detail(match_id, headers)
                    if not detail or "info" not in detail:
                        continue

                    game_info = detail["info"]
                    if not game_info.get("gameVersion", "").startswith(patch_prefix):
                        continue
                    if game_info.get("gameDuration", 0) < 300:  # drop remakes
                        continue

                    detail["custom_collected_tier"] = tier
                    detail["custom_target_patch"] = target_patch
                    out_file.write(json.dumps(detail, ensure_ascii=False) + "\n")
                    out_file.flush()

                    collected_ids.add(match_id)
                    tier_collected += 1

            print(f"[+] {tier}: {tier_collected}/{target_count} collected.")

    print(f"[done] {len(collected_ids)} matches total -> {RAW_MATCHES_FILE}")


if __name__ == "__main__":
    main()
