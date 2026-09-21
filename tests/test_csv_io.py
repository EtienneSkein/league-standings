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
    assert read("\ufeff" + HEADER + "1974-08-17,A,B,1,0\n")[0].home_team == "A"


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
        (HEADER + "1974-08-17,A,B,\u0661,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "1974-08-17,A,B,1 0,0\n", "line 2: home_goals must be a whole number"),
        (HEADER + "17/08/1974,A,B,1,0\n", "line 2: date must be a valid YYYY-MM-DD date"),
        (HEADER + "1974-02-30,A,B,1,0\n", "line 2: date must be a valid YYYY-MM-DD date"),
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
        "line 3: team 'CHELSEA' differs only in capitalisation or spacing from 'Chelsea' on line 2"
    )


def test_rejects_capitalisation_variant_within_one_row():
    with pytest.raises(InputError, match=re.escape("line 2: 'A' cannot play itself")):
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


# --- Malformed files -------------------------------------------------------


def read_bytes(data):
    """Read raw bytes the way the CLI opens files."""
    return read_results(io.TextIOWrapper(io.BytesIO(data), encoding="utf-8", newline=""))


def test_rejects_file_that_is_not_utf8():
    latin1 = (HEADER + "1974-08-17,Mönchengladbach,B,1,0\n").encode("latin-1")
    with pytest.raises(InputError, match="file is not UTF-8 text"):
        read_bytes(latin1)


def test_rejects_non_utf8_bytes_far_into_a_large_file():
    rows = "".join(f"1974-08-17,Team {n},Opponent {n},1,0\n" for n in range(5000))
    data = (HEADER + rows).encode("utf-8") + "1974-08-24,Mönchengladbach,B,1,0\n".encode("latin-1")
    with pytest.raises(InputError, match="file is not UTF-8 text"):
        read_bytes(data)


OK_ROW = "1974-08-17,A,B,1,0\n"


def test_rejects_unclosed_quote_with_hint():
    # The csv module only notices at the end of the file (line 4 here).
    with pytest.raises(InputError) as error:
        read(HEADER + OK_ROW + '1974-08-18,"C,D,1,0\n' + OK_ROW)
    assert str(error.value) == (
        "line 4: not valid CSV (unexpected end of data); is a closing quote missing?"
    )


def test_csv_error_names_the_line_it_happened_on():
    with pytest.raises(InputError, match=re.escape("line 3: not valid CSV")):
        read(HEADER + OK_ROW + '1974-08-18,"C"x,D,1,0\n' + OK_ROW)


def test_csv_error_line_counts_blank_lines():
    with pytest.raises(InputError, match=re.escape("line 4: not valid CSV")):
        read(HEADER + OK_ROW + "\n" + "1974-08-18," + "C" * 200_000 + ",D,1,0\n")


def test_nul_byte_error_names_its_line():
    # Python 3.9/3.10: csv error. Python 3.11+: invisible-character error.
    with pytest.raises(InputError, match="^line 3: "):
        read(HEADER + OK_ROW + "1974-08-18,C\x00,D,1,0\n" + OK_ROW)


def test_rejects_nul_byte_on_every_python_version():
    # Python 3.9/3.10 reject NUL in the csv module; 3.11+ let it through to the
    # team-name check. Either way it must be a clean InputError.
    with pytest.raises(InputError):
        read(HEADER + "1974-08-17,A\x00,B,1,0\n")


def test_rejects_value_longer_than_csv_field_limit():
    with pytest.raises(InputError, match="not valid CSV"):
        read(HEADER + "1974-08-17," + "A" * 200_000 + ",B,1,0\n")


def test_rejects_absurdly_large_score_cleanly():
    with pytest.raises(InputError, match=re.escape("line 2: home_goals is too large")):
        read(HEADER + "1974-08-17,A,B," + "9" * 5000 + ",0\n")


@pytest.mark.parametrize("separator, name", [(";", "semicolons"), ("\t", "tabs")])
def test_wrong_separator_gets_a_hint(separator, name):
    header = separator.join(["date", "home_team", "away_team", "home_goals", "away_goals"])
    with pytest.raises(InputError, match=re.escape(f"seems to be separated by {name}; it must use commas")):
        read(header + "\n1974-08-17" + separator + "A" + separator + "B" + separator + "1" + separator + "0\n")


def test_accepts_empty_trailing_columns_added_by_spreadsheets():
    text = HEADER.rstrip("\n") + ",,\n1974-08-17,A,B,1,0,,\n,,,,,,\n1974-08-24,B,A,0,0,\n"
    assert len(read(text)) == 2


def test_rejects_non_empty_value_beyond_the_header_even_on_an_otherwise_empty_row():
    with pytest.raises(InputError, match=re.escape("line 2: too many values")):
        read(HEADER + ",,,,,x\n")


def test_leading_zeros_in_goals_are_accepted():
    assert read(HEADER + "1974-08-17,A,B,007,00\n")[0].home_goals == 7


# --- Dates: same behaviour on every Python version ---------------------------


@pytest.mark.parametrize(
    "value",
    ["19740817", "1974-W33-6", "1974-8-17", "1974-08-17T15:00", "74-08-17", "1974-229", " "],
)
def test_rejects_date_formats_that_newer_pythons_would_accept(value):
    with pytest.raises(InputError):
        read(HEADER + f"{value},A,B,1,0\n")


@pytest.mark.parametrize("value", ["1974-00-10", "1974-13-01", "1975-02-29", "1974-04-31"])
def test_rejects_impossible_dates(value):
    with pytest.raises(InputError, match="date must be a valid YYYY-MM-DD date"):
        read(HEADER + f"{value},A,B,1,0\n")


def test_accepts_leap_day():
    assert read(HEADER + "1976-02-29,A,B,1,0\n")[0].date == date(1976, 2, 29)


# --- Team names that look the same ------------------------------------------


@pytest.mark.parametrize(
    "variant",
    ["Leeds  United", "Leeds\u00a0United", "LEEDS UNITED"],
    ids=["double-space", "non-breaking-space", "upper-case"],
)
def test_rejects_names_differing_only_in_spacing_or_case(variant):
    text = HEADER + f"1974-08-17,Leeds United,B,1,0\n1974-08-24,{variant},C,1,0\n"
    with pytest.raises(InputError, match="differs only in capitalisation or spacing"):
        read(text)


def test_composed_and_decomposed_accents_are_the_same_team():
    composed, decomposed = "Álava", "A\u0301lava"
    results = read(HEADER + f"1974-08-17,{composed},B,1,0\n1974-08-24,{decomposed},C,1,0\n")
    assert results[0].home_team == results[1].home_team == composed
    assert len(compute_table(results)) == 3


def test_decomposed_accent_is_written_in_composed_form():
    results = read(HEADER + "1974-08-17,A\u0301lava,B,1,0\n")
    assert "Álava" in table_csv(results)


@pytest.mark.parametrize(
    "name",
    ['"Two\nLines"', '"Tab\tInside"', "Zero\u200bWidth", "Right\u200fMark", "Bell\x07"],
    ids=["newline", "tab", "zero-width-space", "direction-mark", "control"],
)
def test_rejects_invisible_or_control_characters_in_names(name):
    with pytest.raises(InputError, match="control or invisible character"):
        read(HEADER + f"1974-08-17,{name},B,1,0\n")


def test_team_cannot_play_itself_under_a_different_spelling():
    with pytest.raises(InputError, match="cannot play itself"):
        read(HEADER + "1974-08-17,Leeds United,leeds  united,1,0\n")
