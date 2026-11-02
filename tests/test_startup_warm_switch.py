"""API-only startup opt-in; all warmup operations are mocked, without provider calls."""

import asyncio
from copy import deepcopy
import threading
import time
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from api import main
from nestling import graph


@pytest.fixture(autouse=True)
def r1_startup(monkeypatch):
    # The retained profile can change independently of this operational switch.
    monkeypatch.setattr(graph, "APP_VERSION", "v7_vector_safe+lessons")
    monkeypatch.delenv("NESTLING_PREWARM_SOURCES", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


@pytest.mark.parametrize("value,enabled", [(None, False), ("false", False), ("0", False),
                                         ("true", True), ("1", True), (" TRUE ", True)])
def test_api_warmup_switch_does_not_change_answer_flags(monkeypatch, value, enabled):
    if value is not None:
        monkeypatch.setenv("NESTLING_PREWARM_SOURCES", value)
    flags = deepcopy(graph.VERSIONS)
    selected = graph.APP_VERSION
    warmup = Mock(return_value=None)
    monkeypatch.setattr(main, "warm_sources", warmup)

    with TestClient(main.app) as client:
        assert client.get("/api/health").status_code == 200
        assert main.app.state.sources_warmup == ("ready" if enabled else "skipped")
    assert warmup.call_count == int(enabled)
    assert graph.APP_VERSION == selected
    assert graph.VERSIONS == flags


def test_slow_warmup_stops_waiting_and_serves_health(monkeypatch):
    monkeypatch.setenv("NESTLING_PREWARM_SOURCES", "true")
    assert main.SOURCE_WARMUP_TIMEOUT_S == 5.0
    monkeypatch.setattr(main, "SOURCE_WARMUP_TIMEOUT_S", 0.02)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def slow_warmup():
        entered.set()
        try:
            release.wait(5)
        finally:
            finished.set()

    monkeypatch.setattr(main, "warm_sources", slow_warmup)
    started = time.perf_counter()
    with TestClient(main.app) as client:
        try:
            assert entered.wait(0.5)
            assert not finished.is_set()  # Timeout did not abort the worker thread.
            assert main.app.state.sources_warmup == "degraded"
            assert client.get("/api/health").status_code == 200
            assert time.perf_counter() - started < 1.5
        finally:
            # Release before TestClient closes its event-loop executor.
            release.set()
            assert finished.wait(1)


def test_opted_in_failure_keeps_only_fixed_degraded_state(monkeypatch, caplog, capsys):
    monkeypatch.setenv("NESTLING_PREWARM_SOURCES", "1")
    private_error = "provider-private-detail-never-recorded"
    monkeypatch.setattr(main, "warm_sources", Mock(side_effect=TimeoutError(private_error)))

    with TestClient(main.app) as client:
        assert client.get("/api/health").status_code == 200
        assert main.app.state.sources_warmup == "degraded"
        assert private_error not in repr(main.app.state._state)
    captured = capsys.readouterr()
    assert private_error not in caplog.text + captured.out + captured.err
