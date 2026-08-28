"""Tests for the concurrent agent pass in engine.py.

The per-asset analyze() calls are dispatched in parallel because each one
blocks on an LLM request. That is only acceptable if it changes timing and
nothing else, so these tests pin both halves of that claim: the calls really
do overlap, and the results are identical and in the same order as running
them one at a time.
"""
import threading
import time

from decision.decision_schema import RegimeType
from engine import AutonomousLoop, _AgentJob
from feedback.adaptation_engine import AdaptiveState

DELAY = 0.15


class StubAgent:
    """Stands in for a market agent whose analyze() blocks on the network."""

    def __init__(self, name):
        self.name = name
        self.threads = []

    def analyze(self, event, regime, memory_hint, *, available_capital,
                has_position, adaptive_confidence_mult, adaptive_size_mult):
        self.threads.append(threading.current_thread().name)
        time.sleep(DELAY)
        return {
            "asset": event,
            "agent": self.name,
            "capital": available_capital,
            "has_position": has_position,
            "confidence_mult": adaptive_confidence_mult,
            "size_mult": adaptive_size_mult,
            "hint": memory_hint,
            "regime": regime,
        }


def make_jobs(n, shared_agent=None):
    jobs = []
    for i in range(n):
        agent = shared_agent or StubAgent(f"agent-{i}")
        jobs.append(_AgentJob(
            agent=agent,
            event=f"ASSET_{i}",
            regime=RegimeType.NORMAL,
            memory_hint={"success_rate": None, "summary": f"hint {i}"},
            has_position=bool(i % 2),
            adaptive=AdaptiveState(confidence_multiplier=0.9, size_multiplier=0.8),
        ))
    return jobs


def loop():
    """An AutonomousLoop without __init__ -- _analyze_all needs no state."""
    return AutonomousLoop.__new__(AutonomousLoop)


def test_results_keep_job_order(): 
    """The coordinator sees assets in a stable sequence regardless of which
    agent call happens to finish first."""
    jobs = make_jobs(6)

    results = loop()._analyze_all(jobs, available_capital=50_000.0)

    assert [r["asset"] for r in results] == [f"ASSET_{i}" for i in range(6)]


def test_every_job_gets_its_own_arguments():
    """Nothing is shared or overwritten between concurrent calls."""
    jobs = make_jobs(6)

    results = loop()._analyze_all(jobs, available_capital=50_000.0)

    assert [r["hint"]["summary"] for r in results] == [f"hint {i}" for i in range(6)]
    assert [r["has_position"] for r in results] == [bool(i % 2) for i in range(6)]
    assert all(r["capital"] == 50_000.0 for r in results)
    assert all(r["confidence_mult"] == 0.9 and r["size_mult"] == 0.8 for r in results)


def test_calls_actually_overlap():
    """Six 0.15s calls take ~0.15s in total, not ~0.9s."""
    jobs = make_jobs(6)

    started = time.perf_counter()
    loop()._analyze_all(jobs, available_capital=50_000.0)
    elapsed = time.perf_counter() - started

    sequential = DELAY * len(jobs)
    assert elapsed < sequential / 2, f"took {elapsed:.2f}s, barely better than {sequential:.2f}s"


def test_one_agent_instance_serves_several_assets_concurrently():
    """Two equity assets share a single EquityAgent instance -- that must be
    safe, and must still run in parallel."""
    shared = StubAgent("shared")
    jobs = make_jobs(4, shared_agent=shared)

    started = time.perf_counter()
    results = loop()._analyze_all(jobs, available_capital=50_000.0)
    elapsed = time.perf_counter() - started

    assert len(results) == 4
    assert len(set(shared.threads)) == 4, "calls were not spread across threads"
    assert elapsed < DELAY * 4 / 2


def test_concurrent_and_sequential_agree():
    """The parallel path must produce exactly what running the jobs one at a
    time produces."""
    engine = loop()
    jobs = make_jobs(6)

    concurrent = engine._analyze_all(jobs, available_capital=50_000.0)
    sequential = [engine._analyze_one(job, 50_000.0) for job in jobs]

    assert concurrent == sequential


def test_single_job_is_handled_without_a_pool():
    jobs = make_jobs(1)

    results = loop()._analyze_all(jobs, available_capital=50_000.0)

    assert len(results) == 1
    assert results[0]["asset"] == "ASSET_0"
    assert jobs[0].agent.threads == [threading.current_thread().name]


def test_no_jobs_is_not_an_error():
    assert loop()._analyze_all([], available_capital=50_000.0) == []
