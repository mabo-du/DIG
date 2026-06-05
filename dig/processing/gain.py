"""Gain functions — compensate for signal attenuation.

GPR signals attenuate exponentially due to geometric spreading and
dielectric attenuation. Gain amplifies late-time arrivals while
preserving relative amplitude dynamics where possible.
"""

import numpy as np


def sec_gain(data: np.ndarray, sample_rate: float, alpha: float = 0.5) -> np.ndarray:
    """Spreading and Exponential Compensation (SEC) gain.

    Models physical attenuation: A(t) = A₀ · t · exp(α·t)

    SEC preserves relative amplitude ratios — superior to AGC for
    stratigraphic analysis.

    Args:
        data: 2D array (traces, samples)
        sample_rate: Sampling rate in Hz
        alpha: Attenuation coefficient

    Returns:
        Gain-corrected data
    """
    data = np.asarray(data, dtype=np.float64)
    n_samples = data.shape[1]
    dt = 1.0 / sample_rate
    t = np.arange(n_samples, dtype=np.float64) * dt

    # SEC gain function
    gain = t * np.exp(alpha * t)
    gain[0] = 1.0  # avoid division by zero at t=0
    gain = np.where(np.isfinite(gain) & (gain > 0), gain, 1.0)

    return data / gain[np.newaxis, :]


def agc(data: np.ndarray, window_samples: int = 50) -> np.ndarray:
    """Automatic Gain Control (AGC).

    Normalizes each sample by the RMS amplitude within a sliding window.

    Warning: Destroys relative amplitude information. Use SEC for
    stratigraphic analysis.

    Args:
        data: 2D array (traces, samples)
        window_samples: RMS window size in samples

    Returns:
        AGC-normalized data
    """
    data = np.asarray(data, dtype=np.float64)
    from scipy.ndimage import uniform_filter1d

    # RMS in sliding window
    squared = data ** 2
    mean_sq = uniform_filter1d(squared, size=window_samples, axis=1, mode="reflect")
    rms = np.sqrt(np.maximum(mean_sq, 1e-12))

    return data / rms


def linear_gain(data: np.ndarray, gain_db_per_us: float = 10.0, sample_rate: float = 1e9) -> np.ndarray:
    """Apply linear time-power gain.

    Args:
        data: 2D array (traces, samples)
        gain_db_per_us: Gain in dB per microsecond
        sample_rate: Sampling rate in Hz

    Returns:
        Gain-corrected data
    """
    data = np.asarray(data, dtype=np.float64)
    n_samples = data.shape[1]
    dt = 1.0 / sample_rate
    t = np.arange(n_samples, dtype=np.float64) * dt * 1e6  # convert to µs

    gain_linear = 10.0 ** (gain_db_per_us * t / 20.0)
    return data * gain_linear[np.newaxis, :]