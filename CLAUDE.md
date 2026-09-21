# CLAUDE.md

A Python command-line app that calculates a football league table from match
results using the **1974/75 English First Division** rules. This is a coding
test submission, so keep it simple, readable and well tested.

## Commands

- Run: `python -m standings data/results_1974-75_week10.csv` (stdin/stdout by default, `-o FILE` to write a file)
- Test: `.venv/Scripts/python -m pytest` (Windows) / `.venv/bin/pytest` (macOS/Linux)
- Set up: `python -m venv .venv` then `pip install pytest` (the package itself needs no install)
- Must stay compatible with Python 3.9, the `python3` that ships with macOS. Keep `from __future__ import annotations` in modules that use `X | None` hints.

## Domain rules (do not "modernise" these)

- A win is worth 2 points, a draw 1 and a loss 0. Do not use 3 points for a win.
- Ties on points are broken by **goal average** (GF / GA), then goals scored. Do not use goal difference.
- Compare goal average as a `Fraction`, never a float. Show it to 3 decimal places.
- A team with 0 goals conceded has no goal average (`None`). It ranks above any finite average and the cell is written empty.
- Teams still fully level share a position and are listed alphabetically.
- "Week 10" means every match up to and including the week of Saturday 19 October 1974 (148 matches).

## Conventions

- Use only the standard library at runtime. pytest is the only dev dependency.
- The code must run on macOS. Use no platform-specific paths or behaviour, and open CSV files with `newline=""` and `encoding="utf-8"`.
- Input errors raise `InputError` with a line number. The CLI prints them to stderr and exits with status 1.
- `data/standings_1974-75_week10.csv` is a golden file that `tests/test_cli.py` checks. Regenerate it only when output is meant to change:
  `python -m standings data/results_1974-75_week10.csv -o data/standings_1974-75_week10.csv`
- Input validation rejects: goals that aren't plain ASCII digits or exceed `MAX_GOALS` (999), dates not written exactly `YYYY-MM-DD` (newer Pythons' `fromisoformat` accepts more, so check the shape first), team names with control/invisible characters or starting with `=`, `+`, `-`, `@` (CSV injection; `FORMULA_PREFIXES`), names that differ only in capitalisation or spacing (compared after NFC normalisation), and a team with two matches on one date. Every error names the line.
- Behaviour must be identical on Python 3.9 to 3.13. Watch for standard-library differences (csv NUL handling, `int()` digit limits, `date.fromisoformat`).
- No input may produce a traceback: all input problems become `InputError`. `tests/test_fuzz.py` enforces this; keep it passing.
- Output files are written atomically (temp file + `os.replace`). Never write the output over the input file.
- Standard streams are switched to UTF-8 with Unix (`\n`) line endings in `cli.py`, so output is identical on every platform.
- `PUBLISHED_FINAL_TABLE` in `tests/test_1974_75_data.py` is copied from the published 1974/75 final table. Never regenerate it from this code; it is the independent check.
- CI (`.github/workflows/tests.yml`) runs on macOS, Linux and Windows with Python 3.9, 3.12 and 3.13.
- Keep the rules in `table.py`, CSV handling in `csv_io.py` and argument handling in `cli.py`.
