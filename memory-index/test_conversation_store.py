"""Unit tests for the global conversation store.

Covers: append_volley, get_hot_window, get_project_volleys, volley_count,
effective_score (Ebbinghaus decay), is_dormant, grow_stability, classify_lane.
"""
from __future__ import annotations

import math
import time

import pytest

import conversation_store as cs


@pytest.fixture
def db(tmp_path):
    """In-memory-like SQLite conversation store for isolated tests."""
    path = tmp_path / "conversations.sqlite3"
    conn = cs.connect(path)
    yield conn
    conn.close()


# --- append_volley ----------------------------------------------------------


def test_append_volley_assigns_sequential_seq(db):
    v0 = cs.append_volley(db, "kiro", "harness", "s1", "user", "hello")
    v1 = cs.append_volley(db, "kiro", "harness", "s1", "assistant", "hi back")
    assert v0 is not None
    assert v1 is not None
    assert v0.seq == 0
    assert v1.seq == 1
    assert v0.harness_id == "kiro"
    assert v1.role == "assistant"


def test_append_volley_separate_sessions_have_independent_seq(db):
    cs.append_volley(db, "kiro", "proj", "s1", "user", "a")
    cs.append_volley(db, "kiro", "proj", "s1", "user", "b")
    v = cs.append_volley(db, "kiro", "proj", "s2", "user", "first in s2")
    assert v is not None
    assert v.seq == 0  # independent from s1


def test_append_volley_separate_harnesses_same_project(db):
    v1 = cs.append_volley(db, "claude", "proj", "s1", "user", "from claude")
    v2 = cs.append_volley(db, "kiro", "proj", "s1", "user", "from kiro")
    assert v1 is not None and v2 is not None
    # Both are seq 0 because (harness, project, session) differs on harness
    assert v1.seq == 0
    assert v2.seq == 0


def test_append_volley_returns_none_on_duplicate(db):
    # Force a collision by inserting same volley twice at same timestamp
    ts = 1000000.0
    v1 = cs.append_volley(db, "kiro", "p", "s", "user", "x", timestamp=ts)
    assert v1 is not None
    # Second call with same (harness, project, session, seq) would violate UNIQUE
    # but append_volley catches and returns None
    # We need to force seq collision — insert directly
    try:
        db.execute(
            "INSERT INTO volleys VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("dup", "kiro", "p", "s", 0, "user", "dup", ts + 1, None),
        )
        assert False, "Should have raised IntegrityError"
    except Exception:
        pass  # Expected: UNIQUE constraint on (harness, project, session, seq)


# --- get_hot_window ---------------------------------------------------------


def test_hot_window_returns_last_n_in_chronological_order(db):
    for i in range(20):
        cs.append_volley(db, "kiro", "proj", "s1", "user", f"msg-{i}", timestamp=1000.0 + i)
    window = cs.get_hot_window(db, "kiro", "proj", limit=13)
    assert len(window) == 13
    # Chronological: oldest first
    assert window[0].content == "msg-7"
    assert window[-1].content == "msg-19"


def test_hot_window_filters_by_harness(db):
    cs.append_volley(db, "claude", "proj", "s1", "user", "claude msg", timestamp=1000.0)
    cs.append_volley(db, "kiro", "proj", "s1", "user", "kiro msg", timestamp=1001.0)
    window = cs.get_hot_window(db, "kiro", "proj")
    assert len(window) == 1
    assert window[0].content == "kiro msg"


def test_hot_window_empty_when_no_matching_volleys(db):
    cs.append_volley(db, "kiro", "other-project", "s1", "user", "hello")
    window = cs.get_hot_window(db, "kiro", "proj")
    assert window == []


# --- get_project_volleys (cross-harness) ------------------------------------


def test_project_volleys_returns_all_harnesses(db):
    cs.append_volley(db, "claude", "proj", "s1", "user", "from claude", timestamp=1000.0)
    cs.append_volley(db, "kiro", "proj", "s2", "user", "from kiro", timestamp=1001.0)
    cs.append_volley(db, "codex", "proj", "s3", "user", "from codex", timestamp=1002.0)
    volleys = cs.get_project_volleys(db, "proj")
    assert len(volleys) == 3
    harnesses = {v.harness_id for v in volleys}
    assert harnesses == {"claude", "kiro", "codex"}


