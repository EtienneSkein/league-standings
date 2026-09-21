import io
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_help_exits_0(capsys):
    with pytest.raises(SystemExit) as exit_:
        main(["--help"])
    assert exit_.value.code == 0
    assert "usage: league-table" in capsys.readouterr().out


def test_unknown_option_exits_2(capsys):
    with pytest.raises(SystemExit) as exit_:
        main(["--bogus"])
    assert exit_.value.code == 2
    assert "unrecognized arguments: --bogus" in capsys.readouterr().err


def test_unwritable_output_exits_1_without_creating_file(tmp_path, capsys):
    target = tmp_path / "no-such-dir" / "table.csv"
    assert main([str(RESULTS_FILE), "-o", str(target)]) == 1
    assert "cannot write" in capsys.readouterr().err
    assert not target.exists()


def test_invalid_input_does_not_touch_existing_output(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("date,home_team,away_team,home_goals,away_goals\n1974-08-17,A,B,x,0\n")
    output = tmp_path / "table.csv"
    output.write_text("previous contents")
    assert main([str(bad), "-o", str(output)]) == 1
    assert output.read_text() == "previous contents"


def test_existing_output_file_is_overwritten(tmp_path):
    output = tmp_path / "table.csv"
    output.write_text("stale\n" * 100)
    assert main([str(RESULTS_FILE), "-o", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == EXPECTED_TABLE.read_text(encoding="utf-8")


def test_output_is_byte_for_byte_repeatable(tmp_path):
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    assert main([str(RESULTS_FILE), "-o", str(first)]) == 0
    assert main([str(RESULTS_FILE), "-o", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes() == EXPECTED_TABLE.read_bytes()


def test_output_uses_unix_line_endings(tmp_path):
    output = tmp_path / "table.csv"
    assert main([str(RESULTS_FILE), "-o", str(output)]) == 0
    assert b"\r" not in output.read_bytes()


def test_accepts_excel_style_file_with_bom_and_crlf(tmp_path):
    excel_file = tmp_path / "excel.csv"
    content = RESULTS_FILE.read_text(encoding="utf-8").replace("\n", "\r\n")
    excel_file.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    output = tmp_path / "table.csv"
    assert main([str(excel_file), "-o", str(output)]) == 0
    assert output.read_bytes() == EXPECTED_TABLE.read_bytes()


def test_explicit_dash_means_stdin_and_stdout(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(RESULTS_FILE.read_text(encoding="utf-8")))
    assert main(["-", "-o", "-"]) == 0
    assert capsys.readouterr().out == EXPECTED_TABLE.read_text(encoding="utf-8")


def test_stdin_error_names_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not,a,header\n"))
    assert main([]) == 1
    assert capsys.readouterr().err.startswith("league-table: <stdin>: header is missing")


def test_module_reads_stdin_and_writes_stdout_as_a_real_process():
    completed = subprocess.run(
        [sys.executable, "-m", "standings"],
        cwd=PROJECT_ROOT,
        input=RESULTS_FILE.read_bytes(),
        capture_output=True,
        check=True,
    )
    assert completed.stdout == EXPECTED_TABLE.read_bytes()


def test_module_exits_1_on_bad_input_as_a_real_process():
    completed = subprocess.run(
        [sys.executable, "-m", "standings"],
        cwd=PROJECT_ROOT,
        input=b"garbage\n",
        capture_output=True,
    )
    assert completed.returncode == 1
    assert completed.stdout == b""
    assert b"header is missing" in completed.stderr


UTF8_HEADER = b"date,home_team,away_team,home_goals,away_goals\n"


def run_module_with_stdin(data):
    return subprocess.run(
        [sys.executable, "-m", "standings"],
        cwd=PROJECT_ROOT,
        input=data,
        capture_output=True,
    )


def test_stdout_is_utf8_with_unix_line_endings_on_every_platform():
    completed = run_module_with_stdin(UTF8_HEADER + "1974-08-17,Álava,B,1,0\n".encode("utf-8"))
    assert completed.returncode == 0
    assert completed.stdout.splitlines(keepends=True)[1] == "1,Álava,1,1,0,0,1,0,,2\n".encode("utf-8")


def test_stdin_is_decoded_as_utf8_on_every_platform():
    # Only correct decoding lets the capitalisation check see Álava and álava as one name.
    data = UTF8_HEADER + "1974-08-17,Álava,B,1,0\n1974-08-24,álava,C,1,0\n".encode("utf-8")
    completed = run_module_with_stdin(data)
    assert completed.returncode == 1
    assert "team 'álava' differs only in capitalisation from 'Álava'".encode("utf-8") in completed.stderr
