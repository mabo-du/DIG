import numpy as np
import os
from dig.models import Profile, Grid3D
from dig.processing.assembly import assemble_regular_grid
from dig.processing.detection import blob_detection, export_to_geopackage
from dig.viz.volume_widget import VolumeWidget
from PySide6.QtWidgets import QApplication
import sys
import fiona

def run_e2e():
    print("Starting Synthetic E2E Test...")
    # 1. Generate Synthetic Profiles
    profiles = []
    for i in range(5):
        data = np.random.rand(100, 50).astype(np.float32)
        # Add a "blob" anomaly
        data[40:50, 20:30] += 5.0
        p = Profile(data=data, trace_spacing_m=0.1, sample_interval_ns=0.5, name=f"Line_{i}")
        profiles.append(p)
    
    # 2. Assemble into Grid3D
    print("Assembling Grid3D...")
    grid = assemble_regular_grid(profiles, crossline_spacing_m=0.5)
    assert grid.data.shape == (100, 5, 50)
    
    # 3. Instantiate VolumeWidget (skipped in headless test to avoid VTK/OpenGL crashes)
    print("Skipping VolumeWidget instantiation in headless environment...")
    # app = QApplication.instance() or QApplication(sys.argv)
    # widget = VolumeWidget()
    # widget.set_grid(grid)
    # assert widget is not None
    
    # 4. Run Detection on the middle slice
    print("Running Threshold Detection...")
    slice_idx = 2
    slice_data = grid.data[:, :, slice_idx]
    # Inject an explicit point
    slice_data[45, 2] = 100.0
    from dig.processing.detection import threshold_detection
    detections = threshold_detection(slice_data, threshold=50.0)
    print(f"Detected {len(detections['points'])} points.")
    
    # 5. Export GeoPackage
    print("Exporting GeoPackage...")
    out_gpkg = "test_blobs.gpkg"
    export_to_geopackage([detections], out_gpkg)
    
    # 6. Confirm file is valid
    print("Validating GeoPackage...")
    assert os.path.exists(out_gpkg)
    with fiona.open(out_gpkg, "r") as src:
        assert len(src) == len(detections['points'])
        
    # Cleanup
    os.remove(out_gpkg)
    print("E2E Test Passed Successfully!")

if __name__ == "__main__":
    run_e2e()