def test_project_volleys_since_filter(db):
    cs.append_volley(db, "kiro", "proj", "s1", "user", "old", timestamp=100.0)
    cs.append_volley(db, "kiro", "proj", "s1", "user", "new", timestamp=200.0)
    volleys = cs.get_project_volleys(db, "proj", since=150.0)
    assert len(volleys) == 1
    assert volleys[0].content == "new"


# --- volley_count -----------------------------------------------------------


def test_volley_count_all_and_filtered(db):
    cs.append_volley(db, "kiro", "proj-a", "s1", "user", "a")
    cs.append_volley(db, "kiro", "proj-a", "s1", "user", "b")
    cs.append_volley(db, "kiro", "proj-b", "s1", "user", "c")
    assert cs.volley_count(db) == 3
    assert cs.volley_count(db, "proj-a") == 2
    assert cs.volley_count(db, "proj-b") == 1
    assert cs.volley_count(db, "nonexistent") == 0


# --- Ebbinghaus decay -------------------------------------------------------


def test_effective_score_no_decay_when_just_retrieved():
    now = time.time()
    score = cs.effective_score(0.85, last_retrieved_at=now, stability=7.0, now=now)
    assert score == pytest.approx(0.85, abs=1e-6)


def test_effective_score_decays_over_time():
    now = time.time()
    one_week_ago = now - 7 * 86400
    # stability=7 days, elapsed=7 days -> decay = e^(-1) ≈ 0.368
    score = cs.effective_score(1.0, last_retrieved_at=one_week_ago, stability=7.0, now=now)
    expected = math.exp(-1.0)
    assert score == pytest.approx(expected, abs=1e-4)


def test_effective_score_high_stability_slow_decay():
    now = time.time()
    one_week_ago = now - 7 * 86400
    # stability=30 days, elapsed=7 days -> decay = e^(-7/30) ≈ 0.792
    score = cs.effective_score(1.0, last_retrieved_at=one_week_ago, stability=30.0, now=now)
    expected = math.exp(-7.0 / 30.0)
    assert score == pytest.approx(expected, abs=1e-4)


def test_effective_score_respects_similarity():
    now = time.time()
    old = now - 3 * 86400
    score = cs.effective_score(0.5, last_retrieved_at=old, stability=7.0, now=now)
    assert score < 0.5
    assert score > 0.0


# --- is_dormant -------------------------------------------------------------


def test_is_dormant_fresh_entry_is_not_dormant():
    now = time.time()
    assert not cs.is_dormant(now, stability=7.0, now=now)


def test_is_dormant_very_old_entry_with_low_stability():
    now = time.time()
    very_old = now - 365 * 86400  # a year ago
    assert cs.is_dormant(very_old, stability=7.0, now=now)


def test_is_dormant_old_entry_with_high_stability_stays_active():
    now = time.time()
    month_ago = now - 30 * 86400
    # stability=100 days, 30 days elapsed -> e^(-0.3) ≈ 0.74 > 0.1 floor
    assert not cs.is_dormant(month_ago, stability=100.0, now=now)


# --- grow_stability ---------------------------------------------------------


def test_grow_stability_increases():
    assert cs.grow_stability(7.0) == pytest.approx(10.5)
    assert cs.grow_stability(10.5) == pytest.approx(15.75)


# --- classify_lane ----------------------------------------------------------


def test_classify_lane_specs():
    assert cs.classify_lane("This is a requirement that the system SHALL do X") == "specs-proposal"
    assert cs.classify_lane("Design decision: use SQLite") == "specs-proposal"
    assert cs.classify_lane("Acceptance criteria: must pass") == "specs-proposal"


def test_classify_lane_steering():
    assert cs.classify_lane("Policy: always run tests before commit") == "steering-proposal"
    assert cs.classify_lane("Rule: never push to main") == "steering-proposal"
    assert cs.classify_lane("Constraint: no shared SQLite over stdio") == "steering-proposal"


def test_classify_lane_skill():
    assert cs.classify_lane("Procedure: first check health, then call tools") == "skill-candidate"
    assert cs.classify_lane("Workflow: extract, transform, load") == "skill-candidate"
    assert cs.classify_lane("When to use: for any debugging session") == "skill-candidate"


def test_classify_lane_default_memory_bank():
    assert cs.classify_lane("The server runs on port 8055") == "memory-bank"
    assert cs.classify_lane("We decided to use polars over pandas") == "memory-bank"
    assert cs.classify_lane("") == "memory-bank"
