"""The README shows the week-10 table; it must always match the committed output file."""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README = PROJECT_ROOT / "README.md"
EXPECTED_TABLE = PROJECT_ROOT / "data" / "standings_1974-75_week10.csv"
START, END = "<!-- standings:start -->", "<!-- standings:end -->"


def render_table(csv_path: Path) -> str:
    """The Markdown table for a standings CSV, numeric columns right-aligned."""
    with csv_path.open(newline="", encoding="utf-8") as stream:
        header, *rows = list(csv.reader(stream))
    align = [":---" if name == "Team" else "---:" for name in header]
    lines = [header, align, *rows]
    return "\n".join("| " + " | ".join(cells) + " |" for cells in lines)


def test_readme_table_matches_committed_standings():
    text = README.read_text(encoding="utf-8")
    assert START in text and END in text, f"README needs {START} and {END} markers"
    shown = text.split(START, 1)[1].split(END, 1)[0].strip()
    expected = render_table(EXPECTED_TABLE)
    assert shown == expected, "README table is out of date; replace it with:\n" + expected
