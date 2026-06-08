"""Tests for DIG export modules."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np

from dig.export.csv_export import export_csv
from dig.export.geojson import anomaly_to_feature, export_geojson
from dig.export.geotiff import _build_affine, export_geotiff


class TestGeoTIFF:
    def test_build_affine_no_rotation(self):
        transform = _build_affine(
            origin_easting=500000.0,
            origin_northing=5000000.0,
            pixel_size=1.0,
            rotation_deg=0.0,
            n_cols=100,
            n_rows=100,
        )
        assert abs(transform.a - 1.0) < 0.01  # pixel width
        assert (
            abs(transform.e - (-1.0)) < 0.01
        )  # pixel height (rasterio convention: north-up is negative)

    def test_build_affine_rotation(self):
        transform = _build_affine(
            origin_easting=500000.0,
            origin_northing=5000000.0,
            pixel_size=0.5,
            rotation_deg=15.0,
            n_cols=100,
            n_rows=100,
        )
        assert abs(transform.a) < 0.5
        assert abs(transform.e) < 0.5

    def test_export_geotiff_2d(self):
        data = np.random.rand(50, 100).astype(np.float32)
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
            path = f.name

        try:
            result = export_geotiff(data, path, crs_epsg=32630)
            assert Path(result).exists()
            assert Path(result).stat().st_size > 0
        finally:
            Path(path).unlink(missing_ok=True)

    def test_export_geotiff_3d(self):
        data = np.random.rand(3, 50, 100).astype(np.float32)
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
            path = f.name

        try:
            result = export_geotiff(
                data,
                path,
                crs_epsg=32630,
                band_descriptions=["Depth 0.5m", "Depth 1.0m", "Depth 1.5m"],
            )
            assert Path(result).exists()
        finally:
            Path(path).unlink(missing_ok=True)


class TestCSV:
    def test_export_csv_2d(self):
        data = np.random.rand(10, 20)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name

        try:
            result = export_csv(data, path)
            assert Path(result).exists()
            content = Path(result).read_text()
            assert len(content.splitlines()) > 0
        finally:
            Path(path).unlink(missing_ok=True)


class TestGeoJSON:
    def test_anomaly_to_feature(self):
        feature = anomaly_to_feature(
            easting=500000.0,
            northing=5000000.0,
            anomaly_type="wall",
            confidence=0.85,
            depth_m=1.5,
        )
        assert feature["type"] == "Feature"
        assert feature["geometry"]["coordinates"] == [500000.0, 5000000.0]
        assert feature["properties"]["anomaly_type"] == "wall"
        assert feature["properties"]["confidence"] == 0.85

    def test_export_geojson(self):
        features = [
            anomaly_to_feature(500000, 5000000, "wall", 0.9),
            anomaly_to_feature(500010, 5000020, "void", 0.7),
        ]
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as f:
            path = f.name

        try:
            result = export_geojson(features, path)
            assert Path(result).exists()
        finally:
            Path(path).unlink(missing_ok=True)
