"""Step 4: turn each match timeline into per-team laning-phase stats.

Definition used for "end of laning phase": the timestamp of the first bot
lane tower (BUILDING_KILL, buildingType=TOWER_BUILDING, laneType=BOT_LANE)
destroyed in the game. The team that destroyed it "wins" the lane
(laneOutcome=WIN), the team that owned it "loses" (laneOutcome=LOSE).
Matches where neither team's bot lane tower falls are skipped (no lane
resolution event).

For each (matchId, teamId), counts every CHAMPION_KILL / ELITE_MONSTER_KILL
/ WARD_PLACED event up to that timestamp and attributes it to a role (ADC /
Support / Jungle) using the role each participant was assigned in the raw
match data (participants[].teamPosition).

Writes data/interim/team_lane_events.csv:

    matchId, teamId, laneOutcome, laneEventTimestampMs, laneEventTimestampMin,
    adc_kills, adc_deaths, support_kills, support_deaths, support_wardsPlaced,
    jungle_kills, jungle_deaths, team_hordeKills, team_dragonKills

Usage:
    python src/04_build_lane_events.py
"""
import csv
import json
import os

from tqdm import tqdm

from common import RAW_MATCHES_FILE, RAW_TIMELINE_DIR, INTERIM_DIR
from common import ROLE_ADC, ROLE_SUPPORT, ROLE_JUNGLE, participant_role

OUT_FILE = os.path.join(INTERIM_DIR, "team_lane_events.csv")

FIELDNAMES = [
    "matchId", "teamId", "laneOutcome", "laneEventTimestampMs", "laneEventTimestampMin",
    "adc_kills", "adc_deaths", "support_kills", "support_deaths", "support_wardsPlaced",
    "jungle_kills", "jungle_deaths", "team_hordeKills", "team_dragonKills",
]


def iter_matches():
    with open(RAW_MATCHES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def find_first_bot_tower_event(frames):
    for frame in frames:
        for event in frame["events"]:
            if (
                event["type"] == "BUILDING_KILL"
                and event.get("buildingType") == "TOWER_BUILDING"
                and event.get("laneType") == "BOT_LANE"
            ):
                return event
    return None


def build_role_maps(participants):
    """participantId -> (teamId, role) using the raw match participant list."""
    return {p["participantId"]: (p["teamId"], participant_role(p)) for p in participants}


def main():
    os.makedirs(INTERIM_DIR, exist_ok=True)

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=FIELDNAMES)
        writer.writeheader()

        for match in tqdm(list(iter_matches()), desc="lane events"):
            match_id = match["metadata"]["matchId"]
            timeline_path = os.path.join(RAW_TIMELINE_DIR, f"{match_id}.json")
            if not os.path.exists(timeline_path):
                continue

            with open(timeline_path, "r", encoding="utf-8") as f:
                timeline = json.load(f)
            frames = timeline["info"]["frames"]

            role_map = build_role_maps(match["info"]["participants"])

            tower_event = find_first_bot_tower_event(frames)
            if tower_event is None:
                continue  # no bot lane tower fell -> lane outcome undefined

            cutoff_ms = tower_event["timestamp"]
            losing_team = tower_event["teamId"]  # team whose tower was destroyed
            winning_team = 200 if losing_team == 100 else 100

            stats = {
                100: {"adc_kills": 0, "adc_deaths": 0, "support_kills": 0, "support_deaths": 0,
                      "jungle_kills": 0, "jungle_deaths": 0, "support_wardsPlaced": 0,
                      "team_hordeKills": 0, "team_dragonKills": 0},
                200: {"adc_kills": 0, "adc_deaths": 0, "support_kills": 0, "support_deaths": 0,
                      "jungle_kills": 0, "jungle_deaths": 0, "support_wardsPlaced": 0,
                      "team_hordeKills": 0, "team_dragonKills": 0},
            }

            for frame in frames:
                for event in frame["events"]:
                    ts = event.get("timestamp")
                    if ts is None or ts > cutoff_ms:
                        continue

                    etype = event["type"]

                    if etype == "CHAMPION_KILL":
                        killer_team, killer_role = role_map.get(event.get("killerId"), (None, None))
                        victim_team, victim_role = role_map.get(event.get("victimId"), (None, None))
                        if killer_role == ROLE_ADC:
                            stats[killer_team]["adc_kills"] += 1
                        elif killer_role == ROLE_SUPPORT:
                            stats[killer_team]["support_kills"] += 1
                        elif killer_role == ROLE_JUNGLE:
                            stats[killer_team]["jungle_kills"] += 1
                        if victim_role == ROLE_ADC:
                            stats[victim_team]["adc_deaths"] += 1
                        elif victim_role == ROLE_SUPPORT:
                            stats[victim_team]["support_deaths"] += 1
                        elif victim_role == ROLE_JUNGLE:
                            stats[victim_team]["jungle_deaths"] += 1

                    elif etype == "WARD_PLACED":
                        creator_team, creator_role = role_map.get(event.get("creatorId"), (None, None))
                        if creator_role == ROLE_SUPPORT:
                            stats[creator_team]["support_wardsPlaced"] += 1

                    elif etype == "ELITE_MONSTER_KILL":
                        killer_team = event.get("killerTeamId")
                        if killer_team not in (100, 200):
                            continue
                        if event.get("monsterType") == "HORDE":
                            stats[killer_team]["team_hordeKills"] += 1
                        elif event.get("monsterType") == "DRAGON":
                            stats[killer_team]["team_dragonKills"] += 1

            for team_id in (100, 200):
                s = stats[team_id]
                writer.writerow({
                    "matchId": match_id,
                    "teamId": team_id,
                    "laneOutcome": "WIN" if team_id == winning_team else "LOSE",
                    "laneEventTimestampMs": cutoff_ms,
                    "laneEventTimestampMin": round(cutoff_ms / 60000, 2),
                    **s,
                })

    print(f"[done] -> {OUT_FILE}")


if __name__ == "__main__":
    main()
