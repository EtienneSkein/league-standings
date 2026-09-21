"""Rebuild data/results_1974-75_week10.csv from the engsoccerdata dataset.

Source: James P. Curley (2016). engsoccerdata: English Soccer Data 1871-2016.
https://github.com/jalapic/engsoccerdata (free for non-commercial use)

Week 10 of the 1974/75 season is the week of Saturday 19 October 1974
(the season opened on Saturday 17 August 1974), so every top-flight match
played up to and including Friday 25 October 1974 is included.

Usage: python scripts/build_week10_results.py
"""

import csv
import io
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/england.csv"
SEASON = "1974"
TIER = "1"
LAST_DATE = "1974-10-25"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "results_1974-75_week10.csv"


def main() -> None:
    with urllib.request.urlopen(SOURCE_URL) as response:
        rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))

    matches = sorted(
        (r for r in rows if r["Season"] == SEASON and r["tier"] == TIER and r["Date"] <= LAST_DATE),
        key=lambda r: (r["Date"], r["home"]),
    )

    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["date", "home_team", "away_team", "home_goals", "away_goals"])
        for r in matches:
            writer.writerow([r["Date"], r["home"], r["visitor"], r["hgoal"], r["vgoal"]])

    print(f"Wrote {len(matches)} matches to {OUTPUT}")


if __name__ == "__main__":
    main()
