"""Immutable DAG processing pipeline with full audit trail.

Every processing step creates a new node in a Directed Acyclic Graph.
Original data is never modified — each node references its parent
and stores the function name, parameters, and timestamp.

This is the core architectural difference between DIG and tools like
RGPR/GPRPy which use mutable in-place data models.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

# ── DAG Node ──────────────────────────────────────────────────────────

# Software version for audit trail
SOFTWARE_VERSION = "0.1.0"


@dataclass
class ProcessingNode:
    """A single node in the processing DAG.

    Each node represents one processing step applied to its parent's data.
    The root node (step 0) holds the original unprocessed data.
    """

    step_id: int
    name: str
    parameters: dict[str, Any]
    timestamp: float
    parent_id: int | None
    data: np.ndarray | None = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialize node metadata (excluding data array) for audit export."""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "parameters": dict(self.parameters),
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "software_version": SOFTWARE_VERSION,
        }


# ── Processing Pipeline ───────────────────────────────────────────────


class ProcessingPipeline:
    """Immutable DAG processing pipeline.

    Usage:
        pipe = ProcessingPipeline(raw_data)
        # Chain operations — each returns a new pipeline instance
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)
        pipe = pipe.process(remove_background_global)
        pipe = pipe.process(bandpass_butterworth, low_cut=100e6, high_cut=500e6)

        # Branch from any previous step (non-linear undo)
        branch = pipe.branch(step_id=1)
        branch = branch.process(different_filter, ...)

        # Export audit trail
        history = pipe.export_history()
    """

    def __init__(
        self,
        data: np.ndarray,
        nodes: list[ProcessingNode] | None = None,
        survey_metadata: dict[str, Any] | None = None,
    ):
        self._survey_metadata = survey_metadata or {}

        if nodes is None:
            # Root node — original unprocessed data
            root = ProcessingNode(
                step_id=0,
                name="original",
                parameters={},
                timestamp=time.time(),
                parent_id=None,
                data=np.asarray(data, dtype=np.float64).copy(),
            )
            self._nodes: list[ProcessingNode] = [root]
        else:
            self._nodes = list(nodes)

    @property
    def data(self) -> np.ndarray:
        """Current (latest) data array."""
        return self._nodes[-1].data

    @property
    def current_step(self) -> ProcessingNode:
        """The most recent processing node."""
        return self._nodes[-1]

    @property
    def original_data(self) -> np.ndarray:
        """The original unprocessed data (root node)."""
        return self._nodes[0].data

    @property
    def num_steps(self) -> int:
        return len(self._nodes)

    @property
    def steps(self) -> list[ProcessingNode]:
        """All processing steps in order."""
        return list(self._nodes)

    def process(
        self,
        func: Callable[..., np.ndarray],
        /,
        **kwargs: Any,
    ) -> ProcessingPipeline:
        """Apply a processing function and return a new pipeline instance.

        The function receives the current data as its first argument.
        Additional keyword arguments are passed through and recorded
        in the audit trail.

        Args:
            func: Processing function (data, **kwargs) -> np.ndarray
            **kwargs: Additional arguments passed to the function

        Returns:
            New ProcessingPipeline with the step appended
        """
        current_data = self.data
        func_name = self._resolve_func_name(func)

        # Apply the function
        result = func(current_data, **kwargs)
        result = np.asarray(result, dtype=np.float64)

        # Create new node
        new_node = ProcessingNode(
            step_id=len(self._nodes),
            name=func_name,
            parameters=kwargs,
            timestamp=time.time(),
            parent_id=self.current_step.step_id,
            data=result,
        )

        return ProcessingPipeline(
            data=None,  # not used when nodes provided
            nodes=self._nodes + [new_node],
            survey_metadata=self._survey_metadata,
        )

    def branch(self, step_id: int) -> ProcessingPipeline:
        """Create a branch from a previous step (non-linear undo).

        Args:
            step_id: The step ID to branch from

        Returns:
            New pipeline starting from that step's data
        """
        if step_id < 0 or step_id >= len(self._nodes):
            raise ValueError(
                f"Step {step_id} not found. Pipeline has {len(self._nodes)} steps."
            )

        source = self._nodes[step_id]
        return ProcessingPipeline(
            data=source.data.copy(),
            survey_metadata=self._survey_metadata,
        )

    def export_history(self, include_data: bool = False) -> list[dict[str, Any]]:
        """Export the processing history as a list of serializable dicts.

        Args:
            include_data: If True, include array shapes in output

        Returns:
            List of step dicts suitable for JSON serialization
        """
        history = []
        for node in self._nodes:
            entry = node.to_dict()
            if include_data and node.data is not None:
                entry["data_shape"] = list(node.data.shape)
                entry["data_dtype"] = str(node.data.dtype)
            history.append(entry)
        return history

    def export_history_json(self, indent: int = 2) -> str:
        """Export processing history as a JSON string."""
        return json.dumps(self.export_history(include_data=True), indent=indent)

    def get_step(self, step_id: int) -> ProcessingNode:
        """Get a specific processing step by ID."""
        if step_id < 0 or step_id >= len(self._nodes):
            raise ValueError(
                f"Step {step_id} not found. Pipeline has {len(self._nodes)} steps."
            )
        return self._nodes[step_id]

    def _resolve_func_name(self, func: Callable) -> str:
        """Get a human-readable name for a function."""
        name = getattr(func, "__name__", None)
        if name:
            return name
        module = getattr(func, "__module__", "")
        return f"{module}.{type(func).__name__}"

    def __repr__(self) -> str:
        return (
            f"ProcessingPipeline(steps={self.num_steps}, "
            f"shape={self.data.shape}, "
            f"current={self.current_step.name})"
        )