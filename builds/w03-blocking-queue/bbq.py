import threading
import time

class Closed(Exception):
    pass

"""
Requirements
put(item, timeout=None): blocks while full; raises TimeoutError on timeout; raises Closed if closed, including while waiting.
get(timeout=None): returns the oldest item (FIFO); blocks while empty; raises TimeoutError on timeout. After close() it drains remaining items, then raises Closed.
size() returns the item count. close() is idempotent and calls notify_all() on both conditions so every blocked thread wakes.
Example: q = BoundedBlockingQueue(2); q.put(1); q.put(2); q.put(3, timeout=0.1) raises TimeoutError. After q.close(), get() returns 1, then 2, then raises Closed.
Tests: 8 producers x 8 consumers x 10,000 items, each received exactly once (check with a Counter); put and get timeouts; close() wakes blocked getters and putters and every thread passes join(timeout=2).
"""

class BoundedBlockingQueue:

    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("Capacity should be greater than 1")
        self.capacity = capacity
        self.closed = False
        self.lock = threading.Lock()
        self.not_full = threading.Condition(self.lock )
        self.not_empty = threading.Condition(self.lock )
        self.q = []

    def put(self, item, timeout=None):
        with self.not_full:
            # Fix the deadline once so wakeups that find the queue still full don't restart the clock.
            deadline = None if timeout is None else time.monotonic() + timeout
            while len(self.q) >= self.capacity and not self.closed:
                if deadline is None:
                    self.not_full.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    self.not_full.wait(remaining)
            if self.closed:
                raise Closed("Queue is closed")
            self.q.append(item)
            self.not_empty.notify()

    def get(self, timeout=None):
        with self.not_empty:
            deadline = None if timeout is None else time.monotonic() + timeout
            while not self.q and not self.closed:
                if deadline is None:
                    self.not_empty.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    self.not_empty.wait(remaining)
            if self.closed and not self.q:
                raise Closed("Queue is closed")
            value = self.q.pop(0)
            self.not_full.notify()
            return value


    def close(self):
        with self.lock:
            self.closed = True
            self.not_full.notify_all()
            self.not_empty.notify_all()


    def size(self):
        with self.lock:
            return len(self.q)
