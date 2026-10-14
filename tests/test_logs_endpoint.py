import json
import urllib.error
import urllib.parse
import urllib.request

from tests._pytest_port import BASE, TEST_STATE_DIR


def _get_logs(file="agent", tail=200):
    url = f"{BASE}/api/logs?file={urllib.parse.quote(str(file))}&tail={urllib.parse.quote(str(tail))}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read()), r.status


def _get_logs_error(file="agent", tail=200):
    url = f"{BASE}/api/logs?file={urllib.parse.quote(str(file))}&tail={urllib.parse.quote(str(tail))}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def test_logs_endpoint_tails_whitelisted_synthetic_agent_log():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "agent.log").write_text(
        "\n".join(
            [f"2026-05-04 INFO synthetic-log-marker line {i}" for i in range(105)]
            + ["2026-05-04 ERROR synthetic-log-marker failed safely"]
        ) + "\n",
        encoding="utf-8",
    )

    data, status = _get_logs("agent", 100)

    assert status == 200
    assert data["file"] == "agent"
    assert data["tail"] == 100
    assert len(data["lines"]) == 100
    assert data["lines"][0] == "2026-05-04 INFO synthetic-log-marker line 6"
    assert data["lines"][-1] == "2026-05-04 ERROR synthetic-log-marker failed safely"
    assert data["truncated"] is False
    assert data["total_bytes"] > 0
    assert data["mtime"] > 0
    assert data.get("hint") == ""


def test_logs_endpoint_rejects_path_traversal_and_unknown_files():
    for bad_file in ("../../etc/passwd", "agent.log", "private", "/tmp/agent"):
        data, status = _get_logs_error(bad_file, 200)
        assert status == 400
        assert "error" in data


def test_logs_endpoint_missing_file_returns_empty_lines_with_safe_hint():
    missing = TEST_STATE_DIR / "logs" / "gateway.log"
    if missing.exists():
        missing.unlink()

    data, status = _get_logs("gateway", 200)

    assert status == 200
    assert data["file"] == "gateway"
    assert data["lines"] == []
    assert data["truncated"] is False
    assert data["total_bytes"] == 0
    assert data["mtime"] is None
    assert "not found" in data["hint"].lower()
    assert str(TEST_STATE_DIR) not in data["hint"]


def test_logs_endpoint_tail_selector_is_allowlisted_and_defaults_to_200():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "errors.log").write_text(
        "\n".join(f"2026-05-04 ERROR synthetic-log-marker line {i}" for i in range(250)) + "\n",
        encoding="utf-8",
    )

    default_data, default_status = _get_logs("errors", "not-a-number")
    capped_data, capped_status = _get_logs("errors", 999999)
    allowed_data, allowed_status = _get_logs("errors", 100)

    assert default_status == capped_status == allowed_status == 200
    assert default_data["tail"] == 200
    assert len(default_data["lines"]) == 200
    assert capped_data["tail"] == 200
    assert len(capped_data["lines"]) == 200
    assert allowed_data["tail"] == 100
    assert len(allowed_data["lines"]) == 100


def test_logs_endpoint_reads_bounded_window_and_reports_truncation():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    huge_prefix = "x" * (4 * 1024 * 1024 + 64)
    (logs_dir / "gateway.log").write_text(
        huge_prefix + "\n2026-05-04 INFO synthetic-log-marker tail survives\n",
        encoding="utf-8",
    )

    data, status = _get_logs("gateway", 1000)

    assert status == 200
    assert data["tail"] == 1000
    assert data["truncated"] is True
    assert data["lines"][-1] == "2026-05-04 INFO synthetic-log-marker tail survives"
    assert data["total_bytes"] > 4 * 1024 * 1024


def test_logs_endpoint_drops_partial_first_line_when_window_is_truncated():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    huge_prefix = "x" * (4 * 1024 * 1024 + 64)
    (logs_dir / "gateway.log").write_text(
        huge_prefix + "\n2026-05-04 INFO synthetic-log-marker tail survives\n",
        encoding="utf-8",
    )

    data, status = _get_logs("gateway", 1000)

    assert status == 200
    assert data["truncated"] is True
    # The 4 MiB window starts mid-line inside huge_prefix; the fragment must
    # be dropped so the first returned line is complete, never a run of x's.
    assert data["lines"]
    assert data["lines"][-1] == "2026-05-04 INFO synthetic-log-marker tail survives"
    assert all("x" * 64 not in line for line in data["lines"])
    assert all("�" not in line for line in data["lines"])


