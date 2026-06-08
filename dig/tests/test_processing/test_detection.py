import warnings

import numpy as np

from dig.processing.detection import blob_detection, onnx_inference, threshold_detection


def test_threshold_detection():
    data = np.zeros((100, 50))
    # Inject high amplitude
    data[20:25, 30:35] = 2.0

    res = threshold_detection(data, threshold=1.0)

    assert res["type"] == "threshold"
    pts = res["points"]
    # 5x5 region = 25 points
    assert len(pts) == 25

    # Check that a known point is present (note: points are [x, y] == [sample, trace])
    # x is sample (idx 1), y is trace (idx 0)
    # data[20, 30] means trace 20, sample 30 -> [30.0, 20.0]
    assert [30.0, 20.0] in pts


def test_blob_detection():
    data = np.zeros((100, 50))
    # Inject a Gaussian-like blob
    # A simple square for LoG to detect
    data[40:60, 20:30] = 5.0

    res = blob_detection(data, min_sigma=1.0, max_sigma=5.0, num_sigma=5, threshold=0.1)

    assert res["type"] == "blob_log"
    pts = res["points"]
    assert len(pts) > 0

    # We injected it around trace 50, sample 25
    # Verify there is at least one point near [25.0, 50.0]
    found_near = False
    for pt in pts:
        x, y = pt
        if 20 <= x <= 30 and 40 <= y <= 60:
            found_near = True
            break
    assert found_near


def test_onnx_inference_missing_model():
    data = np.zeros((100, 50))

    # Catch warnings so they don't clutter output, though pytest captures them
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        res = onnx_inference(data, "/path/to/nonexistent/model.onnx")

        assert len(w) == 1
        assert "not found" in str(w[-1].message)

    assert res["type"] == "onnx"
    assert res["points"] == []
    assert res["error"] == "model_not_found"
