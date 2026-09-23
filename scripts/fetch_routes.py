#!/usr/bin/env python3
"""Build data/routes.csv for the 925 DFS tool.

Estimated routes = team dropbacks * offensive snap %.
route_pct is that snap % (0–1). Swap this file later if you get true charted routes.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen

SEASON = 2026
PBP_URL = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{SEASON}.csv"
SNAPS_URL = f"https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{SEASON}.csv"
OUT = Path("data/routes.csv")

UA = {"User-Agent": "925Sports-NFL-Player-Log/1.0"}


def get_csv(url: str) -> list[dict]:
    req = Request(url, headers=UA)
    with urlopen(req, timeout=180) as r:
        text = r.read().decode("utf-8", "replace")
    return list(csv.DictReader(StringIO(text)))


def num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def main() -> None:
    print("Downloading PBP…")
    pbp = get_csv(PBP_URL)
    print("Downloading snaps…")
    snaps = get_csv(SNAPS_URL)

    dropbacks = defaultdict(int)  # (week, team) -> dropbacks
    for row in pbp:
        if str(row.get("season_type") or "REG").upper() != "REG":
            continue
        if num(row.get("pass_attempt")) < 1 and str(row.get("play_type") or "") != "pass":
            # sack / scramble still a dropback when qb_dropback is 1
            if num(row.get("qb_dropback")) < 1:
                continue
        week = int(num(row.get("week")))
        team = str(row.get("posteam") or "").upper()
        if week < 1 or not team:
            continue
        dropbacks[(week, team)] += 1

    out_rows = []
    for row in snaps:
        if str(row.get("game_type") or "REG").upper() not in {"REG", ""}:
            continue
        pos = str(row.get("position") or "").upper()
        if pos not in {"QB", "RB", "HB", "FB", "WR", "TE"}:
            continue
        week = int(num(row.get("week")))
        team = str(row.get("team") or "").upper()
        name = row.get("player") or row.get("player_name") or ""
        if not name or week < 1 or not team:
            continue
        off_pct = num(row.get("offense_pct"))
        if off_pct > 1.5:
            off_pct = off_pct / 100.0
        routes = round(dropbacks.get((week, team), 0) * off_pct, 1)
        out_rows.append(
            {
                "season": int(num(row.get("season"), SEASON)),
                "week": week,
                "player": name,
                "team": team,
                "position": pos,
                "routes": routes,
                "route_pct": round(off_pct, 4),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["season", "week", "player", "team", "position", "routes", "route_pct"],
        )
        w.writeheader()
        w.writerows(sorted(out_rows, key=lambda r: (r["week"], r["team"], r["player"])))
    print(f"Wrote {len(out_rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
