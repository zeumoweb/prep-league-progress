What can be lost on leader failover with asynchronous replication, and how would you limit it?

Data could easily be lost on leader failover in async replication, more specifically all data that was acknowledged by the old leader that never reached the new leader. This is because in this type of replication, the leader is responsible for writing to all the followers and the leader does not take the responsibility to verify that all the replicas have received and wrote the data before acknowledging the write as complete to the client.  The client was told success but the write never persisted which breaks durability.

This can be limited through:
- Promoting the most upto date follower: we can look at the log of each follower and promote the follower with the highest log number, reducing the risk/lost to only what the most upto date follower didn't have.
- Using a semi-synchronous replication where one follower is made synchronous and has to confirm all the writes, in this way this follower will be next in line to become the leader after failover.
- We can also put a cap to the replication lag, this way we can monitor how far behind the other followers are from the leader in seconds or bytes and halt receiving new write requests until it meets the threshhold

How does a new follower catch up (snapshot plus log position)?
We can take a consistent snapshot of the leader that has a log number associated with it and copy this snapshot into the new node. The follower then asks the leader for every change after that position and backfills it until the follower has caught up.

When would you choose leaderless replication over a single leader?
There is no failover in leaderless election, which means that writes are mainly avaibable almost all the times even during node failures or when when the nodes are slow as long as we can write to W of N nodes. it also tolerates multiple data centers and slow nodes. The data can leave with eventual consistency and write conflicts are handled.

What does R + W > N not guarantee? Give one concrete scenario (for example sloppy quorums or concurrent writes).

▎ N=3, W=2, R=2 (4 > 3). The home nodes are A, B and C. A partition cuts the client off from A and B, so a sloppy quorum writes the new value to C and to a stand-in node D (hinted handoff). Before D hands the write back, another client reads from A and B and gets the old value from both. The quorum rule holds, but the read is stale.

Other valid cases from the chapter:
- Concurrent writes with last-writer-wins: clock skew can silently drop one of them.
- A read that overlaps a write: it may return either the old value or the new one.
- A write that reached fewer than W nodes: it's reported as failed but not rolled back, so later reads may still see it.
- A node holding the new value fails and is restored from a stale replica: the number of copies of the new value drops below W.

End with 3 sentences you could say in a design interview about failover.

- "With async replication, failover can lose writes the client was told succeeded, so I'd use semi-sync to keep at least one follower in step and promote the most up-to-date replica."
- "I'd guard against split brain with fencing tokens or epoch numbers, so a returning old leader can't accept writes."
- "If losing even one acknowledged write is unacceptable, like in a ledger, I'd use a consensus protocol such as Raft and accept higher write latency."

