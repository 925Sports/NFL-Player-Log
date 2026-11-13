#!/usr/bin/env python3
"""Write data/current_injuries.csv from the ESPN injury endpoint.
Active / Probable are dropped so the tool only sees real designations.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path("data/current_injuries.csv")
URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
UA = {"User-Agent": "925Sports-NFL-Player-Log/1.0"}

def main() -> None:
    req = Request(URL, headers=UA)
    with urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    rows = []
    for team in data.get("injuries") or []:
        team_name = team.get("displayName") or ""
        for item in team.get("injuries") or []:
            ath = item.get("athlete") or {}
            name = ath.get("displayName") or ""
            status = str(item.get("status") or "").strip()
            if not name or not status:
                continue
            if status.lower() in {"active", "probable"}:
                continue
            rows.append({
                "player": name,
                "team": team_name,
                "status": status,
                "comment": item.get("shortComment") or item.get("longComment") or "",
                "date": item.get("date") or "",
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["player", "team", "status", "comment", "date"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} injury rows to {OUT}")

if __name__ == "__main__":
    main()
