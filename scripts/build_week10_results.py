"""Rebuild the 1974/75 results files from the engsoccerdata dataset.

Source: James P. Curley (2016). engsoccerdata: English Soccer Data 1871-2016.
https://github.com/jalapic/engsoccerdata (free for non-commercial use)

Writes two files:
- data/results_1974-75_week10.csv: the submission input. Week 10 of the
  season is the week of Saturday 19 October 1974 (the season opened on
  Saturday 17 August 1974), so it holds every top-flight match up to and
  including Friday 25 October 1974.
- tests/fixtures/results_1974-75_full_season.csv: all 462 matches, used by
  the tests to check the final table against the published one.

Usage: python scripts/build_week10_results.py
"""

import csv
import io
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/england.csv"
SEASON = "1974"
TIER = "1"
WEEK10_LAST_DATE = "1974-10-25"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEEK10_OUTPUT = PROJECT_ROOT / "data" / "results_1974-75_week10.csv"
FULL_SEASON_OUTPUT = PROJECT_ROOT / "tests" / "fixtures" / "results_1974-75_full_season.csv"


def write_results(path: Path, matches: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["date", "home_team", "away_team", "home_goals", "away_goals"])
        for r in matches:
            writer.writerow([r["Date"], r["home"], r["visitor"], r["hgoal"], r["vgoal"]])
    print(f"Wrote {len(matches)} matches to {path}")


def main() -> None:
    with urllib.request.urlopen(SOURCE_URL) as response:
        rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))

    season = sorted(
        (r for r in rows if r["Season"] == SEASON and r["tier"] == TIER),
        key=lambda r: (r["Date"], r["home"]),
    )
    write_results(FULL_SEASON_OUTPUT, season)
    write_results(WEEK10_OUTPUT, [r for r in season if r["Date"] <= WEEK10_LAST_DATE])


if __name__ == "__main__":
    main()
