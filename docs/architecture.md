# System Architecture Specification

This document details the macro-architecture of the storage engine, defining how execution requests flow across volatile and non-volatile boundaries.

## Component Interactions

1. **Concurrency Control:** Every database operation passes through a critical section protected by a strict synchronization primitive (`threading.Lock`), ensuring total isolation across concurrent reader and writer workers.
2. **Write Path:** Mutations write immediately to the append-only Write-Ahead Log (WAL) to achieve immediate physical durability before altering the virtual address space.
3. **Memory Allocation:** The database manipulates records through structured virtual memory slices (`mmap`), mapping pages straight to the host operation system's page-cache subsystem.