"""Reading match results from CSV and writing the league table as CSV."""

from __future__ import annotations

import csv
from datetime import date
from typing import Iterable, TextIO

from standings.table import MatchResult, Standing

INPUT_COLUMNS = ("date", "home_team", "away_team", "home_goals", "away_goals")
OUTPUT_COLUMNS = ("Pos", "Team", "Pld", "W", "D", "L", "GF", "GA", "GAv", "Pts")


class InputError(ValueError):
    """Raised when the results file cannot be parsed."""


def _parse_goals(value: str, column: str, line: int) -> int:
    try:
        goals = int(value)
    except ValueError:
        raise InputError(f"line {line}: {column} must be a whole number, got {value!r}") from None
    if goals < 0:
        raise InputError(f"line {line}: {column} cannot be negative, got {goals}")
    return goals


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


def read_results(stream: TextIO) -> list[MatchResult]:
    reader = csv.DictReader(stream)
    header = [name.strip() for name in reader.fieldnames or []]
    missing = [column for column in INPUT_COLUMNS if column not in header]
    if missing:
        raise InputError(
            f"header is missing column(s): {', '.join(missing)}; "
            f"expected {','.join(INPUT_COLUMNS)}"
        )
    reader.fieldnames = header

    results = []
    for row in reader:
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue  # blank line
        if None in row:
            raise InputError(f"line {reader.line_num}: too many values")
        results.append(_parse_row(row, reader.line_num))
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
