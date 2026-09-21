"""League table calculation using 1974/75 English First Division rules.

- 2 points for a win, 1 for a draw, 0 for a loss.
- Teams level on points are separated by goal average (goals for / goals
  against), then by goals scored.
- A team that has conceded no goals has no goal average; it ranks above any
  team with a finite goal average on the same points.
- Teams still level after all criteria share a position and are listed
  alphabetically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Iterable

POINTS_FOR_WIN = 2
POINTS_FOR_DRAW = 1


@dataclass(frozen=True)
class MatchResult:
    date: date
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


@dataclass
class TeamRecord:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.won * POINTS_FOR_WIN + self.drawn * POINTS_FOR_DRAW

    @property
    def goal_average(self) -> Fraction | None:
        """Goals for divided by goals against, or None if nothing conceded."""
        if self.goals_against == 0:
            return None
        return Fraction(self.goals_for, self.goals_against)

    def record(self, scored: int, conceded: int) -> None:
        self.played += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.won += 1
        elif scored == conceded:
            self.drawn += 1
        else:
            self.lost += 1


@dataclass(frozen=True)
class Standing:
    position: int
    record: TeamRecord


def _ranking_key(record: TeamRecord) -> tuple:
    """Key on which equal values mean the teams share a position."""
    average = record.goal_average
    # (0, ...) sorts before (1, ...): an undefined average ranks highest.
    average_key = (0, Fraction(0)) if average is None else (1, -average)
    return (-record.points, average_key, -record.goals_for)


def compute_table(results: Iterable[MatchResult]) -> list[Standing]:
    records: dict[str, TeamRecord] = {}
    for result in results:
        home = records.setdefault(result.home_team, TeamRecord(result.home_team))
        away = records.setdefault(result.away_team, TeamRecord(result.away_team))
        home.record(result.home_goals, result.away_goals)
        away.record(result.away_goals, result.home_goals)

    ordered = sorted(
        records.values(),
        key=lambda r: (_ranking_key(r), r.team.casefold()),
    )

    standings: list[Standing] = []
    for index, record in enumerate(ordered, start=1):
        if standings and _ranking_key(standings[-1].record) == _ranking_key(record):
            position = standings[-1].position
        else:
            position = index
        standings.append(Standing(position, record))
    return standings
