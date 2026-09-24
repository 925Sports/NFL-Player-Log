#!/usr/bin/env python3
"""Estimated routes, kept separate from targets.

routes      = team dropbacks * offensive snap %
route_pct   = offensive snap %
targets     = actual targets from weekly player stats (reference only)
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
STATS_URL = f"https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_{SEASON}.csv"
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


def norm(name: str) -> str:
    s = (name or "").lower().strip()
    for suf in (" jr.", " jr", " sr.", " sr", " iii", " ii", " iv"):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    return s.replace(".", "")


def main() -> None:
    pbp = get_csv(PBP_URL)
    snaps = get_csv(SNAPS_URL)
    try:
        stats = get_csv(STATS_URL)
    except Exception:
        stats = []

    dropbacks = defaultdict(int)
    for row in pbp:
        if str(row.get("season_type") or "REG").upper() != "REG":
            continue
        if num(row.get("qb_dropback")) < 1 and num(row.get("pass_attempt")) < 1:
            continue
        week = int(num(row.get("week")))
        team = str(row.get("posteam") or "").upper()
        if week >= 1 and team:
            dropbacks[(week, team)] += 1

    targets = {}
    for row in stats:
        if str(row.get("season_type") or "REG").upper() not in {"REG", ""}:
            continue
        name = row.get("player_display_name") or row.get("player_name") or ""
        week = int(num(row.get("week")))
        targets[(norm(name), week)] = int(num(row.get("targets")))

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
        db = dropbacks.get((week, team), 0)
        routes = round(db * off_pct, 1)
        tgt = targets.get((norm(name), week), 0)
        out_rows.append({
            "season": int(num(row.get("season"), SEASON)),
            "week": week,
            "player": name,
            "team": team,
            "position": pos,
            "team_dropbacks": db,
            "routes": routes,
            "route_pct": round(off_pct, 4),
            "targets": tgt,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["season", "week", "player", "team", "position", "team_dropbacks", "routes", "route_pct", "targets"]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(out_rows, key=lambda r: (r["week"], r["team"], r["player"])))
    print(f"Wrote {len(out_rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
