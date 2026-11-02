"""Tests for the Week 3 card: bounded blocking queue with threading.Condition.

Every blocking call runs in a daemon thread that is joined with a timeout, so a broken
queue makes a test fail instead of hanging the suite.

Run once:      pytest -q test_bbq.py
Run 20 times:  for i in $(seq 20); do pytest -q -x test_bbq.py || break; done
"""

import threading
import time
from collections import Counter

import pytest

from bbq import BoundedBlockingQueue, Closed

JOIN_TIMEOUT = 2.0  # the card: every thread must pass join(timeout=2)
BLOCK_CHECK = 0.1  # how long a call must stay blocked before we call it "blocked"


class Call(threading.Thread):
    """Runs fn(*args, **kwargs) in a daemon thread and records its result or exception."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__(daemon=True)
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.result = None
        self.error = None
        self.start()

    def run(self):
        try:
            self.result = self.fn(*self.args, **self.kwargs)
        except BaseException as e:  # noqa: BLE001 (re-checked by the test)
            self.error = e

    def finish(self):
        """Join with the card's timeout and fail the test if the thread is still blocked."""
        self.join(JOIN_TIMEOUT)
        assert not self.is_alive(), f"{self.fn.__name__}{self.args} still blocked after {JOIN_TIMEOUT}s"
        return self


def assert_blocked(*calls):
    time.sleep(BLOCK_CHECK)
    for c in calls:
        assert c.is_alive(), f"{c.fn.__name__}{c.args} returned instead of blocking"


def full_queue(capacity):
    q = BoundedBlockingQueue(capacity)
    for i in range(capacity):
        q.put(i)
    return q


# ---------------------------------------------------------------------------
# Construction, FIFO and size
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("capacity", [0, -1])
def test_capacity_below_one_raises_value_error(capacity):
    with pytest.raises(ValueError):
        BoundedBlockingQueue(capacity)


def test_capacity_one_is_allowed():
    q = BoundedBlockingQueue(1)
    q.put("x")
    assert q.get() == "x"


def test_get_returns_oldest_item_first():
    q = BoundedBlockingQueue(5)
    for item in ["a", "b", "c"]:
        q.put(item)
    assert [q.get(), q.get(), q.get()] == ["a", "b", "c"]


def test_size_tracks_puts_and_gets():
    q = BoundedBlockingQueue(3)
    assert q.size() == 0
    q.put(1)
    q.put(2)
    assert q.size() == 2
    q.get()
    assert q.size() == 1


def test_none_and_falsy_items_round_trip():
    # Catches implementations that use None (or truthiness) as an "empty" signal.
    q = BoundedBlockingQueue(4)
    for item in [None, 0, "", False]:
        q.put(item)
    assert [q.get() for _ in range(4)] == [None, 0, "", False]


def test_card_example():
    q = BoundedBlockingQueue(2)
    q.put(1)
    q.put(2)
    with pytest.raises(TimeoutError):
        q.put(3, timeout=0.1)
    q.close()
    assert q.get() == 1
    assert q.get() == 2
    with pytest.raises(Closed):
        q.get()


# ---------------------------------------------------------------------------
# Blocking
# ---------------------------------------------------------------------------


def test_put_blocks_while_full_and_resumes_after_get():
    q = full_queue(2)
    putter = Call(q.put, "late")
    assert_blocked(putter)
    assert q.get() == 0  # frees one slot
    putter.finish()
    assert putter.error is None
    assert [q.get(), q.get()] == [1, "late"]


def test_get_blocks_while_empty_and_resumes_after_put():
    q = BoundedBlockingQueue(2)
    getter = Call(q.get)
    assert_blocked(getter)
    q.put("hello")
    getter.finish()
    assert getter.error is None
    assert getter.result == "hello"
    assert q.size() == 0


def test_each_put_wakes_a_waiting_getter():
    q = BoundedBlockingQueue(4)
    getters = [Call(q.get) for _ in range(3)]
    assert_blocked(*getters)
    for i in range(3):
        q.put(i)
    for g in getters:
        g.finish()
        assert g.error is None
    assert sorted(g.result for g in getters) == [0, 1, 2]


def test_each_get_wakes_a_waiting_putter():
    q = full_queue(1)
    putters = [Call(q.put, f"p{i}") for i in range(3)]
    assert_blocked(*putters)
    got = [q.get(timeout=JOIN_TIMEOUT) for _ in range(4)]
    for p in putters:
        p.finish()
        assert p.error is None
    assert got[0] == 0
    assert sorted(got[1:]) == ["p0", "p1", "p2"]


# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------


def test_put_times_out_when_full_and_does_not_add_the_item():
    q = full_queue(2)
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        q.put("x", timeout=0.2)
    elapsed = time.monotonic() - start
    assert 0.15 <= elapsed < 1.0, f"timed out after {elapsed:.3f}s, expected about 0.2s"
    assert q.size() == 2
    assert [q.get(), q.get()] == [0, 1]


def test_get_times_out_when_empty():
    q = BoundedBlockingQueue(2)
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        q.get(timeout=0.2)
    elapsed = time.monotonic() - start
    assert 0.15 <= elapsed < 1.0, f"timed out after {elapsed:.3f}s, expected about 0.2s"
    assert q.size() == 0


def test_timeout_is_not_needed_when_space_or_items_exist():
    q = BoundedBlockingQueue(2)
    start = time.monotonic()
    q.put("a", timeout=5)
    assert q.get(timeout=5) == "a"
    assert time.monotonic() - start < 0.5


