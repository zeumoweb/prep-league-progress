import bisect
from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    """One field's value. `expires_at` is None for fields that never expire."""

    value: str
    expires_at: int | None = None

    def is_alive(self, ts: int | None) -> bool:
        """Alive on [set time, expires_at). ts=None means "ignore time" (Level 1-2 calls)."""
        return ts is None or self.expires_at is None or ts < self.expires_at


class InMemoryDB:
    """Records (by key) hold fields (name -> string value), with optional TTLs and backups.

    Every field is stored as a Record, so Level 1-2 calls and timestamped Level 3-4 calls can be
    mixed freely. Timestamps are assumed to only increase between calls, which lets expired fields
    be removed lazily whenever a timestamped call touches their record.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Record]] = {}
        # Each backup maps key -> field -> (value, remaining_ttl or None).
        self._backup_times: list[int] = []
        self._backups: dict[int, dict[str, dict[str, tuple[str, int | None]]]] = {}

    #  Level 1: records and fields (no timestamps)

    def set(self, key: str, field: str, value: str) -> None:
        self._put(key, field, Record(value))

    def get(self, key: str, field: str) -> str | None:
        return self._get(key, field, ts=None)

    def delete(self, key: str, field: str) -> bool:
        return self._delete(key, field, ts=None)

    #  Level 2: scanning

    def scan(self, key: str) -> list[str]:
        return self._scan(key, prefix="", ts=None)

    def scan_by_prefix(self, key: str, prefix: str) -> list[str]:
        return self._scan(key, prefix=prefix, ts=None)

    #  Level 3: timestamps and TTL

    def set_at(self, key: str, field: str, value: str, ts: int) -> None:
        self._purge_expired(key, ts)
        self._put(key, field, Record(value))  # overwriting drops any previous TTL

    def set_at_with_ttl(self, key: str, field: str, value: str, ts: int, ttl: int) -> None:
        self._purge_expired(key, ts)
        self._put(key, field, Record(value, ts + ttl))  # overwriting starts a new TTL

    def get_at(self, key: str, field: str, ts: int) -> str | None:
        self._purge_expired(key, ts)
        return self._get(key, field, ts)

    def delete_at(self, key: str, field: str, ts: int) -> bool:
        self._purge_expired(key, ts)
        return self._delete(key, field, ts)

    def scan_at(self, key: str, ts: int) -> list[str]:
        self._purge_expired(key, ts)
        return self._scan(key, prefix="", ts=ts)

    def scan_by_prefix_at(self, key: str, prefix: str, ts: int) -> list[str]:
        self._purge_expired(key, ts)
        return self._scan(key, prefix=prefix, ts=ts)

    # Level 4: backup and restore

    def backup(self, timestamp: int) -> int:
        """Snapshot everything alive at `timestamp`; return the number of non-empty records."""
        snapshot: dict[str, dict[str, tuple[str, int | None]]] = {}
        for key, fields in self._records.items():
            alive = {
                field: (rec.value, None if rec.expires_at is None else rec.expires_at - timestamp)
                for field, rec in fields.items()
                if rec.is_alive(timestamp)
            }
            if alive:
                snapshot[key] = alive
        if timestamp not in self._backups:
            bisect.insort(self._backup_times, timestamp)
        self._backups[timestamp] = snapshot
        return len(snapshot)

    def restore(self, timestamp: int, timestamp_to_restore: int) -> None:
        """Load the latest backup at or before `timestamp_to_restore`; TTLs restart at `timestamp`."""
        i = bisect.bisect_right(self._backup_times, timestamp_to_restore)
        if i == 0:
            return None  # no backup that early: leave the database unchanged
        snapshot = self._backups[self._backup_times[i - 1]]
        # Build fresh Records so later writes can never change the saved backup.
        self._records = {
            key: {
                field: Record(value, None if remaining is None else timestamp + remaining)
                for field, (value, remaining) in fields.items()
            }
            for key, fields in snapshot.items()
        }
        return None

    # Helper

    def _put(self, key: str, field: str, record: Record) -> None:
        self._records.setdefault(key, {})[field] = record

    def _get(self, key: str, field: str, ts: int | None) -> str | None:
        rec = self._records.get(key, {}).get(field)
        return rec.value if rec is not None and rec.is_alive(ts) else None

    def _delete(self, key: str, field: str, ts: int | None) -> bool:
        fields = self._records.get(key)
        if fields is None or field not in fields or not fields[field].is_alive(ts):
            return False
        del fields[field]
        if not fields:  # a record with no fields left no longer exists
            del self._records[key]
        return True

    def _scan(self, key: str, prefix: str, ts: int | None) -> list[str]:
        fields = self._records.get(key, {})
        matches = [(f, r.value) for f, r in fields.items() if f.startswith(prefix) and r.is_alive(ts)]
        return [f"{f}({v})" for f, v in sorted(matches)]

    def _purge_expired(self, key: str, ts: int) -> None:
        """Drop fields of `key` that are dead at `ts` (safe because timestamps only increase)."""
        fields = self._records.get(key)
        if not fields:
            return
        for field in [f for f, r in fields.items() if not r.is_alive(ts)]:
            del fields[field]
        if not fields:
            del self._records[key]
