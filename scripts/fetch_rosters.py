from pathlib import Path
from datetime import datetime, timezone
import io
import pandas as pd
from espn import get_text

now = datetime.now(timezone.utc)
YEAR = now.year if now.month >= 3 else now.year - 1

NFLVERSE_PLAYERS = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
NFLVERSE_ROSTER = "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{year}.csv"

DATA = Path("data")
DATA.mkdir(exist_ok=True)

STATUS_MAP = {
    "ACT": "Active",
    "RES": "Reserve/IR",
    "INA": "Inactive",
    "CUT": "Cut",
    "RET": "Retired",
    "DEV": "Practice Squad",
    "E14": "Exempt",
}

def read_csv_url(url):
    raw = get_text(url, sleep=0.2)
    if not raw or len(raw) < 50:
        print("missing or empty", url)
        return None
    return pd.read_csv(io.BytesIO(raw), dtype=str)

def clean_id(val):
    if val is None or str(val).strip() in ("", "nan", "None"):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def main():
    players = read_csv_url(NFLVERSE_PLAYERS)
    if players is not None:
        players.to_csv(DATA / "nflverse_players.csv", index=False)
        print("nflverse players", len(players))

    roster = read_csv_url(NFLVERSE_ROSTER.format(year=YEAR))
    if roster is None:
        roster = read_csv_url(NFLVERSE_ROSTER.format(year=YEAR - 1))
    if roster is None:
        raise SystemExit("Could not download nflverse roster")

    roster.to_csv(DATA / "nflverse_roster.csv", index=False)
    print("nflverse roster", len(roster))

    out = pd.DataFrame({
        "espn_id": roster.get("espn_id", pd.Series(dtype=str)).map(clean_id),
        "gsis_id": roster.get("gsis_id", pd.Series(dtype=str)).map(clean_id),
        "sleeper_id": roster.get("sleeper_id", pd.Series(dtype=str)).map(clean_id),
        "pfr_id": roster.get("pfr_id", pd.Series(dtype=str)).map(clean_id),
        "yahoo_id": roster.get("yahoo_id", pd.Series(dtype=str)).map(clean_id),
        "rotowire_id": roster.get("rotowire_id", pd.Series(dtype=str)).map(clean_id),
        "full_name": roster.get("full_name"),
        "first_name": roster.get("first_name"),
        "last_name": roster.get("last_name"),
        "position": roster.get("position"),
        "depth_chart_position": roster.get("depth_chart_position"),
        "team_abbr": roster.get("team"),
        "jersey": roster.get("jersey_number"),
        "status_raw": roster.get("status"),
        "status": roster.get("status").map(lambda x: STATUS_MAP.get(str(x), x) if pd.notna(x) else ""),
        "years_exp": roster.get("years_exp"),
        "college": roster.get("college"),
        "headshot": roster.get("headshot_url"),
        "season": roster.get("season"),
    })

    # keep current-season active-ish players first; still write everyone
    out.to_csv(DATA / "players.csv", index=False)
    print("players master", len(out), "with espn_id", (out["espn_id"] != "").sum())

if __name__ == "__main__":
    main()
