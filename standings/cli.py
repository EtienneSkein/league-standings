"""Command-line entry point: results CSV in, league table CSV out."""

from __future__ import annotations

import argparse
import errno
import os
import sys
import tempfile
from typing import Iterable, Sequence

from standings.csv_io import InputError, read_results, write_table
from standings.table import Standing, compute_table

EXIT_OK = 0
EXIT_ERROR = 1


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


def _error(message: str) -> int:
    print(f"league-table: {message}", file=sys.stderr)
    return EXIT_ERROR


def _is_same_file(input_path: str, output_path: str) -> bool:
    if input_path == "-" or output_path == "-":
        return False
    try:
        return os.path.samefile(input_path, output_path)
    except OSError:  # one of them does not exist yet
        return False


def _write_file_atomically(standings: Iterable[Standing], path: str) -> None:
    """Write via a temporary file so a failure never leaves a partial table."""
    directory = os.path.dirname(os.path.abspath(path))
    handle, temporary_path = tempfile.mkstemp(dir=directory, prefix=".league-table-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", newline="", encoding="utf-8") as stream:
            write_table(standings, stream)
        os.replace(temporary_path, path)
    except BaseException:
        os.unlink(temporary_path)
        raise


def _write_stdout(standings: Iterable[Standing]) -> int:
    try:
        write_table(standings, sys.stdout)
        sys.stdout.flush()
    except OSError as error:
        # Send anything still buffered to devnull so Python does not report
        # the same failure again on exit.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        # The reader stopped early (e.g. `| head -1`): EPIPE on macOS/Linux,
        # EINVAL on Windows. That is not worth an error message.
        if error.errno in (errno.EPIPE, errno.EINVAL):
            return EXIT_ERROR
        return _error(f"cannot write <stdout>: {error.strerror}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _use_utf8_standard_streams()

    if _is_same_file(args.input, args.output):
        return _error(f"output {args.output} is the input file; choose a different output file")

    source = "<stdin>" if args.input == "-" else args.input
    try:
        if args.input == "-":
            results = read_results(sys.stdin)
        else:
            with open(args.input, newline="", encoding="utf-8") as stream:
                results = read_results(stream)
    except OSError as error:
        return _error(f"cannot read {args.input}: {error.strerror}")
    except InputError as error:
        return _error(f"{source}: {error}")

    standings = compute_table(results)

    if args.output == "-":
        return _write_stdout(standings)
    try:
        _write_file_atomically(standings, args.output)
    except OSError as error:
        return _error(f"cannot write {args.output}: {error.strerror}")
    return EXIT_OK
