"""Topographic correction — adjusts GPR data for surface elevation changes."""

import numpy as np
from scipy import interpolate


def correct_topography_shift(
    data: np.ndarray,
    elevations: np.ndarray,
    velocity_m_ns: float = 0.1,
    sample_interval_ns: float = 0.1,
) -> np.ndarray:
    """Apply topographic correction via vertical trace shifting.

    Simple approach suitable for gentle slopes (<15°). For steep
    terrain, use topographic Kirchhoff migration instead.

    Args:
        data: 2D array (traces, samples)
        elevations: 1D array of surface elevations per trace (m)
        velocity_m_ns: Electromagnetic wave velocity (m/ns)
        sample_interval_ns: Time between samples (ns)

    Returns:
        Topographically corrected data
    """
    data = np.asarray(data, dtype=np.float64)
    elevations = np.asarray(elevations, dtype=np.float64)

    # Interpolate elevations to match trace count
    if len(elevations) != data.shape[0]:
        x_old = np.linspace(0, 1, len(elevations))
        x_new = np.linspace(0, 1, data.shape[0])
        f = interpolate.interp1d(x_old, elevations, kind="cubic", fill_value="extrapolate")
        elevations = f(x_new)

    # Convert elevation to time shift (two-way travel)
    ref_elevation = np.median(elevations)
    time_shift_ns = 2.0 * (elevations - ref_elevation) / velocity_m_ns
    shift_samples = np.round(time_shift_ns / sample_interval_ns).astype(int)

    # Apply shifts
    result = np.zeros_like(data)
    for i, shift in enumerate(shift_samples):
        if shift > 0:
            result[i, shift:] = data[i, :-shift]
        elif shift < 0:
            result[i, :shift] = data[i, -shift:]
        else:
            result[i] = data[i]

    return result
