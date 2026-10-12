"""Tests for the Week 1 in-memory database (levels 1-4).

Each test mirrors a row group from the task card's example tables, plus the edge cases those
rules imply. Run with:  python -m pytest -q
"""

import pytest

from db import InMemoryDB


@pytest.fixture
def db():
    return InMemoryDB()


# ---------------------------------------------------------------------------
# Level 1: records and fields
# ---------------------------------------------------------------------------
class TestLevel1:
    def test_set_returns_none_and_get_reads_value(self, db):
        assert db.set("u1", "name", "ann") is None
        assert db.get("u1", "name") == "ann"

    def test_set_overwrites_existing_field(self, db):
        db.set("u1", "name", "ann")
        db.set("u1", "name", "bob")
        assert db.get("u1", "name") == "bob"

    def test_fields_are_independent(self, db):
        db.set("u1", "name", "ann")
        db.set("u1", "age", "30")
        assert db.get("u1", "name") == "ann"
        assert db.get("u1", "age") == "30"

    def test_records_are_independent(self, db):
        db.set("u1", "name", "ann")
        db.set("u2", "name", "bob")
        assert db.get("u1", "name") == "ann"
        assert db.get("u2", "name") == "bob"

    def test_get_missing_record_or_field_is_none(self, db):
        db.set("u1", "name", "ann")
        assert db.get("u2", "name") is None
        assert db.get("u1", "zip") is None

    def test_delete_existing_field_returns_true_then_gone(self, db):
        db.set("u1", "age", "30")
        assert db.delete("u1", "age") is True
        assert db.get("u1", "age") is None

    def test_delete_missing_field_or_record_returns_false(self, db):
        db.set("u1", "name", "ann")
        assert db.delete("u1", "zip") is False
        assert db.delete("nobody", "name") is False

    def test_delete_twice_second_is_false(self, db):
        db.set("u1", "name", "ann")
        assert db.delete("u1", "name") is True
        assert db.delete("u1", "name") is False

    def test_record_with_no_fields_left_no_longer_exists(self, db):
        db.set("u1", "name", "ann")
        db.delete("u1", "name")
        assert db.scan("u1") == []

    def test_empty_string_value_is_a_real_value(self, db):
        db.set("u1", "note", "")
        assert db.get("u1", "note") == ""


# ---------------------------------------------------------------------------
# Level 2: scanning
# ---------------------------------------------------------------------------
class TestLevel2:
    @pytest.fixture
    def u1(self, db):
        db.set("u1", "name", "ann")
        db.set("u1", "age", "30")
        db.set("u1", "nickname", "a")
        return db

    def test_scan_sorted_by_field_name(self, u1):
        assert u1.scan("u1") == ["age(30)", "name(ann)", "nickname(a)"]

    def test_scan_by_prefix(self, u1):
        assert u1.scan_by_prefix("u1", "n") == ["name(ann)", "nickname(a)"]

    def test_scan_by_prefix_no_match(self, u1):
        assert u1.scan_by_prefix("u1", "x") == []

    def test_scan_missing_record(self, db):
        assert db.scan("u9") == []
        assert db.scan_by_prefix("u9", "a") == []

    def test_prefix_is_case_sensitive(self, u1):
        assert u1.scan_by_prefix("u1", "N") == []

    def test_empty_prefix_matches_all(self, u1):
        assert u1.scan_by_prefix("u1", "") == u1.scan("u1")

    def test_full_field_name_is_a_valid_prefix(self, u1):
        assert u1.scan_by_prefix("u1", "name") == ["name(ann)"]

    def test_scan_reflects_overwrite_and_delete(self, u1):
        u1.set("u1", "name", "bob")
        u1.delete("u1", "age")
        assert u1.scan("u1") == ["name(bob)", "nickname(a)"]


