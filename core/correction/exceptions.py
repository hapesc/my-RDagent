"""Exception hierarchy for agent loop error routing.

Borrowed from RD-Agent's design principle: exception types drive control flow.
The loop engine catches SkipIterationError subclasses to continue the loop
instead of terminating. Other exceptions propagate and stop the run.

Hierarchy:
    SkipIterationError          (base — "current iteration failed, continue loop")
    ├── CoderError              (code generation / validation failed)
    └── RunnerError             (execution failed)
"""

from __future__ import annotations


class SkipIterationError(Exception):
    """Current iteration failed but the loop should continue to the next.

    The loop engine catches this and archives the failure, then proceeds.
    This is NOT a RuntimeError — it must not be caught by generic
    ``except RuntimeError`` handlers.
    """


class CoderError(SkipIterationError):
    """Code generation or static validation failed.

    Attributes:
        caused_by_timeout: True if the failure was due to an LLM timeout.
    """

    def __init__(self, message: str, *, caused_by_timeout: bool = False) -> None:
        super().__init__(message)
        self.caused_by_timeout = caused_by_timeout


class RunnerError(SkipIterationError):
    """Experiment execution failed (non-zero exit, timeout, missing artifacts)."""

    pass
