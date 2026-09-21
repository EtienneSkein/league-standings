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
- Keep the rules in `table.py`, CSV handling in `csv_io.py` and argument handling in `cli.py`.
