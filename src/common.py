"""Shared helpers for the collection / preprocessing scripts.

All scripts read the Riot API key from the RIOT_API_KEY environment
variable -- never hardcode it in source files that get committed.
"""
import os
import time

import requests

PLATFORM_ROUTING = "kr"    # league-v4, champion-mastery-v4
REGIONAL_ROUTING = "asia"  # match-v5

RAW_MATCHES_FILE = "data/raw/matches_raw.jsonl"
RAW_TIMELINE_DIR = "data/raw/timelines"
INTERIM_DIR = "data/interim"
PROCESSED_DIR = "data/processed"

ROLE_ADC = "BOTTOM"
ROLE_SUPPORT = "UTILITY"
ROLE_JUNGLE = "JUNGLE"


def get_api_key() -> str:
    api_key = os.environ.get("RIOT_API_KEY")
    if not api_key:
        raise RuntimeError(
            "RIOT_API_KEY environment variable is not set. "
            "Get a key at https://developer.riotgames.com/ and "
            "export RIOT_API_KEY=... before running this script."
        )
    return api_key


def make_headers() -> dict:
    return {
        "X-Riot-Token": get_api_key(),
        "User-Agent": "Mozilla/5.0 (Data-Collector)",
    }


def safe_request(url: str, headers: dict):
    """GET with 429 backoff and basic network-error retry."""
    while True:
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                return res.json()
            if res.status_code == 429:
                retry_after = int(res.headers.get("Retry-After", 5))
                print(f"[*] Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            if res.status_code == 404:
                return None
            print(f"[!] HTTP {res.status_code} for {url}")
            return None
        except requests.exceptions.RequestException as exc:
            print(f"[!] Network error, retrying: {exc}")
            time.sleep(3)


def participant_role(participant: dict) -> str:
    """TOP / JUNGLE / MIDDLE / BOTTOM / UTILITY, with a fallback field."""
    return participant.get("teamPosition") or participant.get("individualPosition") or ""
