import io
import subprocess
import sys
from pathlib import Path

from standings.cli import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = PROJECT_ROOT / "data" / "results_1974-75_week10.csv"
EXPECTED_TABLE = PROJECT_ROOT / "data" / "standings_1974-75_week10.csv"


def test_week10_table_matches_committed_output(tmp_path):
    output = tmp_path / "table.csv"
    assert main([str(RESULTS_FILE), "-o", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == EXPECTED_TABLE.read_text(encoding="utf-8")


def test_week10_table_known_positions():
    rows = EXPECTED_TABLE.read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 22
    # Liverpool top on goal average ahead of Manchester City (both 19 points).
    assert rows[0] == "1,Liverpool,13,9,1,3,21,8,2.625,19"
    assert rows[1] == "2,Manchester City,14,8,3,3,19,15,1.267,19"
    assert rows[-1] == "22,Arsenal,13,2,3,8,12,20,0.600,7"


def test_reads_stdin_and_writes_stdout(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(RESULTS_FILE.read_text(encoding="utf-8")))
    assert main([]) == 0
    assert capsys.readouterr().out == EXPECTED_TABLE.read_text(encoding="utf-8")


def test_invalid_input_reports_error_and_exits_1(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("date,home_team,away_team,home_goals,away_goals\n1974-08-17,A,B,x,0\n")
    assert main([str(bad)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "line 2: home_goals must be a whole number" in captured.err


def test_missing_file_exits_1(tmp_path, capsys):
    assert main([str(tmp_path / "missing.csv")]) == 1
    assert "cannot read" in capsys.readouterr().err


def test_runs_as_module():
    completed = subprocess.run(
        [sys.executable, "-m", "standings", str(RESULTS_FILE)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.splitlines()[1].startswith("1,Liverpool,")
