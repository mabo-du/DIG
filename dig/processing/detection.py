"""detection.py — Target detection and extraction in GPR data.

exports: threshold_detection(data, threshold) -> dict
exports: blob_detection(data, min_sigma, max_sigma, num_sigma, threshold) -> dict
exports: onnx_inference(data, model_path) -> dict
exports: export_to_geopackage(detections, filepath, crs) -> None
used_by: dig/processing/pipeline.py -> process
rules:
  - ONNX inference must degrade gracefully if model file is missing or onnxruntime is absent.
  - GeoPackage export uses geopandas or fiona if available.
"""

import os
import warnings
from typing import Any, Dict, List

import numpy as np


def threshold_detection(data: np.ndarray, threshold: float = 0.8) -> Dict[str, Any]:
    """Basic amplitude threshold detection.

    Args:
        data: 2D numpy array (traces, samples)
        threshold: Amplitude threshold

    Returns:
        Dict with 'points' (list of [trace, sample] coords)
    """
    abs_data = np.abs(data)
    y_idx, x_idx = np.where(abs_data >= threshold)

    points = [[float(x), float(y)] for y, x in zip(y_idx, x_idx)]

    return {"type": "threshold", "points": points}


def blob_detection(
    data: np.ndarray,
    min_sigma: float = 1.0,
    max_sigma: float = 10.0,
    num_sigma: int = 5,
    threshold: float = 0.2,
) -> Dict[str, Any]:
    """Scipy ndimage LoG (Laplacian of Gaussian) blob detection.

    Args:
        data: 2D numpy array
        min_sigma: Minimum standard deviation for Gaussian kernel
        max_sigma: Maximum standard deviation for Gaussian kernel
        num_sigma: Number of scales to compute
        threshold: Detection threshold in scale space
    """
    from scipy.ndimage import gaussian_laplace, maximum_filter

    sigmas = np.linspace(min_sigma, max_sigma, num_sigma)
    scale_space = np.empty((num_sigma, *data.shape))

    for i, s in enumerate(sigmas):
        # Laplacian of Gaussian (LoG)
        # Normalize by s**2 to maintain scale invariance
        log_img = -gaussian_laplace(data, sigma=s) * (s**2)
        scale_space[i, :, :] = log_img

    # Find local maxima across scale space
    local_max = maximum_filter(scale_space, size=3) == scale_space

    # Thresholding
    mask = scale_space > threshold
    peaks = local_max & mask

    z, y, x = np.where(peaks)

    points = [[float(x_val), float(y_val)] for y_val, x_val in zip(y, x)]
    radii = [float(sigmas[z_val] * np.sqrt(2)) for z_val in z]

    return {"type": "blob_log", "points": points, "radii": radii}


def onnx_inference(data: np.ndarray, model_path: str) -> Dict[str, Any]:
    """Graceful placeholder ONNX inference harness.

    Args:
        data: GPR data array
        model_path: Path to .onnx model

    Returns:
        Detection dictionary. Returns empty if onnxruntime is missing or model not found.
    """
    if not os.path.exists(model_path):
        warnings.warn(f"ONNX model not found at {model_path}. Skipping inference.")
        return {"type": "onnx", "points": [], "error": "model_not_found"}

    try:
        import onnxruntime as ort
    except ImportError:
        warnings.warn("onnxruntime not installed. Skipping ONNX inference.")
        return {"type": "onnx", "points": [], "error": "onnxruntime_missing"}

    try:
        session = ort.InferenceSession(model_path)
        input_name = session.get_inputs()[0].name

        # Preprocess: reshape to typical model format, e.g. [1, 1, H, W]
        input_data = data.astype(np.float32)
        input_data = np.expand_dims(np.expand_dims(input_data, axis=0), axis=0)

        outputs = session.run(None, {input_name: input_data})

        # Placeholder extraction
        out_heatmap = outputs[0][0, 0]
        y_idx, x_idx = np.where(out_heatmap > 0.5)
        points = [[float(x), float(y)] for y, x in zip(y_idx, x_idx)]

        return {"type": "onnx", "points": points}

    except Exception as e:
        warnings.warn(f"ONNX inference failed: {e}")
        return {"type": "onnx", "points": [], "error": str(e)}


def export_to_geopackage(
    detections: List[Dict[str, Any]], filepath: str, crs: str = "EPSG:4326"
) -> None:
    """Export detections to GeoPackage using geopandas.

    Args:
        detections: List of detection dictionaries (each needs 'points' mapped to lon/lat)
        filepath: Output .gpkg path
        crs: Coordinate reference system
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        warnings.warn("geopandas or shapely not installed. Cannot export to GeoPackage.")
        return

    all_points = []
    types = []

    for det in detections:
        t = det.get("type", "unknown")
        for pt in det.get("points", []):
            if len(pt) >= 2:
                # Expecting pt as [x, y]
                x, y = pt[0], pt[1]
                all_points.append(Point(x, y))
                types.append(t)

    if not all_points:
        warnings.warn("No valid points found to export.")
        return

    gdf = gpd.GeoDataFrame({"type": types}, geometry=all_points, crs=crs)

    gdf.to_file(filepath, driver="GPKG")
