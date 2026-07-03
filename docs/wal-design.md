Markdown
# Write-Ahead Log (WAL) Architecture Protocol

The database guarantees ACID atomic state durability by adhering to a strict Write-Ahead logging mechanism.

## Durability Flow Diagram
[Mutation Command] ──> (1. Sequential Flush to wal.log) ──> (2. Virtual Memory Map Copy)


## Recovery Subsystem Implementation
During engine startup sequence initialization:
1. The memory map offset crawler indexes valid database page blocks.
2. If the `wal.log` file contains residual un-cleared bytes, a system crash state is assumed.
3. A low-level file stream loader loops through the transaction log records sequentially, copying them directly to the appropriate address slices inside the active virtual memory mapped pages, ensuring transactional permanence.