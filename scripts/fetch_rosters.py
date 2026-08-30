from pathlib import Path
from datetime import datetime
import io
import pandas as pd
from espn import get_json, get_text

YEAR = datetime.utcnow().year
# NFL season year: Aug-Dec = current year, Jan-Feb = previous
if datetime.utcnow().month < 3:
    YEAR = YEAR - 1

NFLVERSE_PLAYERS = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
NFLVERSE_ROSTER = f"https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{YEAR}.csv"
TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=32"
ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{tid}/roster"

DATA = Path("data")
DATA.mkdir(exist_ok=True)

def read_csv_url(url):
    raw = get_text(url, sleep=0.2)
    if not raw:
        return None
    return pd.read_csv(io.BytesIO(raw), dtype=str)

def espn_teams():
    js = get_json(TEAMS_URL)
    teams = []
    for sport in (js or {}).get("sports", []):
        for league in sport.get("leagues", []):
            for t in league.get("teams", []):
                teams.append(t.get("team") or t)
    return teams

def espn_roster_rows():
    rows = []
    for t in espn_teams():
        roster = get_json(ROSTER_URL.format(tid=t.get("id")), sleep=0.7)
        if not roster:
            continue
        for group in roster.get("athletes") or []:
            for p in group.get("items") or []:
                pos = p.get("position") or {}
                status = p.get("status") or {}
                inj = (p.get("injuries") or [{}])[0] if p.get("injuries") else {}
                rows.append({
                    "espn_id": str(p.get("id") or ""),
                    "full_name": p.get("fullName") or p.get("displayName"),
                    "position": pos.get("abbreviation"),
                    "team_id": str(t.get("id") or ""),
                    "team_abbr": t.get("abbreviation"),
                    "team_name": t.get("displayName"),
                    "status": status.get("name"),
                    "injury_status": inj.get("status"),
                    "jersey": p.get("jersey"),
                    "age": p.get("age"),
                    "headshot": (p.get("headshot") or {}).get("href"),
                })
        print("ESPN roster", t.get("abbreviation"))
    return pd.DataFrame(rows)

def main():
    players = read_csv_url(NFLVERSE_PLAYERS)
    if players is not None:
        players.to_csv(DATA / "nflverse_players.csv", index=False)
        print("nflverse players", len(players))

    roster = read_csv_url(NFLVERSE_ROSTER)
    if roster is None:
        roster = read_csv_url(
            f"https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{YEAR-1}.csv"
        )
    if roster is not None:
        roster.to_csv(DATA / "nflverse_roster.csv", index=False)
        print("nflverse roster", len(roster))

    espn = espn_roster_rows()
    if espn.empty:
        print("No ESPN roster rows")
        return
    espn.to_csv(DATA / "espn_roster.csv", index=False)

    # compact master used by the dashboard
    master = espn.copy()
    if players is not None and "espn_id" in players.columns:
        keep = [c for c in ["espn_id", "gsis_id", "sleeper_id", "pfr_id", "yahoo_id", "display_name"] if c in players.columns]
        merged = master.merge(players[keep].drop_duplicates("espn_id"), on="espn_id", how="left")
    else:
        merged = master
    merged.to_csv(DATA / "players.csv", index=False)
    print("players master", len(merged))

if __name__ == "__main__":
    main()
