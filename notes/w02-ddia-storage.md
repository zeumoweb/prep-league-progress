# DDIA "Storage and Retrieval": LSM-tree vs B-tree

## 1. Write path and read path

### LSM-tree (log-structured merge-tree)
- **Write path:**
  1. Append the write to a **write-ahead log (WAL)** on disk. This comes first, so an acknowledged write survives a crash.
  2. Insert it into the **memtable**, an in-memory structure sorted **by key** (a balanced tree or skip list). Then acknowledge the write.
  3. When the memtable passes a size threshold (a few MB), flush it to disk as an immutable, sorted file called an **SSTable**, then discard its WAL.

  All disk writes are sequential appends, which is why LSM writes are fast.
- **Background:** segments are never modified. **Compaction** merges SSTables, keeping only the latest value per key and dropping deleted keys (marked with tombstones).
- **Read path:**
  1. Check the memtable.
  2. Then check the SSTables from newest to oldest, stopping at the first match.

  Each SSTable has a sparse in-memory index, so checking one file is a binary search plus one block read, not a scan. The expensive case is a **missing key**: it must be checked in every segment (or level).

### B-tree
- **Structure:** fixed-size **pages** (typically 4-16 KB) arranged as a tree. Keys inside a page mark the boundaries between child pointers.
  - The branching factor is several hundred, so the depth is O(log n): 3-4 levels hold billions of keys.
- **Read path:** start at the root and follow the child pointer whose key range contains the key, page by page, until you reach the **leaf page** that holds the value.
- **Write path:**
  1. Find the leaf page the same way.
  2. **Overwrite the page in place.**
  3. If the page is full, **split** it into two half-full pages and add a new key and pointer to the **parent**. Splits can cascade upward; a root split is how the tree grows taller.
- **Crash safety:** an in-place page write can be interrupted by a crash, so B-trees also keep a **WAL (redo log)**. Every change is logged before the page is modified.

## 2. Write amplification (what gets rewritten, and roughly how many times)
- **LSM:**
  - **What gets rewritten:** each record is written to the WAL, then to an SSTable on flush, then **again on every compaction** as it moves down the levels.
  - **How many times:** with leveled compaction, roughly **10-30x** in total. Size-tiered compaction rewrites less but uses more disk space.
- **B-tree:**
  - **What gets rewritten:** every update writes a WAL entry **plus a whole page**, so changing 100 bytes can rewrite a 4-16 KB page. A split writes extra pages (both halves and the parent).
  - **How much:** for small random writes, the bytes written per byte changed can be very high.
- **Takeaway:** LSM-trees usually have **lower write amplification** and turn random writes into sequential ones. Both depend heavily on workload and configuration.

## 3. Why compaction can cause latency spikes, and one mitigation
- **Reads and writes are not blocked:** old segments keep serving reads until the merged segment replaces them.
- **The spikes come from competing for resources:** compaction uses disk bandwidth and CPU at the same time as foreground requests, so tail latency (p99) jumps.
- **If writes outpace compaction:**
  - unmerged segments pile up, and reads check more files
  - engines such as RocksDB start to **throttle or stall writes**
- **Contrast:** B-trees have no background merging, so their latency is more predictable.
- **Mitigation:** **rate-limit compaction I/O** (for example, RocksDB's rate limiter) and leave enough disk headroom for compaction to keep up. Watch the backlog with a "pending compaction bytes" metric.

## 4. What Bloom filters save on the LSM read path
- **Each SSTable has its own Bloom filter.** For a given key it answers either "**definitely not here**" or "**maybe here**".
- **No false negatives.** The false-positive rate is small: about 1% at about 10 bits per key.
- **What it saves:** a disk read for every segment that cannot contain the key. A missing-key lookup drops from one disk read per segment to a few in-memory checks.
- **Limitation:** Bloom filters do not help range scans.

## 5. Engine choice for a write-heavy KV store
**LSM-tree.**
- **Why:**
  - Writes are sequential appends, with no in-place page updates or splits.
  - Write amplification is usually lower.
  - It compresses better and fragments less.
  - Immutable segments make concurrency and crash recovery simpler.
- **Trade-offs I would accept and manage:**
  - higher read amplification, reduced with Bloom filters and compaction
  - tail-latency risk from compaction, reduced with rate limiting and headroom
- **When I would pick a B-tree instead:**
  - read-heavy workloads
  - range scans that need predictable latency
  - transactions that need locks on key ranges
