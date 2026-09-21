"""Fuzz tests: damaged input must give a table or a clean InputError, never a crash.

Mutations are generated with fixed seeds, so every run is identical and any
failure can be reproduced from its test id.
"""

import io
import random
from pathlib import Path

import pytest

from standings.csv_io import InputError, read_results, write_table
from standings.table import compute_table

VALID_FILE = (Path(__file__).resolve().parent.parent / "data" / "results_1974-75_week10.csv").read_bytes()
INTERESTING_BYTES = b'",\r\n\x00\t -+0123456789\xef\xbb\xbf\xc3\xa9\xff'


def mutate(data: bytes, rng: random.Random) -> bytes:
    data = bytearray(data)
    for _ in range(rng.randint(1, 8)):
        position = rng.randrange(len(data) + 1)
        choice = rng.random()
        if choice < 0.3 and data:
            del data[position : position + rng.randint(1, 20)]
        elif choice < 0.6:
            data[position:position] = bytes(rng.choice(INTERESTING_BYTES) for _ in range(rng.randint(1, 5)))
        elif data:
            data[min(position, len(data) - 1)] = rng.randrange(256)
    return bytes(data)


VALID_TEXT = VALID_FILE.decode("utf-8")
# Characters that exercise CSV quoting, numbers, dates, spacing, case and Unicode.
INTERESTING_TEXT = [
    '"', ",", "\n", "\r\n", " ", "\t", "\u00a0", "\u200b", "\u0301", "\ufeff",
    "-", "+", "_", ".", "0", "1", "9", "999", "1000", "\u0661", "W", "T",
    "a", "A", "é", "É", "Liverpool", "liverpool", "1974-08-17", "1974-02-30",
]  # fmt: skip


def mutate_text(text: str, rng: random.Random) -> bytes:
    """Mutations that keep the file valid UTF-8, so they reach the deeper checks."""
    lines = text.split("\n")
    for _ in range(rng.randint(1, 4)):
        choice = rng.random()
        index = rng.randrange(len(lines))
        if choice < 0.15:
            lines.insert(index, lines[rng.randrange(len(lines))])  # duplicate a row
        elif choice < 0.25 and len(lines) > 1:
            lines[index], lines[-1] = lines[-1], lines[index]  # move a row
        else:
            line = lines[index]
            position = rng.randrange(len(line) + 1)
            cut = rng.randint(0, 3)
            lines[index] = line[:position] + rng.choice(INTERESTING_TEXT) + line[position + cut :]
    return "\n".join(lines).encode("utf-8")


def run(data: bytes) -> None:
    stream = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8", newline="")
    try:
        results = read_results(stream)
    except InputError:
        return
    write_table(compute_table(results), io.StringIO())


@pytest.mark.parametrize("seed", range(2000))
def test_mutated_file_never_crashes(seed):
    run(mutate(VALID_FILE, random.Random(seed)))


@pytest.mark.parametrize("seed", range(3000))
def test_mutated_text_never_crashes(seed):
    run(mutate_text(VALID_TEXT, random.Random(seed)))


@pytest.mark.parametrize("seed", range(300))
def test_random_bytes_never_crash(seed):
    rng = random.Random(seed)
    run(bytes(rng.randrange(256) for _ in range(rng.randint(0, 500))))


@pytest.mark.parametrize("cut", range(0, len(VALID_FILE), 97))
def test_truncated_file_never_crashes(cut):
    run(VALID_FILE[:cut])
