"""Colormap definitions for geophysical visualization.

Provides gray, seismic, and viridis colormaps as (N, 4) float32 arrays
suitable for use with PyQtGraph ImageItem's setLookupTable.
"""

import numpy as np

# ── Colormap Registry ─────────────────────────────────────────────────

COLORMAPS: dict[str, np.ndarray] = {}


def _register(name: str, colors: np.ndarray) -> None:
    """Register a colormap as a (N, 4) uint8 array (RGBA)."""
    COLORMAPS[name] = np.asarray(colors, dtype=np.uint8)


def _build_gray(n: int = 256) -> np.ndarray:
    """Linear grayscale colormap."""
    ramp = np.linspace(0, 255, n, dtype=np.uint8)
    return np.column_stack([ramp, ramp, ramp, np.full(n, 255, dtype=np.uint8)])


def _build_seismic(n: int = 256) -> np.ndarray:
    """Seismic colormap: dark blue → white → dark red.

    Standard for GPR radargram display. Negative amplitudes in blue,
    positive in red, zero in white.
    """
    half = n // 2
    result = np.zeros((n, 4), dtype=np.uint8)

    # Blue half (negative): dark blue → white
    for i in range(half):
        t = i / max(half - 1, 1)
        result[i] = [
            int(255 * t),  # R: 0 → 255
            int(255 * t),  # G: 0 → 255
            max(50, int(255 * (1 - t * 0.8))),  # B: 255 → ~50
            255,
        ]

    # Red half (positive): white → dark red
    for i in range(half, n):
        t = (i - half) / max(n - half - 1, 1)
        result[i] = [
            max(50, int(255 * (1 - t * 0.8))),  # R: 255 → ~50
            int(255 * (1 - t)),  # G: 255 → 0
            int(255 * (1 - t)),  # B: 255 → 0
            255,
        ]

    return result


def _build_viridis(n: int = 256) -> np.ndarray:
    """Approximate matplotlib viridis colormap.

    Viridis is perceptually uniform and colorblind-friendly.
    Key stops: (0.267, 0.004, 0.329) → (0.127, 0.566, 0.550) → (0.993, 0.906, 0.144)
    """
    stops = np.array(
        [
            [0.267, 0.004, 0.329],
            [0.282, 0.141, 0.458],
            [0.254, 0.265, 0.530],
            [0.207, 0.382, 0.549],
            [0.164, 0.494, 0.528],
            [0.127, 0.566, 0.550],
            [0.135, 0.639, 0.549],
            [0.267, 0.718, 0.510],
            [0.472, 0.788, 0.431],
            [0.690, 0.844, 0.323],
            [0.878, 0.881, 0.209],
            [0.993, 0.906, 0.144],
        ]
    )

    result = np.zeros((n, 4), dtype=np.uint8)
    for i in range(3):
        result[:, i] = (
            np.interp(
                np.linspace(0, 1, n),
                np.linspace(0, 1, len(stops)),
                stops[:, i],
            )
            * 255
        )
    result[:, 3] = 255
    return result


# ── Register built-in colormaps ───────────────────────────────────────

_register("gray", _build_gray())
_register("seismic", _build_seismic())
_register("viridis", _build_viridis())


# ── Public API ────────────────────────────────────────────────────────


def apply_colormap(
    data: np.ndarray,
    colormap: str | np.ndarray = "seismic",
    vmin: float | None = None,
    vmax: float | None = None,
) -> np.ndarray:
    """Apply a colormap to 2D data, returning an (M, N, 4) RGBA uint8 array.

    Args:
        data: 2D array of values
        colormap: Name of registered colormap, or a (N, 4) lookup table
        vmin: Minimum value for mapping (default: data min)
        vmax: Maximum value for mapping (default: data max)

    Returns:
        RGBA image array of shape (M, N, 4)
    """
    if isinstance(colormap, str):
        if colormap not in COLORMAPS:
            raise ValueError(f"Unknown colormap '{colormap}'. Available: {list(COLORMAPS.keys())}")
        lut = COLORMAPS[colormap]
    else:
        lut = np.asarray(colormap, dtype=np.uint8)

    data = np.asarray(data, dtype=np.float64)
    if vmin is None:
        vmin = data.min()
    if vmax is None:
        vmax = data.max()

    # Normalize to [0, 1]
    if abs(vmax - vmin) < 1e-12:
        normalized = np.zeros_like(data)
    else:
        normalized = (data - vmin) / (vmax - vmin)
    normalized = np.clip(normalized, 0, 1)

    # Map through LUT
    indices = (normalized * (len(lut) - 1)).astype(np.uint16)
    return lut[indices]
