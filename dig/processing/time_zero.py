"""Time-zero correction algorithms.

Time-zero represents the moment the transmitter fires and the
electromagnetic wave enters the ground. Thermal drift and variable
air-wave travel time mean time-zero rarely aligns with the first
sample.
"""

import numpy as np
from scipy import signal


def find_time_zero_mer(trace: np.ndarray) -> int:
    """Find time-zero using Modified Energy Ratio (MER).

    The MER algorithm is robust against hardware trigger delay jitter.
    It identifies the inflection point of the true signal arrival
    regardless of absolute amplitude.

    Reference: Coppens (1985) — MER = (A²(t) * A'(t)) / A_base
    """
    trace = np.asarray(trace, dtype=np.float64)
    energy = trace ** 2
    # First derivative approximation
    derivative = np.diff(energy, prepend=energy[0])
    # MER: energy * derivative, smoothed
    mer = energy * np.abs(derivative)
    # Smooth with a short window
    mer_smooth = signal.convolve(mer, np.ones(5) / 5, mode="same")
    return int(np.argmax(mer_smooth))


def find_time_zero_threshold(trace: np.ndarray, threshold: float = 3.0) -> int:
    """Find time-zero using simple amplitude threshold.

    Returns the first sample where amplitude exceeds `threshold`
    times the RMS of the first 10 samples.
    """
    trace = np.asarray(trace, dtype=np.float64)
    noise_floor = np.std(trace[:10])
    if noise_floor < 1e-12:
        return 0
    crossings = np.where(np.abs(trace) > threshold * noise_floor)[0]
    return int(crossings[0]) if len(crossings) > 0 else 0


def correct_time_zero(
    data: np.ndarray, time_zero_samples: int | np.ndarray
) -> np.ndarray:
    """Shift traces to align time-zero.

    Args:
        data: 2D array (traces, samples)
        time_zero_samples: int (constant shift) or 1D array (per-trace shift)

    Returns:
        Shifted array with zero-padding at top.
    """
    data = np.asarray(data)
    if np.isscalar(time_zero_samples):
        time_zero_samples = np.full(data.shape[0], int(time_zero_samples))

    result = np.zeros_like(data)
    for i, shift in enumerate(time_zero_samples):
        shift = int(shift)
        if shift > 0 and shift < data.shape[1]:
            result[i, :-shift] = data[i, shift:]
        elif shift < 0:
            result[i, -shift:] = data[i, :shift]
        else:
            result[i] = data[i]
    return result