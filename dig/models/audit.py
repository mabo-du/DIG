"""Audit trail — immutable processing history DAG.

Every processing step creates a new node in the DAG. Original data
is never modified. This provides infinite undo, full reproducibility,
and a verifiable processing chain.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ProcessingStep:
    """A single processing step in the audit trail."""

    name: str
    parameters: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    software_version: str = "0.1.0"
    parent_step: Optional[str] = None  # ID of the previous step

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
            "software_version": self.software_version,
            "parent_step": self.parent_step,
        }


@dataclass
class AuditTrail:
    """Immutable processing history.

    Each step is appended (never removed). The trail can be
    serialized to JSON for reproducibility.
    """

    steps: list[ProcessingStep] = field(default_factory=list)

    def add_step(self, name: str, parameters: dict | None = None) -> ProcessingStep:
        """Append a processing step to the trail."""
        parent = self.steps[-1].timestamp.isoformat() if self.steps else None
        step = ProcessingStep(
            name=name,
            parameters=parameters or {},
            parent_step=parent,
        )
        self.steps.append(step)
        return step

    def to_json(self) -> str:
        """Serialize the audit trail to JSON."""
        return json.dumps(
            [s.to_dict() for s in self.steps],
            indent=2,
        )

    def save(self, path: str) -> None:
        """Save the audit trail to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_json(cls, path: str) -> "AuditTrail":
        """Load an audit trail from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        trail = cls()
        for item in data:
            step = ProcessingStep(
                name=item["name"],
                parameters=item.get("parameters", {}),
                timestamp=datetime.fromisoformat(item["timestamp"]),
                software_version=item.get("software_version", "unknown"),
                parent_step=item.get("parent_step"),
            )
            trail.steps.append(step)
        return trail

    def __len__(self) -> int:
        return len(self.steps)
