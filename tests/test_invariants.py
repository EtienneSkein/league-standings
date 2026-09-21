"""Properties that must hold for any set of results.

Leagues are generated randomly with fixed seeds, so every run tests the same
cases and any failure can be reproduced.
"""

import random
from datetime import date, timedelta
from pathlib import Path

import pytest

from standings.csv_io import read_results
from standings.table import POINTS_FOR_DRAW, POINTS_FOR_WIN, MatchResult, compute_table

RESULTS_FILE = Path(__file__).resolve().parent.parent / "data" / "results_1974-75_week10.csv"


def random_league(seed):
    rng = random.Random(seed)
    teams = [f"Team {n:02d}" for n in range(rng.randint(2, 24))]
    start = date(1974, 8, 17)
    results = []
    for day in range(rng.randint(0, 40)):
        playing = teams[:]
        rng.shuffle(playing)
        for home, away in zip(playing[0::2], playing[1::2]):
            if rng.random() < 0.8:
                results.append(
                    MatchResult(
                        start + timedelta(days=day),
                        home,
                        away,
                        rng.choice([0, 0, 1, 1, 1, 2, 2, 3, 4, 7]),
                        rng.choice([0, 0, 1, 1, 1, 2, 2, 3, 4, 7]),
                    )
                )
    return results


def real_week10_results():
    with RESULTS_FILE.open(newline="", encoding="utf-8") as stream:
        return read_results(stream)


LEAGUES = [pytest.param(random_league(seed), id=f"seed-{seed}") for seed in range(200)]
LEAGUES.append(pytest.param(real_week10_results(), id="1974-75-week10"))


@pytest.mark.parametrize("results", LEAGUES)
def test_league_totals_balance(results):
    records = [s.record for s in compute_table(results)]
    assert sum(r.won for r in records) == sum(r.lost for r in records)
    assert sum(r.drawn for r in records) % 2 == 0
    assert sum(r.goals_for for r in records) == sum(r.goals_against for r in records)
    assert sum(r.played for r in records) == 2 * len(results)
    assert sum(r.points for r in records) == 2 * len(results)


@pytest.mark.parametrize("results", LEAGUES)
def test_each_team_record_is_consistent(results):
    for standing in compute_table(results):
        r = standing.record
        assert r.played == r.won + r.drawn + r.lost
        assert r.points == POINTS_FOR_WIN * r.won + POINTS_FOR_DRAW * r.drawn


@pytest.mark.parametrize("results", LEAGUES)
def test_every_team_appears_exactly_once(results):
    teams = {t for r in results for t in (r.home_team, r.away_team)}
    listed = [s.record.team for s in compute_table(results)]
    assert sorted(listed) == sorted(teams)


@pytest.mark.parametrize("results", LEAGUES)
def test_table_is_ordered_by_the_rules(results):
    standings = compute_table(results)
    for above, below in zip(standings, standings[1:]):
        a, b = above.record, below.record
        assert a.points >= b.points
        if a.points != b.points:
            continue
        if b.goal_average is None:
            # An undefined average ranks highest, so the team above has none either.
            assert a.goal_average is None
        elif a.goal_average is not None:
            assert a.goal_average >= b.goal_average
        if a.goal_average == b.goal_average:
            assert a.goals_for >= b.goals_for


@pytest.mark.parametrize("results", LEAGUES)
def test_positions_start_at_one_and_skip_after_ties(results):
    standings = compute_table(results)
    for index, standing in enumerate(standings, start=1):
        previous = standings[index - 2] if index > 1 else None
        if previous is not None and standing.position == previous.position:
            continue
        assert standing.position == index


@pytest.mark.parametrize("seed", range(20))
def test_shuffling_results_gives_identical_table(seed):
    results = real_week10_results() if seed == 0 else random_league(seed)
    shuffled = results[:]
    random.Random(seed).shuffle(shuffled)
    assert compute_table(shuffled) == compute_table(results)
