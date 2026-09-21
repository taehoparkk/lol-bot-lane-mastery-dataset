"""Step 3: for each match/team, find the ADC (BOTTOM) and Support (UTILITY)
players and look up their champion-mastery score for the champion they
played, via champion-mastery-v4.

Writes data/interim/team_champion_mastery.csv with one row per
(matchId, teamId):

    matchId, teamId, win,
    adc_championName, adc_masteryPoints, adc_masteryLevel,
    support_championName, support_masteryPoints, support_masteryLevel

Note: puuid is intentionally *not* written to the output file. Riot's
developer policies treat puuid as a player identifier that should not be
redistributed in a public dataset, so it is dropped as soon as the
mastery lookup that needs it is done.

Usage:
    export RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    python src/03_extract_team_mastery.py
"""
import csv
import json
import os

from tqdm import tqdm

from common import PLATFORM_ROUTING, RAW_MATCHES_FILE, INTERIM_DIR, ROLE_ADC, ROLE_SUPPORT
from common import make_headers, safe_request, participant_role

OUT_FILE = os.path.join(INTERIM_DIR, "team_champion_mastery.csv")

FIELDNAMES = [
    "matchId", "teamId", "win",
    "adc_championName", "adc_masteryPoints", "adc_masteryLevel",
    "support_championName", "support_masteryPoints", "support_masteryLevel",
]


def get_champion_mastery(puuid: str, champion_id: int, headers: dict):
    url = (
        f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/champion-mastery/v4/"
        f"champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}"
    )
    return safe_request(url, headers)


def iter_matches():
    with open(RAW_MATCHES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def main():
    headers = make_headers()
    os.makedirs(INTERIM_DIR, exist_ok=True)

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=FIELDNAMES)
        writer.writeheader()

        for match in tqdm(list(iter_matches()), desc="team mastery"):
            match_id = match["metadata"]["matchId"]
            info = match["info"]
            participants = info["participants"]
            teams = {t["teamId"]: t["win"] for t in info["teams"]}

            for team_id in (100, 200):
                team_players = [p for p in participants if p["teamId"] == team_id]
                adc = next((p for p in team_players if participant_role(p) == ROLE_ADC), None)
                support = next((p for p in team_players if participant_role(p) == ROLE_SUPPORT), None)
                if adc is None or support is None:
                    continue

                adc_mastery = get_champion_mastery(adc["puuid"], adc["championId"], headers)
                support_mastery = get_champion_mastery(support["puuid"], support["championId"], headers)

                writer.writerow({
                    "matchId": match_id,
                    "teamId": team_id,
                    "win": teams.get(team_id),
                    "adc_championName": adc["championName"],
                    "adc_masteryPoints": adc_mastery.get("championPoints") if adc_mastery else "",
                    "adc_masteryLevel": adc_mastery.get("championLevel") if adc_mastery else "",
                    "support_championName": support["championName"],
                    "support_masteryPoints": support_mastery.get("championPoints") if support_mastery else "",
                    "support_masteryLevel": support_mastery.get("championLevel") if support_mastery else "",
                })

    print(f"[done] -> {OUT_FILE}")


if __name__ == "__main__":
    main()
