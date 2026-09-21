"""Command-line entry point: results CSV in, league table CSV out."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from standings.csv_io import InputError, read_results, write_table
from standings.table import compute_table

EXIT_OK = 0
EXIT_INPUT_ERROR = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="league-table",
        description=(
            "Calculate a football league table from match results using "
            "1974/75 English First Division rules (2 points for a win, "
            "ties broken by goal average)."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="results CSV file (default: read from stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="file to write the table CSV to (default: stdout)",
    )
    return parser


def _use_utf8_standard_streams() -> None:
    """Make stdin/stdout/stderr UTF-8 with Unix line endings on every platform.

    Without this, Python uses the system's default encoding, which on Windows
    is not UTF-8, so team names with accents would be misread.
    """
    for stream, newline in ((sys.stdin, ""), (sys.stdout, "\n"), (sys.stderr, None)):
        if hasattr(stream, "reconfigure"):  # absent on test replacements like StringIO
            stream.reconfigure(encoding="utf-8", newline=newline)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _use_utf8_standard_streams()

    try:
        if args.input == "-":
            results = read_results(sys.stdin)
        else:
            with open(args.input, newline="", encoding="utf-8") as stream:
                results = read_results(stream)
    except OSError as error:
        print(f"league-table: cannot read {args.input}: {error.strerror}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except InputError as error:
        source = "<stdin>" if args.input == "-" else args.input
        print(f"league-table: {source}: {error}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    standings = compute_table(results)

    try:
        if args.output == "-":
            write_table(standings, sys.stdout)
        else:
            with open(args.output, "w", newline="", encoding="utf-8") as stream:
                write_table(standings, stream)
    except OSError as error:
        print(f"league-table: cannot write {args.output}: {error.strerror}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    return EXIT_OK
