"""Magnetometry-specific processing (destaggering, despiking, destriping)."""

import numpy as np
from scipy import ndimage, signal


def destagger(data: np.ndarray, shift: int = 1) -> np.ndarray:
    """Correct line misalignment (staggering) in magnetometry grids.

    Alternating survey lines may be offset by one sample due to
    instrument timing. This corrects by shifting every other line.

    Args:
        data: 2D array (rows, cols)
        shift: Number of samples to shift

    Returns:
        Destaggered data
    """
    data = np.asarray(data, dtype=np.float64)
    result = data.copy()
    for i in range(1, data.shape[0], 2):
        result[i] = np.roll(data[i], shift)
    return result


def despike(data: np.ndarray, threshold: float = 3.0, window: int = 3) -> np.ndarray:
    """Remove single-point noise spikes.

    Replaces pixels that deviate more than `threshold` standard
    deviations from the local median with the local median.

    Args:
        data: 2D array
        threshold: Z-score threshold for spike detection
        window: Median filter window size

    Returns:
        Despiked data
    """
    data = np.asarray(data, dtype=np.float64)
    local_med = ndimage.median_filter(data, size=window)
    residual = data - local_med
    std = np.std(residual)
    if std < 1e-12:
        return data
    mask = np.abs(residual) > threshold * std
    result = data.copy()
    result[mask] = local_med[mask]
    return result


def destripe(data: np.ndarray, method: str = "median") -> np.ndarray:
    """Remove scan-line artifacts (striping) from magnetometry data.

    Args:
        data: 2D array (rows, cols)
        method: "median" (subtract row median) or "fft" (frequency notch)

    Returns:
        Destriped data
    """
    data = np.asarray(data, dtype=np.float64)

    if method == "median":
        row_medians = np.median(data, axis=1)
        return data - row_medians[:, np.newaxis]

    elif method == "fft":
        # Notch filter in frequency domain along rows
        spec = fft.fft(data, axis=0)
        n_rows = data.shape[0]
        # Zero out DC and low frequencies (striping is typically row-frequency)
        spec[0] = 0
        spec[1] *= 0.5
        spec[-1] *= 0.5
        return np.real(fft.ifft(spec, axis=0))

    raise ValueError(f"Unknown method: {method}")


def interpolate_grid(
    x: np.ndarray,
    y: np.ndarray,
    values: np.ndarray,
    grid_shape: tuple[int, int],
    method: str = "cubic",
) -> np.ndarray:
    """Interpolate irregularly spaced magnetometry readings to a regular grid.

    Args:
        x, y: 1D arrays of coordinates
        values: 1D array of magnetic gradient values
        grid_shape: (n_rows, n_cols) of output grid
        method: "linear", "cubic", or "nearest"

    Returns:
        2D interpolated grid
    """
    from scipy import interpolate as sp_interp

    grid_x = np.linspace(x.min(), x.max(), grid_shape[1])
    grid_y = np.linspace(y.min(), y.max(), grid_shape[0])

    return sp_interp.griddata(
        (x, y),
        values,
        (grid_x[np.newaxis, :], grid_y[:, np.newaxis]),
        method=method,
        fill_value=0.0,
    )