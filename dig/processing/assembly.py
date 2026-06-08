"""dig/processing/assembly.py — Assemble 2D GPR profiles into 3D volumes.

exports: assemble_regular_grid, assemble_irregular_grid
used_by: DIG
rules:
- Must return Grid3D objects
"""

from typing import List, Optional
import numpy as np
from scipy.interpolate import griddata
import pyproj

from dig.models.grid import Grid3D
from dig.models.profile import Profile


def assemble_regular_grid(
    profiles: List[Profile],
    crossline_spacing_m: float = 0.5,
) -> Grid3D:
    """Assemble a set of parallel profiles into a regular 3D grid.

    Assumes all profiles are oriented in the same direction, start at the
    same inline position, and are separated by a constant crossline spacing.
    The volume is truncated to the shortest profile length and sample depth.
    
    Args:
        profiles: List of parallel 2D Profile objects.
        crossline_spacing_m: Distance between adjacent profiles.
        
    Returns:
        Grid3D volume.
    """
    if not profiles:
        raise ValueError("No profiles provided.")

    n_crossline = len(profiles)
    n_inline = min(p.num_traces for p in profiles)
    n_depth = min(p.num_samples for p in profiles)

    data = np.zeros((n_inline, n_crossline, n_depth), dtype=np.float32)

    for i, p in enumerate(profiles):
        data[:, i, :] = p.data[:n_inline, :n_depth]

    return Grid3D(
        data=data,
        inline_spacing_m=profiles[0].trace_spacing_m,
        crossline_spacing_m=crossline_spacing_m,
        sample_interval_ns=profiles[0].sample_interval_ns,
        origin_easting=0.0,
        origin_northing=0.0,
        rotation_deg=0.0,
    )


def assemble_irregular_grid(
    profiles: List[Profile],
    trace_coordinates: List[np.ndarray],
    grid_spacing_m: float = 0.5,
    method: str = "cubic",
    crs_from: Optional[str] = "EPSG:4326",
    crs_to: Optional[str] = "EPSG:32633",
) -> Grid3D:
    """Assemble irregular GPS-tracked profiles into a regular 3D grid using interpolation.

    Args:
        profiles: List of GPR profiles.
        trace_coordinates: List of coordinate arrays (n_traces, 2) corresponding to each profile.
        grid_spacing_m: Desired cell size of the output Grid3D.
        method: Interpolation method for scipy.interpolate.griddata ('linear', 'nearest', 'cubic').
        crs_from: Source CRS (e.g. lon/lat GPS EPSG:4326).
        crs_to: Target projected CRS (e.g. UTM EPSG:32633). If both are provided, coordinates are transformed.

    Returns:
        Grid3D representing the interpolated 3D volume.
    """
    if not profiles or not trace_coordinates:
        raise ValueError("Profiles and trace coordinates must be provided.")

    if len(profiles) != len(trace_coordinates):
        raise ValueError("Number of profiles must match number of coordinate arrays.")

    transformer = None
    if crs_from and crs_to:
        transformer = pyproj.Transformer.from_crs(crs_from, crs_to, always_xy=True)

    all_x = []
    all_y = []
    all_data = []

    n_depth = min(p.num_samples for p in profiles)
    sample_interval_ns = profiles[0].sample_interval_ns

    for p, coords in zip(profiles, trace_coordinates):
        if len(coords) != p.num_traces:
            raise ValueError(f"Profile {p.name} has {p.num_traces} traces but {len(coords)} coordinates.")

        x_coords = coords[:, 0]
        y_coords = coords[:, 1]

        if transformer:
            # Transform from geographic to projected coordinates
            x_coords, y_coords = transformer.transform(x_coords, y_coords)

        all_x.append(x_coords)
        all_y.append(y_coords)

        # Collect data truncated to minimum depth
        all_data.append(p.data[:, :n_depth])

    points_x = np.concatenate(all_x)
    points_y = np.concatenate(all_y)
    values = np.concatenate(all_data, axis=0)

    min_x, max_x = np.min(points_x), np.max(points_x)
    min_y, max_y = np.min(points_y), np.max(points_y)

    # Create coordinate grids
    grid_x, grid_y = np.mgrid[
        min_x:max_x:grid_spacing_m,
        min_y:max_y:grid_spacing_m
    ]

    points = np.column_stack((points_x, points_y))

    # Perform ND interpolation over all depth slices simultaneously
    grid_data_interp = griddata(
        points,
        values,
        (grid_x, grid_y),
        method=method,
        fill_value=0.0
    )

    return Grid3D(
        data=grid_data_interp,
        inline_spacing_m=grid_spacing_m,
        crossline_spacing_m=grid_spacing_m,
        sample_interval_ns=sample_interval_ns,
        origin_easting=min_x,
        origin_northing=min_y,
        rotation_deg=0.0,
    )
