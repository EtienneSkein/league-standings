# League Standings

[![tests](https://github.com/EtienneSkein/league-standings/actions/workflows/tests.yml/badge.svg)](https://github.com/EtienneSkein/league-standings/actions/workflows/tests.yml)

A command-line application that calculates a football (soccer) league table from
match results. It applies the rules of the **English First Division, 1974/75**
and is used here to produce the table in **week 10** of that season.

## Requirements

- Python 3.9 or newer, so the `python3` that ships with macOS works. The
  application uses only the standard library.
- pytest, which is needed only to run the tests.

## Quick start (macOS / Linux)

```sh
# Run straight from the project root. No install is needed.
python3 -m standings data/results_1974-75_week10.csv

# Or read from stdin and write to stdout
python3 -m standings < data/results_1974-75_week10.csv > table.csv

# Or write to a file
python3 -m standings data/results_1974-75_week10.csv -o table.csv
```

## Running the tests

The tests need only pytest:

```sh
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install pytest
pytest
```

To also install the `league-table` command (this needs pip 21.3 or newer), run
`pip install -e ".[test]"`, then `league-table data/results_1974-75_week10.csv`.

### What the tests cover

| File | What it proves |
|---|---|
| `tests/test_1974_75_data.py` | **The answer is right.** The app's final 1974/75 table, calculated from all 462 results, matches the published final table exactly, row by row. The week-10 input contains exactly the 22 real clubs, the right date range and no repeated fixtures. It is also exactly the full season cut off at week 10. |
| `tests/test_table.py` | The rules: 2 points for a win, goal average rather than goal difference, then goals scored. Also teams that have conceded nothing, shared positions, and averages that look equal when rounded but aren't. |
| `tests/test_invariants.py` | Totals that must hold for any league, checked on 200 randomly generated leagues (with fixed seeds) and on the real data. Wins equal losses, goals for equal goals against, each match adds 2 points, and shuffling the input never changes the table. |
| `tests/test_csv_io.py` | Input handling: files saved by Excel (with a byte-order mark and Windows line endings), quoted and accented names, and every kind of invalid row, each with a precise error message. |
| `tests/test_cli.py` | The command line: files and stdin/stdout, exit codes, unwritable output, UTF-8 on every platform, repeatable output, and the committed output file. |

GitHub Actions runs the whole suite on macOS, Linux and Windows with Python
3.9, 3.12 and 3.13 on every push. It also checks the submission output using
the `python3` that ships with macOS.

## Input format

A CSV file with a header row and one match per line:

```csv
date,home_team,away_team,home_goals,away_goals
1974-08-17,Chelsea,Carlisle United,0,2
```

| Column | Rules |
|---|---|
| `date` | ISO date, `YYYY-MM-DD` |
| `home_team`, `away_team` | Non-empty and different from each other |
| `home_goals`, `away_goals` | Whole numbers of 0 or more, digits only (`+1`, `1.0` and `1_0` are rejected) |

The file must also be consistent:

- A team's name must be spelled with the same capitalisation everywhere.
  `Chelsea` and `chelsea` are rejected, so a typo can't create an extra team.
- A team plays at most one match per date. This also catches a result that
  has been entered twice.

The file must be UTF-8. A byte-order mark, as added by Excel's "CSV UTF-8"
option, and Windows line endings are both accepted. Header names are not
case-sensitive and may appear in any order; extra columns are ignored. Blank
lines and whitespace around values are ignored.

For any invalid input, the application prints an error with the line number to
stderr, writes no table and exits with status `1`.

## Output format

A CSV league table with the conventional column headers:

```csv
Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts
1,Liverpool,13,9,1,3,21,8,2.625,19
```

`Pos` position, `Pld` played, `W` won, `D` drawn, `L` lost, `GF` goals for,
`GA` goals against, `GAv` goal average, `Pts` points.

## Rules (English First Division, 1974/75)

1. **Points**: 2 for a win, 1 for a draw, 0 for a loss. Three points for a win
   was not introduced until 1981.
2. Teams level on points are separated by **goal average**: goals scored
   divided by goals conceded. This is *not* goal difference, which replaced
   goal average in 1976/77.
3. If goal average is also equal, **more goals scored** ranks higher.

Goal average is compared as an exact fraction (`fractions.Fraction`) so that
floating-point rounding cannot affect the order. It is shown to 3 decimal
places.

### Assumptions

- **No goals conceded.** Goal average cannot be calculated when a team has
  conceded no goals. Such a team ranks above every team on the same points
  with a finite goal average. The `GAv` cell is left empty.
- **Teams still level** after all three criteria share a position (for example
  `1, 1, 3`) and are listed alphabetically.
- **"Week 10"** means the 10th calendar week of the season. The season opened
  on Saturday 17 August 1974, so week 10 is the week of Saturday 19 October
  1974. The input contains every First Division match up to and including that
  week: 148 matches. Teams have played 12 to 14 games each by then, because
  there were also midweek fixtures.

## Data

`data/results_1974-75_week10.csv` is the input. `data/standings_1974-75_week10.csv`
is the output that the application produces from it.
`tests/fixtures/results_1974-75_full_season.csv` holds the whole season and is
used by the tests to check against the published final table.

The results come from the
[engsoccerdata](https://github.com/jalapic/engsoccerdata) dataset: James P.
Curley (2016), *engsoccerdata: English Soccer Data 1871-2016*. The dataset is
free for non-commercial use. As a spot check, the standings it gives on
5 October 1974 match published tables.

To rebuild both results files from the source (this needs network access):

```sh
python3 scripts/build_week10_results.py
```

## Project layout

```
standings/
  table.py      # rules: points, goal average, ranking
  csv_io.py     # CSV parsing, validation and output
  cli.py        # argument handling, stdin/stdout, exit codes
  __main__.py   # enables `python -m standings`
tests/          # tests (see "What the tests cover")
  fixtures/     # full 1974/75 season results
data/           # input results and generated table
scripts/        # rebuilds the results files from the source dataset
.github/        # GitHub Actions workflow (macOS, Linux, Windows)
```
