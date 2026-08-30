from pathlib import Path
from datetime import datetime, timezone
import io
import pandas as pd
from espn import get_text

now = datetime.now(timezone.utc)
YEAR = now.year if now.month >= 3 else now.year - 1

BASE = "https://github.com/nflverse/nflverse-data/releases/download/stats_player"
INJ = "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{year}.csv"
DATA = Path("data")
DATA.mkdir(exist_ok=True)

def pull_stats(year):
    url = f"{BASE}/stats_player_week_{year}.csv"
    raw = get_text(url, sleep=0.2)
    if not raw or raw.strip() in (b"404", b"Not Found") or len(raw) < 50:
        print("no weekly stats yet for", year)
        return None
    df = pd.read_csv(io.BytesIO(raw))
    df.to_csv(DATA / f"gamelogs_{year}.csv", index=False)
    print(year, "gamelog rows", len(df))
    return df

def pull_injuries(year):
    raw = get_text(INJ.format(year=year), sleep=0.2)
    if not raw or len(raw) < 50:
        print("no injuries file for", year)
        return
    Path(DATA / "injuries.csv").write_bytes(raw)
    print("injuries saved", year)

def main():
    frames = []
    for y in (YEAR - 1, YEAR):
        df = pull_stats(y)
        if df is not None:
            frames.append(df)
    if not frames:
        raise SystemExit("No gamelog files downloaded")
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(DATA / "gamelogs.csv", index=False)
    print("combined gamelogs", len(out))
    pull_injuries(YEAR)
    pull_injuries(YEAR - 1)

if __name__ == "__main__":
    main()
