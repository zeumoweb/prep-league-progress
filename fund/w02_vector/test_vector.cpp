// Tests for the Week 2 Fund cards: Vector<T> part 1 (storage, growth, emplace) and,
// with -DVECTOR_PART2, part 2 (copy/move, pop_back/clear/iterators, strong guarantee).
//
// Expects vector.hpp to define template <class T> class Vector with the card's API.
//
// Part 1:  clang++ -std=c++20 -g -Wall -Wextra -fsanitize=address,undefined test_vector.cpp -o test_vector && ./test_vector
// Part 2:  add -DVECTOR_PART2 to the command above.

#include "vector.hpp"

#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <utility>

// ---------------------------------------------------------------------------
// Tiny test harness: CHECK records failures and keeps going; each TEST runs in main().
// ---------------------------------------------------------------------------
static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                              \
    do {                                                                         \
        ++g_checks;                                                              \
        if (!(cond)) {                                                           \
            ++g_failures;                                                        \
            std::printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);        \
        }                                                                        \
    } while (0)

#define CHECK_EQ(a, b)                                                           \
    do {                                                                         \
        ++g_checks;                                                              \
        auto _va = (a);                                                          \
        auto _vb = (b);                                                          \
        if (!(_va == _vb)) {                                                     \
            ++g_failures;                                                        \
            std::printf("  FAIL %s:%d: %s == %s (got %lld vs %lld)\n", __FILE__,  \
                        __LINE__, #a, #b, (long long)_va, (long long)_vb);       \
        }                                                                        \
    } while (0)

// ---------------------------------------------------------------------------
// Counted: tracks every construction, copy, move and destruction.
// After any vector goes out of scope, constructions must equal destructions.
// ---------------------------------------------------------------------------
struct Counted {
    static inline int defaults = 0, values = 0, copies = 0, moves = 0, destroys = 0;
    static void reset() { defaults = values = copies = moves = destroys = 0; }
    static int constructed() { return defaults + values + copies + moves; }
    static int alive() { return constructed() - destroys; }

    int v;
    Counted() : v(0) { ++defaults; }
    explicit Counted(int x) : v(x) { ++values; }
    Counted(const Counted& o) : v(o.v) { ++copies; }
    Counted(Counted&& o) noexcept : v(o.v) { o.v = -1; ++moves; }
    Counted& operator=(const Counted& o) { v = o.v; return *this; }
    Counted& operator=(Counted&& o) noexcept { v = o.v; o.v = -1; return *this; }
    ~Counted() { ++destroys; }
};

// Balance check run after each test's vectors are destroyed.
#define CHECK_BALANCED() CHECK_EQ(Counted::alive(), 0)

#define TEST(name) static void name()
#define RUN(name)                                                                \
    do {                                                                         \
        int before = g_failures;                                                 \
        Counted::reset();                                                        \
        name();                                                                  \
        std::printf("%s %s\n", g_failures == before ? "ok  " : "FAIL", #name);   \
    } while (0)

// ===========================================================================
// Part 1: storage, growth, emplace
// ===========================================================================

TEST(default_constructed_is_empty) {
    Vector<int> v;
    CHECK_EQ(v.size(), 0u);
    CHECK_EQ(v.capacity(), 0u);
}

TEST(sized_constructor_value_initialises_n_elements) {
    {
        Vector<int> v(5);
        CHECK_EQ(v.size(), 5u);
        CHECK(v.capacity() >= 5u);
        for (std::size_t i = 0; i < v.size(); ++i) CHECK_EQ(v[i], 0);  // value-initialised
    }
    {
        Vector<Counted> v(3);
        CHECK_EQ(v.size(), 3u);
        CHECK_EQ(Counted::defaults, 3);
    }
    CHECK_BALANCED();
}

TEST(growth_doubles_from_one) {
    Vector<int> v;
    const std::size_t expected[] = {1, 2, 4, 4, 8, 8, 8, 8, 16};
    for (int i = 0; i < 9; ++i) {
        v.push_back(i);
        CHECK_EQ(v.capacity(), expected[i]);
        CHECK_EQ(v.size(), (std::size_t)i + 1);
    }
    for (int i = 0; i < 9; ++i) CHECK_EQ(v[i], i);
}

TEST(push_back_lvalue_copies_once) {
    {
        Vector<Counted> v;
        v.reserve(4);  // no reallocation during the push below
        Counted c(7);
        int copies = Counted::copies, moves = Counted::moves;
        v.push_back(c);
        CHECK_EQ(Counted::copies - copies, 1);
        CHECK_EQ(Counted::moves - moves, 0);
        CHECK_EQ(v[0].v, 7);
        CHECK_EQ(c.v, 7);  // source untouched
    }
    CHECK_BALANCED();
}

TEST(push_back_rvalue_moves_not_copies) {
    {
        Vector<Counted> v;
        v.reserve(4);
        Counted c(9);
        v.push_back(std::move(c));
        CHECK_EQ(Counted::copies, 0);
        CHECK_EQ(Counted::moves, 1);
        CHECK_EQ(v[0].v, 9);
    }
    CHECK_BALANCED();
}

TEST(emplace_back_constructs_in_place_and_returns_reference) {
    {
        Vector<Counted> v;
        v.reserve(4);
        Counted& r = v.emplace_back(42);
        CHECK_EQ(Counted::values, 1);
        CHECK_EQ(Counted::copies, 0);
        CHECK_EQ(Counted::moves, 0);
        CHECK_EQ(r.v, 42);
        CHECK(&r == &v[0]);
        r.v = 43;
        CHECK_EQ(v[0].v, 43);
    }
    CHECK_BALANCED();
}

TEST(emplace_back_forwards_multiple_arguments) {
    Vector<std::string> v;
    v.emplace_back(3, 'x');  // std::string(3, 'x')
    CHECK(v[0] == "xxx");
}

TEST(subscript_returns_mutable_reference) {
    Vector<int> v;
    v.push_back(1);
    v.push_back(2);
    v[1] = 20;
    CHECK_EQ(v[1], 20);
    const Vector<int>& cv = v;
    CHECK_EQ(cv[0], 1);  // const overload
}

TEST(reserve_grows_exactly_and_keeps_contents) {
    Vector<std::string> v;
    v.push_back("alpha");
    v.push_back("beta");
    v.reserve(10);
    CHECK_EQ(v.capacity(), 10u);
    CHECK_EQ(v.size(), 2u);
    CHECK(v[0] == "alpha");
    CHECK(v[1] == "beta");
}

TEST(reserve_smaller_or_equal_does_nothing) {
    Vector<int> v;
    v.reserve(8);
    v.push_back(5);
    v.reserve(4);
    CHECK_EQ(v.capacity(), 8u);
    v.reserve(8);
    CHECK_EQ(v.capacity(), 8u);
    CHECK_EQ(v[0], 5);
}

TEST(non_trivial_elements_survive_reallocation) {
    Vector<std::string> v;
    for (int i = 0; i < 50; ++i) v.push_back("item-" + std::to_string(i) + std::string(20, '#'));  // heap strings
    CHECK_EQ(v.size(), 50u);
    for (int i = 0; i < 50; ++i) CHECK(v[i] == "item-" + std::to_string(i) + std::string(20, '#'));
}

TEST(push_back_of_own_element_during_growth) {
    // v[0] refers into the old buffer; reallocation must not destroy it before the copy is made.
    Vector<std::string> v;
    v.push_back(std::string(30, 'a'));  // capacity 1, so the next push reallocates
    v.push_back(v[0]);
    CHECK_EQ(v.size(), 2u);
    CHECK(v[1] == std::string(30, 'a'));
    v.push_back(v[1]);  // capacity 2 -> 4
    CHECK(v[2] == std::string(30, 'a'));
}

TEST(destructor_destroys_every_element) {
    {
        Vector<Counted> v;
        for (int i = 0; i < 10; ++i) v.emplace_back(i);  // includes reallocations
        CHECK_EQ(Counted::alive(), 10);  // only the 10 live elements remain
    }
    CHECK_BALANCED();
}

// ===========================================================================
// Part 2: copy/move, pop_back/clear/iterators, strong guarantee
// ===========================================================================
#ifdef VECTOR_PART2

// Copyable, but its move constructor is NOT noexcept, so growth must copy.
struct ThrowingMove {
    static inline int copies = 0, moves = 0;
    int v;
    explicit ThrowingMove(int x) : v(x) {}
    ThrowingMove(const ThrowingMove& o) : v(o.v) { ++copies; }
    ThrowingMove(ThrowingMove&& o) : v(o.v) { ++moves; }  // not noexcept
};

// Throws on the Nth copy (counting from 1) after arm(N).
struct ThrowOnCopy {
    static inline int copies_until_throw = -1, alive = 0;
    static void arm(int n) { copies_until_throw = n; }
    int v;
    explicit ThrowOnCopy(int x) : v(x) { ++alive; }
    ThrowOnCopy(const ThrowOnCopy& o) : v(o.v) {
        if (copies_until_throw > 0 && --copies_until_throw == 0) throw std::runtime_error("copy failed");
        ++alive;
    }
    ThrowOnCopy(ThrowOnCopy&&) = delete;  // forces copies during growth
    ~ThrowOnCopy() { --alive; }
};

TEST(copy_constructor_is_deep) {
    {
        Vector<std::string> a;
        a.push_back("one");
        a.push_back("two");
        Vector<std::string> b(a);
        CHECK_EQ(b.size(), 2u);
        b[0] = "changed";
        CHECK(a[0] == "one");  // independent storage
        CHECK(b[1] == "two");
    }
    {
        Vector<Counted> a;
        a.emplace_back(1);
        a.emplace_back(2);
        Vector<Counted> b(a);
        CHECK_EQ(b[1].v, 2);
    }
    CHECK_BALANCED();
}

TEST(copy_assignment_replaces_contents) {
    {
        Vector<Counted> a, b;
        a.emplace_back(1);
        a.emplace_back(2);
        b.emplace_back(9);
        b = a;
        CHECK_EQ(b.size(), 2u);
        CHECK_EQ(b[0].v, 1);
        CHECK_EQ(b[1].v, 2);
        b = b;  // self-assignment must be safe
        CHECK_EQ(b.size(), 2u);
        CHECK_EQ(b[1].v, 2);
    }
    CHECK_BALANCED();
}

TEST(move_constructor_steals_and_empties_source) {
    {
        Vector<Counted> a;
        a.emplace_back(1);
        a.emplace_back(2);
        int copies = Counted::copies, moves = Counted::moves;
        Vector<Counted> b(std::move(a));
        CHECK_EQ(Counted::copies - copies, 0);  // buffer stolen, no per-element work
        CHECK_EQ(Counted::moves - moves, 0);
        CHECK_EQ(b.size(), 2u);
        CHECK_EQ(a.size(), 0u);
        CHECK_EQ(a.capacity(), 0u);
        a.push_back(Counted(5));  // moved-from vector must stay usable
        CHECK_EQ(a[0].v, 5);
    }
    CHECK_BALANCED();
}

TEST(move_assignment_steals_and_empties_source) {
    {
        Vector<Counted> a, b;
        a.emplace_back(1);
        b.emplace_back(7);
        b.emplace_back(8);
        b = std::move(a);
        CHECK_EQ(b.size(), 1u);
        CHECK_EQ(b[0].v, 1);
        CHECK_EQ(a.size(), 0u);
        CHECK_EQ(a.capacity(), 0u);
    }
    CHECK_BALANCED();
}

TEST(pop_back_and_clear) {
    {
        Vector<Counted> v;
        for (int i = 0; i < 5; ++i) v.emplace_back(i);
        v.pop_back();
        CHECK_EQ(v.size(), 4u);
        CHECK_EQ(Counted::alive(), 4);  // popped element destroyed
        std::size_t cap = v.capacity();
        v.clear();
        CHECK_EQ(v.size(), 0u);
        CHECK_EQ(v.capacity(), cap);  // clear keeps capacity
        CHECK_EQ(Counted::alive(), 0);
        v.emplace_back(10);  // reusable after clear
        CHECK_EQ(v[0].v, 10);
    }
    CHECK_BALANCED();
}

TEST(begin_end_iterate_all_elements) {
    Vector<int> v;
    for (int i = 1; i <= 4; ++i) v.push_back(i);
    int sum = 0;
    for (int x : v) sum += x;
    CHECK_EQ(sum, 10);
    CHECK_EQ(v.end() - v.begin(), 4);
    Vector<int> empty;
    CHECK(empty.begin() == empty.end());
}

TEST(growth_copies_when_move_may_throw) {
    Vector<ThrowingMove> v;
    v.push_back(ThrowingMove(1));  // capacity 1 (one move into place)
    ThrowingMove::copies = ThrowingMove::moves = 0;
    v.push_back(ThrowingMove(2));  // reallocation: the existing element must be COPIED
    CHECK_EQ(ThrowingMove::copies, 1);
    CHECK_EQ(ThrowingMove::moves, 1);  // only the new element is moved in
}

TEST(growth_moves_when_move_is_noexcept) {
    {
        Vector<Counted> v;
        v.emplace_back(1);
        v.emplace_back(2);  // capacity 2, full
        int copies = Counted::copies, moves = Counted::moves;
        v.emplace_back(3);  // reallocation moves the 2 existing elements
        CHECK_EQ(Counted::copies - copies, 0);
        CHECK_EQ(Counted::moves - moves, 2);
    }
    CHECK_BALANCED();
}

TEST(reserve_gives_strong_guarantee_when_copy_throws) {
    {
        Vector<ThrowOnCopy> v;
        v.reserve(4);
        for (int i = 0; i < 4; ++i) v.emplace_back(i);
        ThrowOnCopy::arm(3);  // 3rd copy during reallocation throws
        bool threw = false;
        try {
            v.reserve(16);
        } catch (const std::runtime_error&) {
            threw = true;
        }
        ThrowOnCopy::arm(-1);
        CHECK(threw);
        CHECK_EQ(v.size(), 4u);       // unchanged
        CHECK_EQ(v.capacity(), 4u);   // unchanged
        for (int i = 0; i < 4; ++i) CHECK_EQ(v[i].v, i);
        CHECK_EQ(ThrowOnCopy::alive, 4);  // partial copies were destroyed
    }
    CHECK_EQ(ThrowOnCopy::alive, 0);
}

#endif  // VECTOR_PART2

int main() {
    RUN(default_constructed_is_empty);
    RUN(sized_constructor_value_initialises_n_elements);
    RUN(growth_doubles_from_one);
    RUN(push_back_lvalue_copies_once);
    RUN(push_back_rvalue_moves_not_copies);
    RUN(emplace_back_constructs_in_place_and_returns_reference);
    RUN(emplace_back_forwards_multiple_arguments);
    RUN(subscript_returns_mutable_reference);
    RUN(reserve_grows_exactly_and_keeps_contents);
    RUN(reserve_smaller_or_equal_does_nothing);
    RUN(non_trivial_elements_survive_reallocation);
    RUN(push_back_of_own_element_during_growth);
    RUN(destructor_destroys_every_element);
#ifdef VECTOR_PART2
    RUN(copy_constructor_is_deep);
    RUN(copy_assignment_replaces_contents);
    RUN(move_constructor_steals_and_empties_source);
    RUN(move_assignment_steals_and_empties_source);
    RUN(pop_back_and_clear);
    RUN(begin_end_iterate_all_elements);
    RUN(growth_copies_when_move_may_throw);
    RUN(growth_moves_when_move_is_noexcept);
    RUN(reserve_gives_strong_guarantee_when_copy_throws);
#endif
    std::printf("\n%d checks, %d failed\n", g_checks, g_failures);
    return g_failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
