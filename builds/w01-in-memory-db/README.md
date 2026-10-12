# Week 1: In-memory database (baseline progressive build)

Prep League task `w01-mon-core-2`: a 90-minute, four-level build done with AI assistants and autocomplete turned off.

- **levels completed: 4/4**
- **Time taken:** 1h 10min
- **Tests:** `test_db.py`, 55 tests (47 from the timed run plus 8 regression tests from the review) covering every example row on the card plus edge cases, especially TTL behaviour across backup and restore. All pass.

```bash
python3 -m pip install pytest
python3 -m pytest -q            # all levels
python3 -m pytest -q -k Level3  # a single level
```

## Levels
1. **Records and fields:** `set`, `get`, `delete`
2. **Scanning:** `scan`, `scan_by_prefix` (sorted `field(value)` output)
3. **Timestamps and TTL:** `set_at`, `set_at_with_ttl` (alive on `[ts, ts+ttl)`), plus `get_at`, `delete_at`, `scan_at`, `scan_by_prefix_at`
4. **Backup and restore:** `backup(ts)` saves live data with remaining TTLs; `restore(ts, ts_to_restore)` loads the latest backup at or before `ts_to_restore` and re-bases TTLs to `ts`

## Strict-interviewer review: top 3 points
1. **`backup` counts fields, not records.** It returns `count += 1` per field, but the spec asks for the number of records with at least one live field. One record with two fields returns 2. Fix: return `len(backup_copy)`.
2. **The Level 1 and Level 3 data models clash.** Plain strings and `Record` objects share one dict, so mixing calls breaks:
   - After `set()`, `scan_at` and `backup` raise `AttributeError`.
   - After `set_at()`, `get` returns a raw `Record`.

   Fix: always store a `Record`, and have `set` delegate to `set_at(..., ts=0)`.
3. **`ttl=0` is treated as "never expires".** `if not record.ttl` is the wrong check. Fix: use `if record.ttl is None`, and use one `is_alive(record, ts)` helper everywhere, including `backup`, so expiry checks can't disagree.

## Other notes from the review
- **Empty strings:** `set_at` ignores `""` (`if not value`), and `delete_at` cannot delete a live `""` because it checks truthiness. Use `is None` checks.
- **Leftover empty records:** `delete_at` leaves `{key: {}}` behind once the last field is removed. Expired fields are never cleaned up.
- **Duplication:** the four scan methods could share one `_scan(key, prefix="", ts=None)`.
- **Faster restore:** keeping backup times sorted and using `bisect_right` would make it O(log B).
- **Rubric self-score (reviewer):**

  | Row | Score |
  |---|---|
  | Understanding | 3 |
  | Approach | 2 |
  | Code | 2 |
  | Testing | 2 |
  | Senior signal | 2 |

- **What went well:** the TTL boundary and the remaining-TTL re-basing on restore are correct, restore never shares state with the saved backup, and all four levels were finished.

## After the review (not part of the timed 1h 10min)
Every point above was then fixed, with a regression test for each (`TestReviewFixes`):
- **One data model:** every field is stored as `Record(value, expires_at)`, so Level 1-2 and Level 3-4 calls mix freely.
- **One expiry check:** a single `Record.is_alive(ts)` (`ttl=0` is never alive) is used everywhere, including `backup`.
- **Correct backup count:** `backup` returns the number of records, not fields.
- **Empty strings:** `""` is stored and deleted like any other value.
- **No leftover records:** empty records are removed, and expired fields are purged lazily when a timestamped call touches their record.
- **Less duplication:** the scan methods share one `_scan(key, prefix, ts)` helper.
- **Faster restore:** it uses a sorted list of backup times with `bisect_right`.
- **Clean-up:** unused imports and fields are gone.
