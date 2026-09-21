"""Reading match results from CSV and writing the league table as CSV."""

from __future__ import annotations

import csv
import re
from datetime import date
from typing import Iterable, TextIO

from standings.table import MatchResult, Standing

INPUT_COLUMNS = ("date", "home_team", "away_team", "home_goals", "away_goals")
OUTPUT_COLUMNS = ("Pos", "Team", "Pld", "W", "D", "L", "GF", "GA", "GAv", "Pts")

# Plain ASCII digits only: int() alone would also accept "+1", "1_0" and
# non-Latin digits, turning typos into wrong scores.
_GOALS_PATTERN = re.compile(r"[0-9]+")
# Spreadsheet programs often start UTF-8 files with a byte order mark.
_BYTE_ORDER_MARK = "\ufeff"


class InputError(ValueError):
    """Raised when the results file cannot be parsed."""


def _parse_goals(value: str, column: str, line: int) -> int:
    if not _GOALS_PATTERN.fullmatch(value):
        raise InputError(f"line {line}: {column} must be a whole number of 0 or more, got {value!r}")
    return int(value)


def _parse_row(row: dict[str, str], line: int) -> MatchResult:
    values = {column: (row.get(column) or "").strip() for column in INPUT_COLUMNS}

    for column in INPUT_COLUMNS:
        if not values[column]:
            raise InputError(f"line {line}: missing value for {column}")

    try:
        match_date = date.fromisoformat(values["date"])
    except ValueError:
        raise InputError(f"line {line}: date must be YYYY-MM-DD, got {values['date']!r}") from None

    home_team, away_team = values["home_team"], values["away_team"]
    if home_team == away_team:
        raise InputError(f"line {line}: {home_team!r} cannot play itself")

    return MatchResult(
        date=match_date,
        home_team=home_team,
        away_team=away_team,
        home_goals=_parse_goals(values["home_goals"], "home_goals", line),
        away_goals=_parse_goals(values["away_goals"], "away_goals", line),
    )


def _normalise_header(fieldnames: list[str] | None) -> list[str]:
    header = [name.replace(_BYTE_ORDER_MARK, "").strip().lower() for name in fieldnames or []]
    duplicates = sorted({name for name in header if name and header.count(name) > 1})
    if duplicates:
        raise InputError(f"header repeats column(s): {', '.join(duplicates)}")
    missing = [column for column in INPUT_COLUMNS if column not in header]
    if missing:
        raise InputError(
            f"header is missing column(s): {', '.join(missing)}; "
            f"expected {','.join(INPUT_COLUMNS)}"
        )
    return header


class _ConsistencyCheck:
    """Rejects results that are individually valid but contradict each other."""

    def __init__(self) -> None:
        self._spellings: dict[str, tuple[str, int]] = {}
        self._fixtures: dict[tuple[date, str], int] = {}

    def check(self, result: MatchResult, line: int) -> None:
        for team in (result.home_team, result.away_team):
            key = team.casefold()
            spelling, first_line = self._spellings.setdefault(key, (team, line))
            if spelling != team:
                raise InputError(
                    f"line {line}: team {team!r} differs only in capitalisation "
                    f"from {spelling!r} on line {first_line}"
                )
            fixture = (result.date, key)
            if fixture in self._fixtures:
                raise InputError(
                    f"line {line}: {team!r} already has a match on "
                    f"{result.date.isoformat()} (line {self._fixtures[fixture]})"
                )
            self._fixtures[fixture] = line


def read_results(stream: TextIO) -> list[MatchResult]:
    reader = csv.DictReader(stream)
    reader.fieldnames = _normalise_header(reader.fieldnames)

    consistency = _ConsistencyCheck()
    results = []
    for row in reader:
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue  # blank line
        if None in row:
            raise InputError(f"line {reader.line_num}: too many values")
        result = _parse_row(row, reader.line_num)
        consistency.check(result, reader.line_num)
        results.append(result)
    return results


def format_goal_average(standing: Standing) -> str:
    average = standing.record.goal_average
    return "" if average is None else f"{float(average):.3f}"


def write_table(standings: Iterable[Standing], stream: TextIO) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(OUTPUT_COLUMNS)
    for standing in standings:
        record = standing.record
        writer.writerow(
            [
                standing.position,
                record.team,
                record.played,
                record.won,
                record.drawn,
                record.lost,
                record.goals_for,
                record.goals_against,
                format_goal_average(standing),
                record.points,
            ]
        )
