import numpy as np
import rasterio
from rasterio.transform import from_origin
from dig.export.geotiff import export_geotiff
from dig.export.qgis import generate_qgz
from pathlib import Path

# Create dummy rasters
data1 = np.random.rand(100, 100).astype(np.float32) * 100
data2 = np.random.rand(100, 100).astype(np.float32) * 50

# Ensure directories
Path("test_out").mkdir(exist_ok=True)

export_geotiff(data1, "test_out/raster1.tif", crs_epsg=3857, origin_easting=1000, origin_northing=2000, pixel_size=1.0)
export_geotiff(data2, "test_out/raster2.tif", crs_epsg=3857, origin_easting=1000, origin_northing=2000, pixel_size=1.0)

print(generate_qgz(["test_out/raster1.tif", "test_out/raster2.tif"], "test_out/project.qgs", crs_epsg=3857))