def test_logs_endpoint_new_line_appears_on_next_poll_without_reload():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    p = logs_dir / "agent.log"
    p.write_text(
        "2026-05-04 INFO synthetic-log-marker poll line 1\n"
        "2026-05-04 INFO synthetic-log-marker poll line 2\n",
        encoding="utf-8",
    )
    first, status1 = _get_logs("agent", 100)
    assert status1 == 200
    assert first["lines"][-2:] == [
        "2026-05-04 INFO synthetic-log-marker poll line 1",
        "2026-05-04 INFO synthetic-log-marker poll line 2",
    ]
    # Append while "watching": the next poll must show the newcomer in order.
    with p.open("a", encoding="utf-8") as fh:
        fh.write("2026-05-04 INFO synthetic-log-marker poll line 3\n")
    second, status2 = _get_logs("agent", 100)
    assert status2 == 200
    assert second["lines"][-3:] == [
        "2026-05-04 INFO synthetic-log-marker poll line 1",
        "2026-05-04 INFO synthetic-log-marker poll line 2",
        "2026-05-04 INFO synthetic-log-marker poll line 3",
    ]


def test_logs_endpoint_incomplete_line_then_completion_has_no_dup():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    p = logs_dir / "errors.log"
    p.write_text("2026-05-04 INFO synthetic-log-marker complete\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as fh:
        fh.write("2026-05-04 INFO synthetic-log-marker partial")
    mid, _ = _get_logs("errors", 100)
    assert mid["lines"][-1] == "2026-05-04 INFO synthetic-log-marker partial"
    with p.open("a", encoding="utf-8") as fh:
        fh.write("-completed\n")
    done, status = _get_logs("errors", 100)
    assert status == 200
    assert done["lines"][-2:] == [
        "2026-05-04 INFO synthetic-log-marker complete",
        "2026-05-04 INFO synthetic-log-marker partial-completed",
    ]
    assert len(done["lines"][-2:]) == len(set(done["lines"][-2:]))


def test_logs_endpoint_burst_of_twenty_lines_has_no_loss_dup_or_reorder():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    p = logs_dir / "agent.log"
    p.write_text("", encoding="utf-8")
    expected = [f"2026-05-04 INFO synthetic-log-marker burst {i}" for i in range(20)]
    with p.open("a", encoding="utf-8") as fh:
        for line in expected:
            fh.write(line + "\n")
    data, status = _get_logs("agent", 100)
    assert status == 200
    assert data["lines"][-20:] == expected
    assert len(set(data["lines"][-20:])) == 20


def test_logs_endpoint_truncated_file_returns_tail_without_stale_prefix():
    logs_dir = TEST_STATE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    p = logs_dir / "gateway.log"
    p.write_text(
        "\n".join(f"2026-05-04 INFO synthetic-log-marker gen1 line {i}" for i in range(50)) + "\n",
        encoding="utf-8",
    )
    before, _ = _get_logs("gateway", 100)
    assert any("gen1" in line for line in before["lines"])
    # Truncate/replace (rotation): the next poll must show only the new
    # content, never a stale prefix of the previous generation.
    p.write_text(
        "\n".join(f"2026-05-04 INFO synthetic-log-marker gen2 line {i}" for i in range(5)) + "\n",
        encoding="utf-8",
    )
    after, status = _get_logs("gateway", 100)
    assert status == 200
    assert after["lines"] == [
        f"2026-05-04 INFO synthetic-log-marker gen2 line {i}" for i in range(5)
    ]
    assert not any("gen1" in line for line in after["lines"])


def test_logs_endpoint_tests_use_only_synthetic_fixture_content():
    source = __import__("pathlib").Path(__file__).read_text(encoding="utf-8")
    assert "synthetic-log-marker" in source
    assert "/home/" + "michael" not in source
    assert "~/" + ".hermes/logs" not in source
    assert "TOK" + "EN=" not in source
    assert "PASS" + "WORD=" not in source
