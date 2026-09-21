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


def test_points_beat_any_goal_average():
    # "Clean" has an undefined (best possible) goal average but fewer points.
    results = [
        match("Clean", "P", 0, 0),
        match("Winner", "Q", 1, 0),
        match("Winner", "R", 0, 5),
    ]
    teams = order(compute_table(results))
    assert teams.index("Winner") < teams.index("Clean")


def test_averages_that_look_equal_to_three_decimals_are_still_separated():
    # 1000/999 = 1.001001... beats 1001/1000 = 1.001 exactly.
    results = [match("X", "P", 1001, 1000), match("Y", "Q", 1000, 999)]
    table = by_team(compute_table(results))
    assert table["Y"].position == 1
    assert table["X"].position == 2


def test_equal_fractions_written_differently_are_level_on_goal_average():
    # X: 4 for 2 against, Y: 2 for 1 against. Both average exactly 2.
    # Goals scored then decides: X ranks above Y.
    results = [
        match("X", "P", 3, 0),
        match("X", "Q", 1, 2),
        match("Y", "R", 2, 0),
        match("Y", "S", 0, 1),
    ]
    table = by_team(compute_table(results))
    assert table["X"].record.goal_average == table["Y"].record.goal_average == 2
    assert table["X"].position < table["Y"].position


def test_teams_without_goals_conceded_are_ordered_by_goals_scored():
    results = [match("Two", "P", 2, 0), match("Five", "Q", 5, 0)]
    assert order(compute_table(results))[:2] == ["Five", "Two"]


def test_goalless_team_ranks_above_team_with_finite_average_on_same_points():
    # Nil: one 0-0 draw, no goal average. Scorer: one 3-3 draw, average 1.
    results = [match("Nil", "P", 0, 0), match("Scorer", "Q", 3, 3)]
    table = by_team(compute_table(results))
    assert table["Nil"].record.goal_average is None
    assert table["Scorer"].record.goal_average == 1
    assert table["Nil"].position < table["Scorer"].position


def test_goalless_team_ranks_below_team_that_scored_without_conceding():
    # Both on 2 points with nothing conceded; goals scored separates them.
    results = [match("Nil", "P", 0, 0), match("Nil", "Q", 0, 0), match("Scorer", "R", 1, 0)]
    table = by_team(compute_table(results))
    assert table["Nil"].record.points == table["Scorer"].record.points == 2
    assert table["Scorer"].position < table["Nil"].position


def test_three_way_tie_shares_position_and_next_position_is_skipped():
    results = [
        match("C", "X", 1, 0),
        match("A", "Y", 1, 0),
        match("B", "Z", 1, 0),
    ]
    standings = compute_table(results)
    assert order(standings)[:3] == ["A", "B", "C"]
    assert [s.position for s in standings] == [1, 1, 1, 4, 4, 4]


def test_alphabetical_order_ignores_capitalisation():
    results = [match("bravo", "X", 1, 0), match("Alpha", "Y", 1, 0), match("Charlie", "Z", 1, 0)]
    assert order(compute_table(results))[:3] == ["Alpha", "bravo", "Charlie"]


def test_result_order_does_not_matter():
    results = [match("A", "B", 3, 1), match("C", "A", 0, 0), match("B", "C", 2, 2)]
    assert compute_table(results) == compute_table(list(reversed(results)))
