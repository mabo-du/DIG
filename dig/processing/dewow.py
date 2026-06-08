"""De-wow filter — removes low-frequency inductive coupling drift.

The "wow" is caused by early-time inductive coupling of transmitter
and receiver antennas, introducing a massive low-frequency DC bias.
"""

import numpy as np
from scipy import signal as sp_signal


def dewow_fft(data: np.ndarray, sample_rate: float, cutoff_hz: float = 0.5) -> np.ndarray:
    """Remove low-frequency drift via FFT high-pass filter.

    Frequency-domain filtering eliminates the edge effects inherent
    in time-domain median subtraction.

    Args:
        data: 2D array (traces, samples)
        sample_rate: Sampling rate in Hz
        cutoff_hz: High-pass cutoff frequency

    Returns:
        De-wowed data (same shape)
    """
    data = np.asarray(data, dtype=np.float64)
    nyquist = sample_rate / 2.0
    sos = sp_signal.butter(4, cutoff_hz / nyquist, btype="high", output="sos")
    return sp_signal.sosfiltfilt(sos, data, axis=1)


def dewow_median(data: np.ndarray, window_size: int = 50) -> np.ndarray:
    """Remove low-frequency drift via running median subtraction.

    Time-domain fallback when FFT is unavailable.

    Args:
        data: 2D array (traces, samples)
        window_size: Running median window in samples

    Returns:
        De-wowed data (same shape)
    """
    data = np.asarray(data, dtype=np.float64)
    result = np.zeros_like(data)
    for i in range(data.shape[0]):
        trend = sp_signal.medfilt(data[i], kernel_size=window_size)
        result[i] = data[i] - trend
    return result
