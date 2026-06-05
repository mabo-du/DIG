"""GeoJSON export for GIS and ecosystem integration."""

from pathlib import Path
import json
import numpy as np


def export_geojson(
    features: list[dict],
    output_path: str | Path,
    crs_epsg: int = 4326,
) -> str:
    """Export anomaly detections or survey boundaries as GeoJSON.

    Args:
        features: List of GeoJSON Feature objects
        output_path: Output .geojson path
        crs_epsg: EPSG code

    Returns:
        Path to the written GeoJSON
    """
    output_path = Path(output_path)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "crs": {
            "type": "name",
            "properties": {"name": f"EPSG:{crs_epsg}"},
        },
    }

    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    return str(output_path)


def anomaly_to_feature(
    easting: float,
    northing: float,
    anomaly_type: str,
    confidence: float,
    depth_m: float = 0.0,
    properties: dict | None = None,
) -> dict:
    """Create a GeoJSON Feature from an anomaly detection.

    Args:
        easting: Easting coordinate
        northing: Northing coordinate
        anomaly_type: Type of anomaly (e.g., "wall", "void", "buried_feature")
        confidence: Detection confidence (0-1)
        depth_m: Estimated depth in metres
        properties: Additional properties

    Returns:
        GeoJSON Feature dict
    """
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [easting, northing],
        },
        "properties": {
            "anomaly_type": anomaly_type,
            "confidence": confidence,
            "depth_m": depth_m,
            **(properties or {}),
        },
    }
    return feature