# ADR 001: SQLite for MVP Persistence

## Status
Accepted

## Context
The Agentic R&D Platform (my-RDagent) requires a persistence layer to store run session metadata, event streams, and checkpoint references. The MVP (Minimum Viable Product) needs a solution that supports rapid development, easy setup for individual users, and sufficient performance for single-machine execution.

We considered the following options:
1.  **PostgreSQL**: A robust relational database, but requires separate installation and management.
2.  **File-based (JSON/YAML)**: Simple to implement, but lacks query capabilities and ACID guarantees.
3.  **SQLite**: Zero-configuration, single-file database that provides full SQL support and ACID compliance.

## Decision
We decided to use **SQLite** as the primary metadata storage for the MVP.

The implementation is abstracted via the `RunMetadataStore` and `EventMetadataStore` protocols in `core/storage/interfaces.py`. The concrete implementation `SQLiteMetadataStore` (located in `core/storage/sqlite_store.py`) handles the interaction with the SQLite database. The database path is configurable via the `AGENTRD_SQLITE_PATH` environment variable or config setting.

## Consequences
- **Zero-config**: Users can start the platform without setting up a database server.
- **Portability**: The entire state can be moved by copying a single file.
- **Single-machine scaling**: SQLite is more than sufficient for the metadata volume of an individual R&D agent.
- **Limited concurrency**: SQLite's write-locking may become a bottleneck if multiple agents or UIs attempt simultaneous writes, though this is mitigated by WAL (Write-Ahead Logging) mode.
- **Migration path**: Since the storage is abstracted behind Python Protocols, we can implement a PostgreSQL provider in the future if we need to scale to a multi-user, multi-node architecture.
