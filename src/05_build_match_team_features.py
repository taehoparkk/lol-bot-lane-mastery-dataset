"""Step 5: merge the two interim tables into the final modeling table.

data/interim/team_lane_events.csv (laning-phase stats, from the timeline)
    + data/interim/team_champion_mastery.csv (ADC/Support mastery, from
      champion-mastery-v4)
    --merge on (matchId, teamId)-->
data/processed/match_team_features.csv

Column layout matches the original match_team_full.csv exactly (see
README.md for the column dictionary); nothing here renames or transforms
those columns further.

Usage:
    python src/05_build_match_team_features.py
"""
import os

import pandas as pd

from common import INTERIM_DIR, PROCESSED_DIR

LANE_EVENTS_FILE = os.path.join(INTERIM_DIR, "team_lane_events.csv")
MASTERY_FILE = os.path.join(INTERIM_DIR, "team_champion_mastery.csv")
OUT_FILE = os.path.join(PROCESSED_DIR, "match_team_features.csv")

OUTPUT_COLUMNS = [
    "matchId", "teamId", "win", "laneEventTimestampMs", "laneOutcome",
    "adc_kills", "adc_deaths", "support_kills", "support_deaths",
    "jungle_kills", "jungle_deaths", "support_wardsPlaced",
    "team_hordeKills", "team_dragonKills",
    "adc_masteryPoints", "support_masteryPoints",
]


def main():
    lane = pd.read_csv(LANE_EVENTS_FILE)
    mastery = pd.read_csv(MASTERY_FILE)

    merged = lane.merge(
        mastery[["matchId", "teamId", "win", "adc_masteryPoints", "support_masteryPoints"]],
        on=["matchId", "teamId"],
        how="inner",
    )

    merged = merged[OUTPUT_COLUMNS]

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    merged.to_csv(OUT_FILE, index=False)
    print(f"[done] {merged.shape} -> {OUT_FILE}")


if __name__ == "__main__":
    main()
