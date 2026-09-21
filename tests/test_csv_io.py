import io
from datetime import date

import pytest

from standings.csv_io import InputError, read_results, write_table
from standings.table import MatchResult, compute_table

HEADER = "date,home_team,away_team,home_goals,away_goals\n"


def read(text):
    return read_results(io.StringIO(text))


def test_reads_valid_rows():
    results = read(HEADER + "1974-08-17,Chelsea,Carlisle United,0,2\n")
    assert results == [MatchResult(date(1974, 8, 17), "Chelsea", "Carlisle United", 0, 2)]


def test_ignores_blank_lines_and_surrounding_whitespace():
    results = read(HEADER + "\n 1974-08-17 , Chelsea , Carlisle United , 0 , 2 \n\n")
    assert results[0].home_team == "Chelsea"
    assert results[0].away_goals == 2


def test_accepts_columns_in_any_order():
    text = "home_team,away_team,home_goals,away_goals,date\nA,B,1,0,1974-08-17\n"
    assert read(text)[0].home_team == "A"


def test_header_only_gives_no_results():
    assert read(HEADER) == []


@pytest.mark.parametrize(
    "text, message",
    [
        ("", "header is missing"),
        ("date,home,away,hg,ag\n", "header is missing column(s): home_team"),
        (HEADER + "1974-08-17,A,B,one,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,1,-1\n", "line 2: away_goals cannot be negative"),
        (HEADER + "17/08/1974,A,B,1,0\n", "line 2: date must be YYYY-MM-DD"),
        (HEADER + "1974-08-17,A,A,1,0\n", "line 2: 'A' cannot play itself"),
        (HEADER + "1974-08-17,A,,1,0\n", "line 2: missing value for away_team"),
        (HEADER + "1974-08-17,A,B,1\n", "line 2: missing value for away_goals"),
        (HEADER + "1974-08-17,A,B,1,0,9\n", "line 2: too many values"),
        (HEADER + "1974-08-17,A,B,1,0\n1974-08-17,C,D,x,0\n", "line 3:"),
    ],
)
def test_rejects_invalid_input(text, message):
    with pytest.raises(InputError, match=message.replace("(", r"\(").replace(")", r"\)")):
        read(text)


def test_writes_table_with_header_and_three_decimal_goal_average():
    standings = compute_table(
        [
            MatchResult(date(1974, 8, 17), "A", "B", 2, 1),
            MatchResult(date(1974, 8, 24), "B", "A", 2, 1),
        ]
    )
    out = io.StringIO()
    write_table(standings, out)
    assert out.getvalue() == (
        "Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts\n"
        "1,A,2,1,0,1,3,3,1.000,2\n"
        "1,B,2,1,0,1,3,3,1.000,2\n"
    )


def test_undefined_goal_average_is_written_as_empty():
    standings = compute_table([MatchResult(date(1974, 8, 17), "A", "B", 1, 0)])
    out = io.StringIO()
    write_table(standings, out)
    assert out.getvalue().splitlines()[1] == "1,A,1,1,0,0,1,0,,2"