def test_put_with_timeout_succeeds_if_space_frees_in_time():
    q = full_queue(1)
    putter = Call(q.put, "x", timeout=2)
    assert_blocked(putter)
    q.get()
    putter.finish()
    assert putter.error is None
    assert q.get() == "x"


def test_get_with_timeout_succeeds_if_item_arrives_in_time():
    q = BoundedBlockingQueue(1)
    getter = Call(q.get, timeout=2)
    assert_blocked(getter)
    q.put("x")
    getter.finish()
    assert getter.error is None
    assert getter.result == "x"


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


def test_get_drains_remaining_items_after_close_then_raises():
    q = BoundedBlockingQueue(3)
    for i in range(3):
        q.put(i)
    q.close()
    assert q.size() == 3
    assert [q.get(), q.get(timeout=0.1), q.get()] == [0, 1, 2]
    with pytest.raises(Closed):
        q.get()
    with pytest.raises(Closed):
        q.get(timeout=0.1)  # Closed, not TimeoutError


def test_put_after_close_raises_closed_even_with_space():
    q = BoundedBlockingQueue(3)
    q.close()
    with pytest.raises(Closed):
        q.put("x")
    with pytest.raises(Closed):
        q.put("x", timeout=0.1)
    assert q.size() == 0


def test_close_is_idempotent():
    q = BoundedBlockingQueue(2)
    q.put(1)
    q.close()
    q.close()
    assert q.get() == 1
    with pytest.raises(Closed):
        q.get()


def test_close_wakes_every_blocked_getter():
    q = BoundedBlockingQueue(2)
    getters = [Call(q.get) for _ in range(4)] + [Call(q.get, timeout=30)]
    assert_blocked(*getters)
    q.close()
    for g in getters:
        g.finish()
        assert isinstance(g.error, Closed), f"expected Closed, got {g.error!r}"


def test_close_wakes_every_blocked_putter_and_drops_their_items():
    q = full_queue(2)
    putters = [Call(q.put, f"p{i}") for i in range(4)] + [Call(q.put, "t", timeout=30)]
    assert_blocked(*putters)
    q.close()
    for p in putters:
        p.finish()
        assert isinstance(p.error, Closed), f"expected Closed, got {p.error!r}"
    assert q.size() == 2
    assert [q.get(), q.get()] == [0, 1]  # only the items put before close()
    with pytest.raises(Closed):
        q.get()


def test_close_wakes_getters_and_putters_on_different_queues_at_once():
    empty = BoundedBlockingQueue(1)
    full = full_queue(1)
    threads = [Call(empty.get) for _ in range(3)] + [Call(full.put, i) for i in range(3)]
    assert_blocked(*threads)
    empty.close()
    full.close()
    for t in threads:
        t.finish()
        assert isinstance(t.error, Closed), f"expected Closed, got {t.error!r}"


# ---------------------------------------------------------------------------
# Structure required by the card (step 2)
# ---------------------------------------------------------------------------


def test_uses_one_lock_shared_by_not_full_and_not_empty():
    q = BoundedBlockingQueue(1)
    not_full = getattr(q, "not_full", None)
    not_empty = getattr(q, "not_empty", None)
    assert isinstance(not_full, threading.Condition), "expected a threading.Condition named not_full"
    assert isinstance(not_empty, threading.Condition), "expected a threading.Condition named not_empty"
    assert not_full is not not_empty
    # CPython stores a Condition's lock in _lock.
    assert not_full._lock is not_empty._lock, "both conditions must share one lock"


# ---------------------------------------------------------------------------
# Stress: 8 producers x 8 consumers x 10,000 items each
# ---------------------------------------------------------------------------


def test_stress_every_item_received_exactly_once():
    producers, consumers, per_producer, capacity = 8, 8, 10_000, 16
    q = BoundedBlockingQueue(capacity)
    received = [[] for _ in range(consumers)]
    oversize = []
    stop_watch = threading.Event()

    def produce(pid):
        for i in range(per_producer):
            q.put((pid, i))

    def consume(cid):
        out = received[cid]
        while True:
            try:
                out.append(q.get())
            except Closed:
                return

    def watch_size():
        while not stop_watch.is_set():
            n = q.size()
            if n > capacity:
                oversize.append(n)
            time.sleep(0.001)  # sample, don't spin: a busy loop would starve the workers of the lock

    watcher = Call(watch_size)
    cons = [Call(consume, c) for c in range(consumers)]
    prods = [Call(produce, p) for p in range(producers)]

    for p in prods:
        p.join(30)
        assert not p.is_alive(), "producer stuck: lost wakeup or deadlock"
        assert p.error is None, f"producer raised {p.error!r}"
    q.close()
    for c in cons:
        c.finish()
        assert c.error is None, f"consumer raised {c.error!r}"
    stop_watch.set()
    watcher.finish()

    counts = Counter(item for out in received for item in out)
    expected = {(p, i) for p in range(producers) for i in range(per_producer)}
    assert set(counts) == expected, f"{len(expected - set(counts))} items lost"
    duplicates = [item for item, n in counts.items() if n > 1]
    assert not duplicates, f"{len(duplicates)} items received more than once, e.g. {duplicates[:3]}"
    assert not oversize, f"size() exceeded capacity {capacity}: saw {max(oversize)}"
    assert q.size() == 0

    # FIFO: each consumer must see any one producer's items in the order they were put.
    for out in received:
        last = {}
        for pid, i in out:
            assert i > last.get(pid, -1), f"producer {pid}'s items arrived out of order"
            last[pid] = i
