# Mistakes and missing requirements to fix:
# - The heap example never processes numbers using a size-k min-heap or
#   asserts that sorted(heap, reverse=True) matches nlargest(k, numbers).
# - insort(arr, 7) mutates arr and returns None; assert on arr afterward.
# - list(groups) exhausts the groupby iterator; calling it again gives [],
#   so indexing the second result raises IndexError.
# - Each group is an iterator, not a list; materialize it while iterating
#   groupby, before advancing to the next group (they share the input).
# - fetch returns the literal "name" instead of its name argument.
# - gather returns all three results in argument order; the expected list
#   must include "etan" after "styve" and "ato" once fetch is fixed.

'''Steps

Create ai/w01-stdlib-drill/stdlib_drill.py. For each item below write a short working example ending in an assert:
collections.Counter: Counter('abracadabra').most_common(1) == [('a', 5)]
defaultdict(list) grouping words by first letter
deque: appendleft, popleft, and maxlen=3 dropping the oldest item
k largest of a list two ways: a size-k min-heap with heapq.heappush/heappushpop, and heapq.nlargest; assert both agree
bisect.insort keeping a list sorted, and bisect_left finding an insert position
@dataclass(order=True) with the sort-key field first, then sorted() on instances
itertools.groupby on sorted data (assert it gives wrong groups on unsorted data)
threading.Lock guarding a counter incremented 10,000 times by each of 4 threads (assert total 40,000)
asyncio.gather over 3 coroutines, asserting results come back in argument order
'''
from collections import Counter, defaultdict, deque
from heapq import heappush, nlargest, heappushpop
from bisect import insort, bisect_left
from itertools import groupby
from threading import Lock, Thread
from dataclasses import dataclass
from asyncio import gather, sleep, run

counts = Counter('abracadabra')

assert counts.most_common(1) == [('a', 5)]
assert counts.most_common(3) == [('a', 5), ('b', 2), ('r', 2)]

words = ["good", "bad", "food", "apps", "beta"]
letter_to_word = defaultdict(list)
for w in words:
    letter_to_word[w[0]].append(w)

assert letter_to_word["b"] == ["bad", "beta"]

d = deque([], maxlen=3)
d.appendleft(2)
d.appendleft(4)
d.appendleft(7)
assert list(d) == [7, 4, 2]
d.appendleft(8)
assert  list(d) == [8, 7, 4]


numbers = [2, 3, 6, 7, 1, 4, 3]
largest_count = 3
heap = []
for number in numbers:
    if len(heap) < largest_count:
        heappush(heap, number)
    else:
        heappushpop(heap, number)

assert len(heap) == largest_count
assert sorted(heap, reverse=True) == nlargest(largest_count, numbers) == [7, 6, 4]


arr = [1, 3, 5, 10, 12]
insort(arr, 7)
assert arr == [1, 3, 5, 7, 10, 12]
assert bisect_left(arr, 5) == 2


@dataclass(order=True)
class Person:
    """ A Person Class. """
    age: int
    name: str


p1 = Person(6, "Chudah")
p2 = Person(6, "Ato")
p3 = Person(5, "Eto")

ps = [p1, p2, p3]

assert sorted(ps) == [p3, p2, p1]

nums = [2, 8, 4, 5, 6]


def is_even(number: int) -> bool:
    return number % 2 == 0


unsorted_groups = [
    (key, list(values)) for key, values in groupby(nums, key=is_even)
]
assert unsorted_groups == [(True, [2, 8, 4]), (False, [5]), (True, [6])]

sorted_nums = sorted(nums, key=is_even)
groups = [
    (key, list(values)) for key, values in groupby(sorted_nums, key=is_even)
]
assert groups == [(False, [5]), (True, [2, 8, 4, 6])]
assert unsorted_groups != groups

counter = 0
lock = Lock()
def increment_10000():
    global counter
    for _ in range(10000):
        with lock:
            counter += 1

threads = []
for i in range(4):
    threads.append(Thread(target=increment_10000))

for t in threads:
    t.start()

for t in threads:
    t.join()

assert counter == 40000



async def fetch(name: str, time: int):
    await sleep(time)
    return name

async def main():
    funcs = [fetch("styve", 3), fetch("ato", 2), fetch("etan", 1)]
    results = await gather(*funcs)
    assert results == ['styve', 'ato', 'etan']


run(main())

