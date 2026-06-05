"""2D GPR profile model — a single radargram line."""

from dataclasses import dataclass
import numpy as np


@dataclass
class Profile:
    """A single 2D GPR profile (radargram).

    Represents one survey line with trace data and spatial metadata.
    """

    name: str
    data: np.ndarray  # (traces, samples)
    trace_spacing_m: float = 0.05
    sample_interval_ns: float = 0.1
    start_position_m: float = 0.0
    elevation_m: float = 0.0

    @property
    def num_traces(self) -> int:
        return self.data.shape[0]

    @property
    def num_samples(self) -> int:
        return self.data.shape[1]

    @property
    def time_window_ns(self) -> float:
        return self.num_samples * self.sample_interval_ns

    @property
    def length_m(self) -> float:
        return self.num_traces * self.trace_spacing_m