# ---------------------------------------------------------------------------
# Level 3: timestamps and TTL
# ---------------------------------------------------------------------------
class TestLevel3:
    def test_card_example_sequence(self, db):
        assert db.set_at_with_ttl("k", "f", "v", 10, 5) is None
        assert db.get_at("k", "f", 14) == "v"
        assert db.get_at("k", "f", 15) is None
        assert db.set_at("k", "g", "w", 16) is None
        assert db.scan_at("k", 20) == ["g(w)"]
        assert db.set_at_with_ttl("k", "g", "x", 21, 3) is None
        assert db.get_at("k", "g", 24) is None
        assert db.delete_at("k", "g", 25) is False

    def test_alive_at_start_timestamp(self, db):
        db.set_at_with_ttl("k", "f", "v", 10, 5)
        assert db.get_at("k", "f", 10) == "v"

    def test_expiry_is_exclusive(self, db):
        db.set_at_with_ttl("k", "f", "v", 10, 5)
        assert db.get_at("k", "f", 14) == "v"
        assert db.get_at("k", "f", 15) is None

    def test_set_at_never_expires(self, db):
        db.set_at("k", "f", "v", 1)
        assert db.get_at("k", "f", 10**9) == "v"

    def test_overwrite_with_ttl_restarts_ttl(self, db):
        db.set_at_with_ttl("k", "f", "v1", 10, 5)   # would expire at 15
        db.set_at_with_ttl("k", "f", "v2", 13, 5)   # now expires at 18
        assert db.get_at("k", "f", 16) == "v2"
        assert db.get_at("k", "f", 18) is None

    def test_set_at_removes_existing_ttl(self, db):
        db.set_at_with_ttl("k", "f", "v1", 10, 5)
        db.set_at("k", "f", "v2", 12)
        assert db.get_at("k", "f", 100) == "v2"

    def test_delete_at_alive_field(self, db):
        db.set_at_with_ttl("k", "f", "v", 10, 5)
        assert db.delete_at("k", "f", 12) is True
        assert db.get_at("k", "f", 13) is None

    def test_delete_at_expired_field_is_false(self, db):
        db.set_at_with_ttl("k", "f", "v", 10, 5)
        assert db.delete_at("k", "f", 15) is False

    def test_scan_by_prefix_at_skips_expired(self, db):
        db.set_at_with_ttl("k", "name", "ann", 1, 2)   # expires at 3
        db.set_at("k", "nick", "a", 1)
        assert db.scan_by_prefix_at("k", "n", 2) == ["name(ann)", "nick(a)"]
        assert db.scan_by_prefix_at("k", "n", 3) == ["nick(a)"]

    def test_record_with_only_expired_fields_scans_empty(self, db):
        db.set_at_with_ttl("k", "f", "v", 1, 1)
        assert db.scan_at("k", 5) == []


