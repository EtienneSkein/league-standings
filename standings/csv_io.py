"""Reading match results from CSV and writing the league table as CSV."""

from __future__ import annotations

import csv
import re
import unicodedata
from datetime import date
from typing import Iterable, TextIO

from standings.table import MatchResult, Standing

INPUT_COLUMNS = ("date", "home_team", "away_team", "home_goals", "away_goals")
OUTPUT_COLUMNS = ("Pos", "Team", "Pld", "W", "D", "L", "GF", "GA", "GAv", "Pts")

# Plain ASCII digits only: int() alone would also accept "+1", "1_0" and
# non-Latin digits, turning typos into wrong scores.
_GOALS_PATTERN = re.compile(r"[0-9]+")
# An explicit sanity limit (the record score is 149-0). It also avoids
# int() limits that differ between Python versions.
MAX_GOALS = 999
# date.fromisoformat() accepts more formats from Python 3.11 (e.g. "19740817",
# "1974-W33-6"), so check the shape first to behave the same on every version.
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# Team names are copied into the output table. A cell starting with one of
# these is run as a formula when opened in Excel and similar programs
# ("CSV injection"), so such names are rejected. Leading tabs and carriage
# returns, the other risky prefixes, are already rejected as control characters.
FORMULA_PREFIXES = ("=", "+", "-", "@")
# Spreadsheet programs often start UTF-8 files with a byte order mark.
_BYTE_ORDER_MARK = "\ufeff"


class InputError(ValueError):
    """Raised when the results file cannot be parsed."""


def _parse_goals(value: str, column: str, line: int) -> int:
    if not _GOALS_PATTERN.fullmatch(value):
        raise InputError(f"line {line}: {column} must be a whole number of 0 or more, got {value!r}")
    if len(value.lstrip("0")) > len(str(MAX_GOALS)) or int(value) > MAX_GOALS:
        raise InputError(f"line {line}: {column} is too large (the maximum is {MAX_GOALS})")
    return int(value)


def _parse_date(value: str, line: int) -> date:
    try:
        if _DATE_PATTERN.fullmatch(value):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise InputError(f"line {line}: date must be a valid YYYY-MM-DD date, got {value!r}")


def _parse_team(value: str, column: str, line: int) -> str:
    # NFC makes an accent typed as one character and as letter + combining
    # accent (common in text from macOS) the same string.
    name = unicodedata.normalize("NFC", value)
    if any(unicodedata.category(char).startswith("C") for char in name):
        raise InputError(f"line {line}: {column} contains a control or invisible character: {name!r}")
    if name.startswith(FORMULA_PREFIXES):
        raise InputError(
            f"line {line}: {column} cannot start with {name[0]!r}, because spreadsheet "
            f"programs would run it as a formula: {name!r}"
        )
    return name


def _team_key(name: str) -> str:
    """Names that are equal under this key are treated as the same team."""
    return " ".join(name.split()).casefold()


def _parse_row(row: dict[str, str], line: int) -> MatchResult:
    values = {column: (row.get(column) or "").strip() for column in INPUT_COLUMNS}

    for column in INPUT_COLUMNS:
        if not values[column]:
            raise InputError(f"line {line}: missing value for {column}")

    home_team = _parse_team(values["home_team"], "home_team", line)
    away_team = _parse_team(values["away_team"], "away_team", line)
    if _team_key(home_team) == _team_key(away_team):
        raise InputError(f"line {line}: {home_team!r} cannot play itself")

    return MatchResult(
        date=_parse_date(values["date"], line),
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
            f"expected {','.join(INPUT_COLUMNS)}{_separator_hint(header)}"
        )
    return header


def _separator_hint(header: list[str]) -> str:
    # Excel in many European locales saves "CSV" separated by semicolons.
    if len(header) == 1:
        for separator, name in ((";", "semicolons"), ("\t", "tabs")):
            if separator in header[0]:
                return f" (this file seems to be separated by {name}; it must use commas)"
    return ""


class _ConsistencyCheck:
    """Rejects results that are individually valid but contradict each other."""

    def __init__(self) -> None:
        self._spellings: dict[str, tuple[str, int]] = {}
        self._fixtures: dict[tuple[date, str], int] = {}

    def check(self, result: MatchResult, line: int) -> None:
        for team in (result.home_team, result.away_team):
            key = _team_key(team)
            spelling, first_line = self._spellings.setdefault(key, (team, line))
            if spelling != team:
                raise InputError(
                    f"line {line}: team {team!r} differs only in capitalisation or spacing "
                    f"from {spelling!r} on line {first_line}"
                )
            fixture = (result.date, key)
            if fixture in self._fixtures:
                raise InputError(
                    f"line {line}: {team!r} already has a match on "
                    f"{result.date.isoformat()} (line {self._fixtures[fixture]})"
                )
            self._fixtures[fixture] = line


def _read_rows(reader: csv.DictReader) -> list[MatchResult]:
    reader.fieldnames = _normalise_header(reader.fieldnames)

    consistency = _ConsistencyCheck()
    results = []
    for row in reader:
        # Values beyond the header; spreadsheets often add empty trailing ones.
        extra = [value for value in row.pop(None, []) if value.strip()]
        if not extra and not any((value or "").strip() for value in row.values()):
            continue  # blank line, or only separators
        if extra:
            raise InputError(f"line {reader.line_num}: too many values")
        result = _parse_row(row, reader.line_num)
        consistency.check(result, reader.line_num)
        results.append(result)
    return results


def read_results(stream: TextIO) -> list[MatchResult]:
    # strict: report broken quoting (e.g. a missing closing quote) as an error.
    reader = csv.DictReader(stream, strict=True)
    try:
        return _read_rows(reader)
    except csv.Error as error:
        # DictReader.line_num only updates after a row succeeds; the underlying
        # reader knows the line that failed.
        line = reader.reader.line_num
        hint = "; is a closing quote missing?" if "unexpected end of data" in str(error) else ""
        raise InputError(f"line {line}: not valid CSV ({error}){hint}") from None
    except UnicodeDecodeError:
        raise InputError(
            'file is not UTF-8 text; save it as UTF-8 (in Excel: "CSV UTF-8")'
        ) from None


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
