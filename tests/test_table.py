from datetime import date
from fractions import Fraction

from standings.table import MatchResult, TeamRecord, compute_table

MATCH_DATE = date(1974, 8, 17)


def match(home, away, home_goals, away_goals):
    return MatchResult(MATCH_DATE, home, away, home_goals, away_goals)


def by_team(standings):
    return {s.record.team: s for s in standings}


def order(standings):
    return [s.record.team for s in standings]


def test_win_is_two_points_draw_is_one():
    table = by_team(compute_table([match("A", "B", 2, 1), match("C", "D", 0, 0)]))
    assert table["A"].record.points == 2
    assert table["B"].record.points == 0
    assert table["C"].record.points == 1
    assert table["D"].record.points == 1


def test_record_counts_home_and_away():
    table = by_team(compute_table([match("A", "B", 3, 1), match("B", "A", 2, 2)]))
    a = table["A"].record
    assert (a.played, a.won, a.drawn, a.lost, a.goals_for, a.goals_against) == (2, 1, 1, 0, 5, 3)
    b = table["B"].record
    assert (b.played, b.won, b.drawn, b.lost, b.goals_for, b.goals_against) == (2, 0, 1, 1, 3, 5)


def test_goal_average_is_exact_fraction():
    record = TeamRecord("A", goals_for=19, goals_against=15)
    assert record.goal_average == Fraction(19, 15)


def test_goal_average_is_undefined_with_no_goals_conceded():
    assert TeamRecord("A", goals_for=3, goals_against=0).goal_average is None


def test_points_rank_first():
    standings = compute_table([match("A", "B", 1, 0), match("C", "D", 5, 5)])
    assert order(standings)[0] == "A"


def test_level_on_points_uses_goal_average_not_goal_difference():
    # X: 6 for, 3 against -> average 2.000, difference +3
    # Y: 10 for, 6 against -> average 1.667, difference +4
    results = [
        match("X", "P", 6, 0),
        match("X", "Q", 0, 3),
        match("Y", "R", 10, 0),
        match("Y", "S", 0, 6),
    ]
    teams = order(compute_table(results))
    assert teams.index("X") < teams.index("Y")


def test_equal_goal_average_uses_goals_scored():
    results = [
        match("X", "P", 2, 1),
        match("X", "Q", 0, 1),  # X: 2 for, 2 against
        match("Y", "R", 4, 2),
        match("Y", "S", 0, 2),  # Y: 4 for, 4 against
    ]
    table = by_team(compute_table(results))
    assert table["Y"].position < table["X"].position


def test_completely_level_teams_share_position_and_sort_alphabetically():
    results = [match("Bravo", "Delta", 1, 0), match("Alpha", "Charlie", 1, 0)]
    standings = compute_table(results)
    assert order(standings) == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert [s.position for s in standings] == [1, 1, 3, 3]


def test_no_goals_conceded_ranks_above_finite_goal_average():
    results = [
        match("Clean", "P", 1, 0),
        match("Leaky", "Q", 5, 1),
    ]
    standings = compute_table(results)
    assert order(standings)[:2] == ["Clean", "Leaky"]


def test_empty_results_give_empty_table():
    assert compute_table([]) == []