# ---------------------------------------------------------------------------
# Level 4: backup and restore
# ---------------------------------------------------------------------------
class TestLevel4:
    def test_card_example_sequence(self, db):
        db.set_at_with_ttl("a", "f", "1", 10, 10)  # expires at 20
        db.set_at("b", "g", "2", 11)
        assert db.backup(15) == 2                   # a.f has 5 left
        db.set_at("a", "h", "3", 16)                # not in the backup
        assert db.restore(30, 17) is None           # uses backup from 15
        assert db.get_at("a", "f", 34) == "1"       # new expiry 30 + 5 = 35
        assert db.get_at("a", "f", 35) is None
        assert db.get_at("a", "h", 31) is None
        assert db.get_at("b", "g", 31) == "2"

    def test_backup_counts_only_records_with_alive_fields(self, db):
        db.set_at_with_ttl("a", "f", "1", 1, 2)   # expires at 3
        db.set_at("b", "g", "2", 1)
        assert db.backup(5) == 1

    def test_backup_of_empty_db(self, db):
        assert db.backup(1) == 0

    def test_backup_excludes_expired_fields(self, db):
        db.set_at_with_ttl("a", "f", "1", 1, 2)   # expires at 3
        db.set_at("a", "g", "2", 1)
        db.backup(5)
        db.restore(10, 5)
        assert db.scan_at("a", 10) == ["g(2)"]

    def test_restore_picks_latest_backup_at_or_before(self, db):
        db.set_at("k", "v", "one", 1)
        db.backup(2)
        db.set_at("k", "v", "two", 3)
        db.backup(4)
        db.set_at("k", "v", "three", 5)
        db.restore(6, 3)                          # latest backup <= 3 is at 2
        assert db.get_at("k", "v", 6) == "one"
        db.restore(7, 4)                          # exactly at 4 counts
        assert db.get_at("k", "v", 7) == "two"

    def test_restore_with_no_backup_does_nothing(self, db):
        db.set_at("k", "v", "keep", 5)
        db.backup(10)
        assert db.restore(12, 9) is None          # no backup at or before 9
        assert db.get_at("k", "v", 12) == "keep"

    def test_restore_replaces_whole_database(self, db):
        db.set_at("a", "f", "1", 1)
        db.backup(2)
        db.set_at("z", "f", "new", 3)
        db.restore(4, 2)
        assert db.get_at("z", "f", 4) is None
        assert db.scan_at("z", 4) == []

    def test_non_ttl_fields_stay_permanent_after_restore(self, db):
        db.set_at("a", "f", "1", 1)
        db.backup(2)
        db.restore(3, 2)
        assert db.get_at("a", "f", 10**9) == "1"

    # --- TTL records across backup and restore ---------------------------------

    def test_ttl_remaining_is_rebased_to_restore_time(self, db):
        db.set_at_with_ttl("a", "f", "1", 10, 20)   # expires at 30
        db.backup(25)                                # 30 - 25 = 5 left
        db.restore(100, 25)                          # new expiry 100 + 5 = 105
        assert db.get_at("a", "f", 104) == "1"
        assert db.get_at("a", "f", 105) is None

    def test_field_expiring_exactly_at_backup_time_is_excluded(self, db):
        db.set_at_with_ttl("a", "f", "1", 10, 5)    # expires at 15
        assert db.backup(15) == 0                   # dead at 15, so nothing to save
        db.restore(20, 15)
        assert db.get_at("a", "f", 20) is None

    def test_field_with_one_tick_left_survives_backup(self, db):
        db.set_at_with_ttl("a", "f", "1", 10, 5)    # expires at 15
        assert db.backup(14) == 1                   # 1 left
        db.restore(50, 14)
        assert db.get_at("a", "f", 50) == "1"       # alive at 50 only
        assert db.get_at("a", "f", 51) is None

    def test_each_field_keeps_its_own_remaining_ttl(self, db):
        db.set_at_with_ttl("u", "short", "s", 0, 10)   # expires at 10
        db.set_at_with_ttl("u", "long", "l", 0, 100)   # expires at 100
        db.set_at("u", "perm", "p", 0)
        db.backup(5)                                    # short: 5 left, long: 95 left
        db.restore(1000, 5)
        assert db.scan_at("u", 1004) == ["long(l)", "perm(p)", "short(s)"]
        assert db.scan_at("u", 1005) == ["long(l)", "perm(p)"]      # short expired at 1005
        assert db.scan_at("u", 1095) == ["perm(p)"]                 # long expired at 1095

    def test_backup_count_with_mixed_ttl_records(self, db):
        db.set_at_with_ttl("a", "f", "1", 0, 5)     # dead by 10
        db.set_at_with_ttl("b", "f", "1", 0, 50)    # alive at 10
        db.set_at_with_ttl("c", "x", "1", 0, 5)     # dead by 10
        db.set_at("c", "y", "1", 0)                 # but c still has a permanent field
        assert db.backup(10) == 2                   # b and c

    def test_field_that_expired_after_backup_comes_back_on_restore(self, db):
        db.set_at_with_ttl("a", "f", "1", 10, 10)   # expires at 20
        db.backup(12)                                # 8 left
        assert db.get_at("a", "f", 25) is None       # expired in the live db
        db.restore(30, 12)                           # restored with 8 left -> expires 38
        assert db.get_at("a", "f", 37) == "1"
        assert db.get_at("a", "f", 38) is None

    def test_restore_chooses_older_backup_with_its_own_remaining_ttl(self, db):
        db.set_at_with_ttl("a", "f", "v", 0, 100)   # expires at 100
        db.backup(10)                                # 90 left
        db.backup(60)                                # 40 left
        db.restore(200, 59)                          # latest backup <= 59 is at 10
        assert db.get_at("a", "f", 289) == "v"       # 200 + 90 = 290
        assert db.get_at("a", "f", 290) is None

    def test_backup_after_restore_uses_rebased_expiry(self, db):
        db.set_at_with_ttl("a", "f", "v", 0, 20)    # expires at 20
        db.backup(10)                                # 10 left
        db.restore(100, 10)                          # expires at 110
        db.backup(105)                               # 5 left
        db.restore(500, 105)                         # expires at 505
        assert db.get_at("a", "f", 504) == "v"
        assert db.get_at("a", "f", 505) is None

    def test_writes_after_restore_work_normally(self, db):
        db.set_at_with_ttl("a", "f", "old", 0, 20)
        db.backup(5)
        db.restore(50, 5)                            # a.f expires at 65
        db.set_at_with_ttl("a", "f", "new", 51, 3)   # overwrite: expires at 54
        assert db.get_at("a", "f", 53) == "new"
        assert db.get_at("a", "f", 54) is None
        db.set_at("a", "g", "perm", 55)
        assert db.scan_at("a", 1000) == ["g(perm)"]

    def test_restore_does_not_mutate_the_saved_backup(self, db):
        db.set_at_with_ttl("a", "f", "v", 0, 100)   # expires at 100
        db.backup(10)                                # 90 left
        db.restore(20, 10)
        db.delete_at("a", "f", 21)                   # change the live db after restoring
        db.restore(30, 10)                           # same backup again
        assert db.get_at("a", "f", 119) == "v"       # 30 + 90 = 120
        assert db.get_at("a", "f", 120) is None

    def test_backup_is_a_snapshot_not_a_live_view(self, db):
        db.set_at("a", "f", "before", 1)
        db.backup(2)
        db.set_at("a", "f", "after", 3)           # must not leak into the saved backup
        db.restore(4, 2)
        assert db.get_at("a", "f", 4) == "before"


