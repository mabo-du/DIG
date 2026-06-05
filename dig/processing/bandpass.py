"""Bandpass filtering — removes out-of-band noise.

GPR antennas are ultra-wideband. A nominal 500 MHz antenna records
roughly 250-750 MHz. Bandpass filtering eliminates high-frequency
thermal noise and low-frequency soil conductivity losses.
"""

import numpy as np
from scipy import signal as sp_signal


def bandpass_butterworth(
    data: np.ndarray,
    sample_rate: float,
    low_cut: float,
    high_cut: float,
    order: int = 4,
) -> np.ndarray:
    """Apply zero-phase Butterworth bandpass filter.

    Uses sosfiltfilt for zero-phase filtering (no phase distortion).

    Args:
        data: 2D array (traces, samples)
        sample_rate: Sampling rate in Hz
        low_cut: Low-cut frequency in Hz
        high_cut: High-cut frequency in Hz
        order: Filter order

    Returns:
        Filtered data (same shape)
    """
    data = np.asarray(data, dtype=np.float64)
    nyquist = sample_rate / 2.0
    sos = sp_signal.butter(
        order,
        [low_cut / nyquist, high_cut / nyquist],
        btype="band",
        output="sos",
    )
    return sp_signal.sosfiltfilt(sos, data, axis=1)