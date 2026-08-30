import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from espn import get_json, get_text

DATA = Path("data")
DATA.mkdir(exist_ok=True)

FEEDS = [
    ("rotowire_rss", "https://www.rotowire.com/rss/news.php?sport=NFL"),
    ("cbs_rss", "https://www.cbssports.com/rss/headlines/nfl/"),
    ("yahoo_rss", "https://sports.yahoo.com/nfl/rss.xml"),
]
ESPN_NEWS = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=50"

def parse_rss(xml_bytes, source):
    rows = []
    if not xml_bytes:
        return rows
    try:
        root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    except Exception as e:
        print("rss parse fail", source, e)
        return rows
    for it in root.findall(".//item"):
        def txt(tag):
            el = it.find(tag)
            return (el.text or "").strip() if el is not None else ""
        desc = txt("description")
        rows.append({
            "article_id": txt("guid") or txt("link"),
            "source": source,
            "headline": txt("title"),
            "description": desc[:2000],
            "published": txt("pubDate"),
            "web_url": txt("link"),
            "athlete_ids": "",
            "team_ids": "",
            "pulled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return rows

def espn_rows(data):
    rows = []
    for a in (data or {}).get("articles") or []:
        cats = a.get("categories") or []
        athlete_ids = [str(c.get("athleteId")) for c in cats if c.get("type") == "athlete" and c.get("athleteId")]
        team_ids = [str(c.get("teamId")) for c in cats if c.get("type") == "team" and c.get("teamId")]
        web = (((a.get("links") or {}).get("web") or {}).get("href")) or ""
        rows.append({
            "article_id": a.get("id"),
            "source": "espn_json",
            "headline": a.get("headline"),
            "description": (a.get("description") or "")[:2000],
            "published": a.get("published") or a.get("lastModified"),
            "web_url": web,
            "athlete_ids": "|".join(athlete_ids),
            "team_ids": "|".join(team_ids),
            "pulled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return rows

def write_csv(path, rows):
    if not rows:
        print("no rows", path)
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(path, len(rows))

def main():
    rows = []
    for name, url in FEEDS:
        raw = get_text(url, sleep=0.3)
        parsed = parse_rss(raw, name)
        print(name, len(parsed))
        rows.extend(parsed)

    espn = get_json(ESPN_NEWS, sleep=0.4)
    if espn:
        extra = espn_rows(espn)
        print("espn_json", len(extra))
        rows.extend(extra)
    else:
        print("espn_json blocked or empty — using RSS only")

    seen = set()
    uniq = []
    for r in rows:
        key = (r.get("source"), r.get("headline"))
        if not r.get("headline") or key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    write_csv(DATA / "news_all.csv", uniq)
    write_csv(DATA / "rss_news.csv", [r for r in uniq if r["source"].endswith("_rss")])
    write_csv(DATA / "news.csv", uniq)

if __name__ == "__main__":
    main()
