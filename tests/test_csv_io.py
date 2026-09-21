import io
import re
from datetime import date

import pytest

from standings.csv_io import InputError, read_results, write_table
from standings.table import MatchResult, compute_table

HEADER = "date,home_team,away_team,home_goals,away_goals\n"


def read(text):
    return read_results(io.StringIO(text, newline=""))


def table_csv(results):
    out = io.StringIO()
    write_table(compute_table(results), out)
    return out.getvalue()


# --- Valid input ---------------------------------------------------------


def test_reads_valid_rows():
    results = read(HEADER + "1974-08-17,Chelsea,Carlisle United,0,2\n")
    assert results == [MatchResult(date(1974, 8, 17), "Chelsea", "Carlisle United", 0, 2)]


def test_ignores_blank_lines_and_surrounding_whitespace():
    results = read(HEADER + "\n 1974-08-17 , Chelsea , Carlisle United , 0 , 2 \n\n")
    assert results == [MatchResult(date(1974, 8, 17), "Chelsea", "Carlisle United", 0, 2)]


def test_accepts_columns_in_any_order():
    text = "home_team,away_team,home_goals,away_goals,date\nA,B,1,0,1974-08-17\n"
    assert read(text) == [MatchResult(date(1974, 8, 17), "A", "B", 1, 0)]


def test_header_names_are_case_insensitive():
    text = "Date,Home_Team,AWAY_TEAM,Home_Goals,Away_Goals\n1974-08-17,A,B,1,0\n"
    assert read(text)[0].home_team == "A"


def test_accepts_byte_order_mark_from_spreadsheet_programs():
    assert read("﻿" + HEADER + "1974-08-17,A,B,1,0\n")[0].home_team == "A"


def test_accepts_windows_line_endings():
    text = HEADER.replace("\n", "\r\n") + "1974-08-17,A,B,1,0\r\n1974-08-24,B,A,2,2\r\n"
    assert len(read(text)) == 2


def test_accepts_quoted_names_containing_commas():
    results = read(HEADER + '1974-08-17,"Brighton, Hove Albion",B,1,0\n')
    assert results[0].home_team == "Brighton, Hove Albion"


def test_accepts_non_ascii_team_names():
    assert read(HEADER + "1974-08-17,Borussia Mönchengladbach,B,1,0\n")[0].home_team == (
        "Borussia Mönchengladbach"
    )


def test_accepts_large_scores():
    assert read(HEADER + "1974-08-17,A,B,149,0\n")[0].home_goals == 149


def test_same_fixture_on_different_dates_is_allowed():
    # Some leagues play each other more than twice a season.
    assert len(read(HEADER + "1974-08-17,A,B,1,0\n1974-09-17,A,B,2,0\n")) == 2


def test_header_only_gives_no_results():
    assert read(HEADER) == []


def test_ignores_extra_columns():
    text = "date,home_team,away_team,home_goals,away_goals,attendance\n1974-08-17,A,B,1,0,40000\n"
    assert read(text)[0].away_team == "B"


# --- Invalid input -------------------------------------------------------


@pytest.mark.parametrize(
    "text, message",
    [
        ("", "header is missing"),
        ("\n\n", "header is missing"),
        ("date,home,away,hg,ag\n", "header is missing column(s): home_team"),
        (
            "date,date,home_team,away_team,home_goals,away_goals\n",
            "header repeats column(s): date",
        ),
        (HEADER + "1974-08-17,A,B,one,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,1,-1\n", "line 2: away_goals must be a whole number of 0 or more"),
        (HEADER + "1974-08-17,A,B,1.0,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,+1,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,1_0,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,١,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,1 0,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "17/08/1974,A,B,1,0\n", "line 2: date must be YYYY-MM-DD"),
        (HEADER + "1974-02-30,A,B,1,0\n", "line 2: date must be YYYY-MM-DD"),
        (HEADER + "1974-08-17,A,A,1,0\n", "line 2: 'A' cannot play itself"),
        (HEADER + "1974-08-17,A,,1,0\n", "line 2: missing value for away_team"),
        (HEADER + "1974-08-17,A,B,1\n", "line 2: missing value for away_goals"),
        (HEADER + "1974-08-17,A,B,1,0,9\n", "line 2: too many values"),
        (HEADER + "1974-08-17,A,B,1,0\n1974-08-17,C,D,x,0\n", "line 3:"),
    ],
)
def test_rejects_invalid_input(text, message):
    with pytest.raises(InputError, match=re.escape(message)):
        read(text)


def test_rejects_team_names_that_differ_only_in_capitalisation():
    text = HEADER + "1974-08-17,Chelsea,B,1,0\n1974-08-24,C,CHELSEA,1,0\n"
    with pytest.raises(InputError) as error:
        read(text)
    assert str(error.value) == (
        "line 3: team 'CHELSEA' differs only in capitalisation from 'Chelsea' on line 2"
    )


def test_rejects_capitalisation_variant_within_one_row():
    with pytest.raises(InputError, match="line 2: 'a' cannot play itself|capitalisation"):
        read(HEADER + "1974-08-17,A,a,1,0\n")


def test_rejects_duplicate_result():
    text = HEADER + "1974-08-17,A,B,1,0\n1974-08-17,A,B,1,0\n"
    with pytest.raises(InputError) as error:
        read(text)
    assert str(error.value) == "line 3: 'A' already has a match on 1974-08-17 (line 2)"


def test_rejects_team_playing_twice_on_one_day():
    text = HEADER + "1974-08-17,A,B,1,0\n1974-08-17,C,B,1,0\n"
    with pytest.raises(InputError, match=re.escape("line 3: 'B' already has a match on 1974-08-17")):
        read(text)


# --- Output --------------------------------------------------------------


def test_writes_table_with_header_and_three_decimal_goal_average():
    results = [
        MatchResult(date(1974, 8, 17), "A", "B", 2, 1),
        MatchResult(date(1974, 8, 24), "B", "A", 2, 1),
    ]
    assert table_csv(results) == (
        "Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts\n"
        "1,A,2,1,0,1,3,3,1.000,2\n"
        "1,B,2,1,0,1,3,3,1.000,2\n"
    )


def test_undefined_goal_average_is_written_as_empty():
    results = [MatchResult(date(1974, 8, 17), "A", "B", 1, 0)]
    assert table_csv(results).splitlines()[1] == "1,A,1,1,0,0,1,0,,2"


@pytest.mark.parametrize(
    "goals_for, goals_against, shown",
    [(2, 3, "0.667"), (1, 3, "0.333"), (21, 8, "2.625"), (0, 5, "0.000"), (100, 1, "100.000")],
)
def test_goal_average_is_rounded_to_three_decimals(goals_for, goals_against, shown):
    results = [MatchResult(date(1974, 8, 17), "A", "B", goals_for, goals_against)]
    rows = [line.split(",") for line in table_csv(results).splitlines()[1:]]
    row_for_a = next(row for row in rows if row[1] == "A")
    assert row_for_a[8] == shown


def test_team_names_with_commas_are_quoted_in_output():
    results = [MatchResult(date(1974, 8, 17), "Brighton, Hove Albion", "B", 1, 0)]
    assert table_csv(results).splitlines()[1] == '1,"Brighton, Hove Albion",1,1,0,0,1,0,,2'


def test_empty_table_is_just_the_header():
    assert table_csv([]) == "Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts\n"
