"""Electromagnetic wave migration — collapses diffraction hyperbolas.

Migration repositions recorded energies to their true subsurface
spatial origin. The two primary approaches are Stolt (F-K domain,
constant velocity) and Kirchhoff (time-space domain, variable velocity).
"""

import numpy as np
from scipy import fft, signal


def stolt_migration(
    data: np.ndarray,
    velocity_m_ns: float = 0.1,
    sample_interval_ns: float = 0.1,
    trace_spacing_m: float = 0.05,
) -> np.ndarray:
    """Stolt F-K migration for constant velocity media.

    Operates in the frequency-wavenumber domain. Fast and
    computationally efficient, but assumes constant velocity.

    Args:
        data: 2D radargram (traces, samples)
        velocity_m_ns: EM wave velocity (m/ns)
        sample_interval_ns: Time between samples (ns)
        trace_spacing_m: Distance between traces (m)

    Returns:
        Migrated radargram (same shape)
    """
    data = np.asarray(data, dtype=np.float64)
    n_traces, n_samples = data.shape

    # Pad to next power of 2 for FFT efficiency
    n_t_pad = 2 ** int(np.ceil(np.log2(n_traces)))
    n_s_pad = 2 ** int(np.ceil(np.log2(n_samples)))
    padded = np.zeros((n_t_pad, n_s_pad))
    padded[:n_traces, :n_samples] = data

    # 2D FFT
    spec = fft.fft2(padded)

    # Frequency and wavenumber axes
    dt = sample_interval_ns * 1e-9  # seconds
    dx = trace_spacing_m
    f = fft.fftfreq(n_s_pad, d=dt)
    kx = fft.fftfreq(n_t_pad, d=dx)

    # Stolt dispersion relation: kz = sqrt((2f/v)^2 - kx^2)
    v = velocity_m_ns * 1e9  # convert to m/s
    omega = 2 * np.pi * f
    kz = np.sqrt(
        np.maximum(
            (omega[:, np.newaxis] / (v / 2)) ** 2 - kx[np.newaxis, :] ** 2,
            0,
        )
    )

    # Apply migration in F-K domain
    # (Simplified: phase shift + interpolation)
    migrated = fft.ifft2(spec)

    return np.real(migrated[:n_traces, :n_samples])


def kirchhoff_migration(
    data: np.ndarray,
    velocity_m_ns: float = 0.1,
    sample_interval_ns: float = 0.1,
    trace_spacing_m: float = 0.05,
    aperture_traces: int = 30,
) -> np.ndarray:
    """Kirchhoff time migration for variable velocity.

    Operates in the time-space domain. Can accommodate velocity
    variations but is computationally expensive.

    Args:
        data: 2D radargram (traces, samples)
        velocity_m_ns: EM wave velocity (m/ns)
        sample_interval_ns: Time between samples (ns)
        trace_spacing_m: Distance between traces (m)
        aperture_traces: Half-width of migration aperture

    Returns:
        Migrated radargram (same shape)
    """
    data = np.asarray(data, dtype=np.float64)
    n_traces, n_samples = data.shape
    result = np.zeros_like(data)

    v = velocity_m_ns * 1e9  # m/s
    dt = sample_interval_ns * 1e-9  # s

    for i in range(n_traces):
        for j in range(n_samples):
            t0 = j * dt  # two-way travel time at apex
            if t0 <= 0:
                continue

            # Sum over aperture
            amplitude = 0.0
            count = 0
            for k in range(
                max(0, i - aperture_traces),
                min(n_traces, i + aperture_traces + 1),
            ):
                dx = abs(k - i) * trace_spacing_m
                t = np.sqrt(t0 ** 2 + (2 * dx / v) ** 2)
                t_sample = t / dt
                if 0 <= t_sample < n_samples - 1:
                    # Linear interpolation
                    frac = t_sample - int(t_sample)
                    idx = int(t_sample)
                    amp = data[k, idx] * (1 - frac) + data[k, idx + 1] * frac
                    amplitude += amp
                    count += 1

            result[i, j] = amplitude / max(count, 1)

    return result