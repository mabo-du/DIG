"""Background removal — suppresses invariant horizontal banding.

Removes coherent system noise (antenna ringing, cross-talk, persistent
ground-surface reflections) that does not vary across the profile.
"""

import numpy as np


def remove_background_global(data: np.ndarray) -> np.ndarray:
    """Subtract the ensemble average trace from every trace.

    Effective for short profiles over homogenous terrain.

    Args:
        data: 2D array (traces, samples)

    Returns:
        Background-removed data
    """
    data = np.asarray(data, dtype=np.float64)
    mean_trace = np.mean(data, axis=0)
    return data - mean_trace[np.newaxis, :]


def remove_background_local(
    data: np.ndarray, window_traces: int = 20
) -> np.ndarray:
    """Subtract a localized running average trace.

    Adapts to non-stationary clutter (changing soil conditions,
    topography, moisture) by using a rolling window.

    Args:
        data: 2D array (traces, samples)
        window_traces: Number of traces in the rolling window

    Returns:
        Background-removed data
    """
    data = np.asarray(data, dtype=np.float64)
    from scipy.ndimage import uniform_filter1d

    mean_trace = uniform_filter1d(data, size=window_traces, axis=0, mode="reflect")
    return data - mean_trace