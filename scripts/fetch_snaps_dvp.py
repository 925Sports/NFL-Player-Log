from pathlib import Path
from datetime import datetime, timezone
import io
import pandas as pd
from espn import get_text

now = datetime.now(timezone.utc)
YEAR = now.year if now.month >= 3 else now.year - 1
DATA = Path("data")
DATA.mkdir(exist_ok=True)

SNAPS = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{year}.csv"

# Keep in sync with the builder TEAM_NICKNAMES / normalizeTeam
NICK = {
    "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills",
    "CAR": "Panthers", "CHI": "Bears", "CIN": "Bengals", "CLE": "Browns",
    "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers", "GNB": "Packers",
    "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "JAC": "Jaguars",
    "KC": "Chiefs", "KAN": "Chiefs", "LA": "Rams", "LAR": "Rams",
    "LAC": "Chargers", "LV": "Raiders", "LVR": "Raiders", "MIA": "Dolphins",
    "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NOR": "Saints",
    "NYG": "Giants", "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers",
    "SEA": "Seahawks", "SF": "49ers", "SFO": "49ers", "TB": "Buccaneers",
    "TAM": "Buccaneers", "TEN": "Titans", "WAS": "Commanders", "WSH": "Commanders",
}

def pull_csv(url):
    raw = get_text(url, sleep=0.2)
    if not raw or len(raw) < 50:
        print("missing", url)
        return None
    return pd.read_csv(io.BytesIO(raw))

def nick(code):
    s = str(code or "").strip().upper()
    return NICK.get(s, s.title() if s else "")

def main():
    # --- snaps ---
    frames = []
    for y in (YEAR - 1, YEAR):
        df = pull_csv(SNAPS.format(year=y))
        if df is None:
            continue
        frames.append(df)
        df.to_csv(DATA / f"snap_counts_{y}.csv", index=False)
        print("snaps", y, len(df))
    if frames:
        snaps = pd.concat(frames, ignore_index=True)
        keep = [c for c in [
            "season", "week", "player", "pfr_player_id", "position", "team", "opponent",
            "offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps", "st_pct"
        ] if c in snaps.columns]
        snaps[keep].to_csv(DATA / "snap_counts.csv", index=False)
        print("combined snaps", len(snaps))
    else:
        print("no snap files yet")

    # --- DVP from existing gamelogs ---
    logs_path = DATA / "gamelogs.csv"
    if not logs_path.exists():
        raise SystemExit("data/gamelogs.csv missing — run fetch_gamelogs.py first")
    logs = pd.read_csv(logs_path)
    pos = logs["position"].astype(str).str.upper()
    logs = logs[pos.isin(["QB", "RB", "WR", "TE", "K"])].copy()
    if "season_type" in logs.columns:
        logs = logs[logs["season_type"].fillna("REG").astype(str).str.upper().eq("REG")]

    def num(col, default=0):
        return pd.to_numeric(logs[col], errors="coerce").fillna(default) if col in logs.columns else default

    # Same DK-ish points the builder uses: PPR for skill, standard for QB/K
    std = num("fantasy_points")
    ppr = num("fantasy_points_ppr")
    is_skill = logs["position"].astype(str).str.upper().isin(["RB", "WR", "TE"])
    logs["dk_fp"] = ppr.where(is_skill, std)

    logs["opp"] = logs["opponent_team"].astype(str).str.upper().str.strip()
    logs["pos"] = logs["position"].astype(str).str.upper().str.strip()
    logs["pass_yds"] = num("passing_yards")
    logs["rush_yds"] = num("rushing_yards")
    logs["rec"] = num("receptions")
    logs["tgt"] = num("targets")
    logs["rec_yds"] = num("receiving_yards")
    logs["td"] = num("passing_tds") + num("rushing_tds") + num("receiving_tds")

    # Current season only once there are 2+ games; else last two seasons
    seasons = sorted(pd.to_numeric(logs["season"], errors="coerce").dropna().unique())
    cur = int(seasons[-1]) if len(seasons) else YEAR
    use = logs[pd.to_numeric(logs["season"], errors="coerce") == cur]
    if use["week"].nunique() < 2:
        use = logs[pd.to_numeric(logs["season"], errors="coerce").isin([cur, cur - 1])]

    g = use.groupby(["opp", "pos"], dropna=False).agg(
        games=("dk_fp", "size"),
        fp_avg=("dk_fp", "mean"),
        pass_yds_avg=("pass_yds", "mean"),
        rush_yds_avg=("rush_yds", "mean"),
        rec_avg=("rec", "mean"),
        rec_yds_avg=("rec_yds", "mean"),
        tgt_avg=("tgt", "mean"),
        td_avg=("td", "mean"),
        season=("season", "max"),
    ).reset_index()
    g["opp_nick"] = g["opp"].map(nick)
    g["rank"] = g.groupby("pos")["fp_avg"].rank(ascending=False, method="min").astype(int)
    g = g.sort_values(["pos", "rank"])
    g.to_csv(DATA / "dvp.csv", index=False)
    print("dvp rows", len(g))

if __name__ == "__main__":
    main()