# ---------------------------------------------------------------------------
# Regression tests for the strict-interviewer review
# ---------------------------------------------------------------------------
class TestReviewFixes:
    def test_backup_counts_records_not_fields(self, db):
        db.set_at("a", "f", "1", 1)
        db.set_at("a", "g", "2", 1)
        db.set_at("b", "f", "3", 1)
        assert db.backup(2) == 2

    def test_level1_set_then_level3_calls(self, db):
        db.set("k", "f", "v")
        assert db.get_at("k", "f", 5) == "v"
        assert db.scan_at("k", 5) == ["f(v)"]
        assert db.backup(6) == 1

    def test_level3_set_then_level1_calls(self, db):
        db.set_at("k", "f", "v", 1)
        assert db.get("k", "f") == "v"
        assert db.scan("k") == ["f(v)"]

    def test_ttl_zero_is_never_alive(self, db):
        db.set_at_with_ttl("k", "f", "v", 10, 0)
        assert db.get_at("k", "f", 10) is None
        assert db.backup(10) == 0

    def test_set_at_stores_empty_string_and_clears_ttl(self, db):
        db.set_at_with_ttl("k", "f", "v", 1, 5)
        db.set_at("k", "f", "", 2)
        assert db.get_at("k", "f", 100) == ""

    def test_delete_at_live_empty_string(self, db):
        db.set_at("k", "f", "", 1)
        assert db.delete_at("k", "f", 2) is True
        assert db.get_at("k", "f", 3) is None

    def test_delete_at_removes_empty_record(self, db):
        db.set_at("k", "f", "v", 1)
        db.delete_at("k", "f", 2)
        assert db.backup(3) == 0
        assert db.scan_at("k", 3) == []

    def test_expired_fields_are_cleaned_up(self, db):
        db.set_at_with_ttl("k", "f", "v", 1, 2)   # expires at 3
        db.scan_at("k", 5)                         # touching the record purges it
        assert db.scan("k") == []                  # gone even for the time-agnostic view
