"""Branch-aware trace store for experiment DAG nodes."""

from __future__ import annotations

from contextlib import contextmanager
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from data_models import ExperimentNode, StepState

logger = logging.getLogger(__name__)


@dataclass
class BranchTraceStoreConfig:
    """Configuration for branch trace store."""

    sqlite_path: str = "/tmp/rd_agent.sqlite3"


class BranchTraceStore:
    """Stores experiment DAG nodes and branch heads in SQLite."""

    def __init__(self, config: BranchTraceStoreConfig) -> None:
        self._config = config
        self._db_path = Path(config.sqlite_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._db_path))
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _managed_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            logger.exception(f"Database operation failed in BranchTraceStore._managed_connection(db_path={self._db_path}); rolling back")
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._managed_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_nodes (
                    run_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    parent_node_id TEXT,
                    loop_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    is_head INTEGER NOT NULL,
                    PRIMARY KEY (run_id, node_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_experiment_nodes_run_branch ON experiment_nodes(run_id, branch_id)"
            )

    def record_node(self, node: ExperimentNode) -> None:
        payload = json.dumps(node.to_dict(), sort_keys=True)
        with self._managed_connection() as conn:
            conn.execute(
                "UPDATE experiment_nodes SET is_head = 0 WHERE run_id = ? AND branch_id = ?",
                (node.run_id, node.branch_id),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO experiment_nodes
                (run_id, node_id, branch_id, parent_node_id, loop_index, payload_json, is_head)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    node.run_id,
                    node.node_id,
                    node.branch_id,
                    node.parent_node_id,
                    node.loop_index,
                    payload,
                ),
            )

    def get_node(self, run_id: str, node_id: str) -> Optional[ExperimentNode]:
        with self._managed_connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM experiment_nodes WHERE run_id = ? AND node_id = ?",
                (run_id, node_id),
            ).fetchone()
        if row is None:
            return None
        return ExperimentNode.from_dict(json.loads(row["payload_json"]))

    def create_child_node(
        self,
        run_id: str,
        parent_node_id: str,
        node_id: str,
        loop_index: int,
        fork_branch: bool = False,
        hypothesis: Optional[Dict[str, object]] = None,
    ) -> ExperimentNode:
        parent_node = self.get_node(run_id, parent_node_id)
        if parent_node is None:
            raise KeyError(f"parent node not found: {run_id}/{parent_node_id}")

        branch_id = parent_node.branch_id
        if fork_branch:
            branch_id = f"{parent_node.branch_id}-fork-{uuid.uuid4().hex[:6]}"

        node = ExperimentNode(
            node_id=node_id,
            run_id=run_id,
            branch_id=branch_id,
            parent_node_id=parent_node_id,
            loop_index=loop_index,
            step_state=StepState.RECORDED,
            hypothesis=dict(hypothesis or {}),
            workspace_ref="",
            result_ref="",
            feedback_ref="",
        )
        self.record_node(node)
        return node

    def get_branch_heads(self, run_id: str) -> Dict[str, str]:
        heads: Dict[str, str] = {}
        with self._managed_connection() as conn:
            rows = conn.execute(
                "SELECT branch_id, node_id FROM experiment_nodes WHERE run_id = ? AND is_head = 1",
                (run_id,),
            ).fetchall()
        for row in rows:
            heads[str(row["branch_id"])] = str(row["node_id"])
        return heads

    def query_nodes(self, run_id: str, branch_id: Optional[str] = None) -> List[ExperimentNode]:
        with self._managed_connection() as conn:
            if branch_id is None:
                rows = conn.execute(
                    "SELECT payload_json FROM experiment_nodes WHERE run_id = ? ORDER BY loop_index, node_id",
                    (run_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM experiment_nodes
                    WHERE run_id = ? AND branch_id = ?
                    ORDER BY loop_index, node_id
                    """,
                    (run_id, branch_id),
                ).fetchall()

        return [ExperimentNode.from_dict(json.loads(row["payload_json"])) for row in rows]
