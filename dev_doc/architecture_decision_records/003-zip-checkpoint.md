# ADR 003: Zip-based Workspace Checkpointing

## Status
Accepted

## Context
The platform needs to save the entire state of the working directory (workspace) at various points in the R&D loop to enable resuming from a failure, replaying actions, or branching the R&D process.

Options for checkpointing included:
1.  **Git**: Powerful and supports branching, but requires git to be initialized in every sandbox and has a more complex management overhead.
2.  **Tar**: A standard UNIX archival format, but less common on some environments.
3.  **Zip**: Simple, cross-platform, and provides a single binary file for each checkpoint.

## Decision
We decided to use the **Zip** format for workspace checkpointing.

The implementation is located in `core/execution/workspace_manager.py`. The `WorkspaceManager` captures the contents of the temporary workspace directory into a `.zip` archive and saves it to a `CheckpointStore`. When a checkpoint is loaded, the zip file is extracted into the workspace directory, restoring its previous state.

## Consequences
- **Simplicity**: Creating and extracting zip files is a straightforward process with standard library support in Python (`zipfile` module).
- **Portability**: Zip files are widely supported across different operating systems and container environments.
- **Standalone Sandboxes**: We can checkpoint the workspace without needing to initialize or manage a git repository inside the sandboxed environment.
- **Non-Incremental Storage**: Each checkpoint is a full copy of the workspace. This can consume significant disk space if the workspace is large or if there are many checkpoints.
- **Suitability**: For the MVP, typical workspace sizes (mostly source code) are small enough that the storage overhead of full zip copies is acceptable. Future iterations might explore deduplication or incremental checkpointing if workspace sizes increase significantly.
