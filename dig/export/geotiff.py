"""geotiff.py — Production-grade GeoTIFF export with proper CRS and affine transforms.

exports: export_geotiff(data, output_path, crs_epsg, origin_easting, origin_northing, pixel_size, rotation_deg, band_descriptions, nodata) -> str, export_cog(data, output_path, **kwargs) -> str
used_by: callers → export_geotiff, export_cog
rules:
  - Affine transform must use standard rasterio definition (negative e for north-up)
"""

from pathlib import Path
from typing import Any, Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine


def _build_affine(
    origin_easting: float,
    origin_northing: float,
    pixel_size: float,
    rotation_deg: float,
    n_cols: int,
    n_rows: int,
) -> Affine:
    """Build an affine transformation matrix for a rotated local grid.

    Handles the half-pixel shift (PixelIsArea convention) and
    clockwise rotation from grid north.

    Args:
        origin_easting: Easting of grid origin (centre of top-left pixel)
        origin_northing: Northing of grid origin
        pixel_size: Pixel resolution in metres
        rotation_deg: Clockwise rotation from north (degrees)
        n_cols: Number of columns
        n_rows: Number of rows

    Returns:
        Rasterio Affine transformation
    """
    alpha = np.radians(rotation_deg)
    cos_a = np.cos(alpha)
    sin_a = np.sin(alpha)

    # Half-pixel shift (PixelIsArea convention)
    # The provided origin is the center of the top-left pixel.
    # Rasterio expects the top-left corner of the top-left pixel.
    half_px = pixel_size / 2.0
    origin_easting += -half_px * cos_a + half_px * sin_a
    origin_northing += half_px * sin_a + half_px * cos_a

    return Affine(
        pixel_size * cos_a,  # a: pixel width in geographic x
        -pixel_size * sin_a,  # b: row rotation (x-skew)
        origin_easting,  # c: x-coordinate of origin
        -pixel_size * sin_a,  # d: column rotation (y-skew)
        -pixel_size * cos_a,  # e: pixel height (negative = north-up)
        origin_northing,  # f: y-coordinate of origin
    )


def export_geotiff(
    data: np.ndarray,
    output_path: str | Path,
    crs_epsg: int = 4326,
    origin_easting: float = 0.0,
    origin_northing: float = 0.0,
    pixel_size: float = 1.0,
    rotation_deg: float = 0.0,
    band_descriptions: Optional[list[str]] = None,
    nodata: Optional[float] = None,
) -> str:
    """Export processed geophysical data as a georeferenced GeoTIFF.

    Supports multi-band export (each band = one depth slice).

    Args:
        data: 2D (rows, cols) or 3D (bands, rows, cols) array
        output_path: Output .tif path
        crs_epsg: EPSG code for the CRS
        origin_easting: Easting of grid origin
        origin_northing: Northing of grid origin
        pixel_size: Pixel resolution in CRS units
        rotation_deg: Clockwise rotation from north
        band_descriptions: Per-band description strings
        nodata: NoData value (auto-detected if None)

    Returns:
        Path to the written GeoTIFF
    """
    output_path = Path(output_path)

    # Handle 2D → 3D
    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    n_bands, n_rows, n_cols = data.shape

    # Build affine transform
    transform = _build_affine(
        origin_easting,
        origin_northing,
        pixel_size,
        rotation_deg,
        n_cols,
        n_rows,
    )

    # CRS
    crs = CRS.from_epsg(crs_epsg)

    # Auto-detect nodata
    if nodata is None:
        if np.issubdtype(data.dtype, np.floating):
            nodata = np.nan
        else:
            nodata = -9999

    profile = {
        "driver": "GTiff",
        "height": n_rows,
        "width": n_cols,
        "count": n_bands,
        "dtype": data.dtype,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }

    with rasterio.open(output_path, "w", **profile) as dst:
        for i in range(n_bands):
            band_data = data[i]
            if nodata is not None and np.isnan(nodata):
                band_data = np.where(np.isnan(band_data), nodata, band_data)
            dst.write(band_data, i + 1)

            # Band description
            if band_descriptions and i < len(band_descriptions):
                dst.set_band_description(i + 1, band_descriptions[i])

    return str(output_path)


def export_cog(
    data: np.ndarray,
    output_path: str | Path,
    **kwargs: Any,
) -> str:
    """Export as Cloud-Optimized GeoTIFF (COG).

    COGs enable efficient web streaming — stakeholders can explore
    visualizations without GIS software.

    Args:
        data: 2D or 3D array
        output_path: Output .tif path
        **kwargs: Passed to export_geotiff

    Returns:
        Path to the written COG
    """
    path = export_geotiff(data, output_path, **kwargs)

    # Re-open and convert to COG
    with rasterio.open(path) as src:
        profile = src.profile.copy()
        profile["driver"] = "COG"
        profile["compress"] = "DEFLATE"

        cog_path = Path(output_path).with_suffix(".cog.tif")
        with rasterio.open(cog_path, "w", **profile) as dst:
            for i in range(1, src.count + 1):
                dst.write(src.read(i), i)

    return str(cog_path)
