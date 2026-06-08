import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dig.processing.batch import load_recipe, process_batch, resolve_function


def test_batch_recipe_parsing_yaml(tmp_path):
    recipe_path = tmp_path / "recipe.yaml"
    recipe_content = """
steps:
  - name: dewow_median
    params:
      window_size: 50
  - name: remove_background_global
    """
    recipe_path.write_text(recipe_content)

    steps = load_recipe(str(recipe_path))
    assert len(steps) == 2
    assert steps[0]["name"] == "dewow_median"
    assert steps[0]["params"]["window_size"] == 50
    assert steps[1]["name"] == "remove_background_global"


def test_batch_recipe_parsing_json(tmp_path):
    recipe_path = tmp_path / "recipe.json"
    recipe_content = {"steps": [{"name": "dewow_median", "params": {"window_size": 10}}]}
    recipe_path.write_text(json.dumps(recipe_content))

    steps = load_recipe(str(recipe_path))
    assert len(steps) == 1
    assert steps[0]["name"] == "dewow_median"


def test_resolve_function():
    func = resolve_function("dewow_median")
    assert callable(func)
    assert func.__name__ == "dewow_median"

    with pytest.raises(ValueError, match="Unknown processing step"):
        resolve_function("non_existent_function")


@patch("dig.processing.batch.DZTFile")
def test_batch_pipeline_execution(mock_dzt, tmp_path):
    # Setup mock parser
    mock_instance = MagicMock()
    mock_instance.traces = np.random.rand(100, 50).astype(np.float32)
    mock_instance.metadata = {"trace_spacing_m": 0.05, "sample_interval_ns": 0.1}
    mock_dzt.return_value = mock_instance

    # Create fake files so path.exists() passes
    f1 = tmp_path / "test1.dzt"
    f1.write_text("fake")

    recipe = [
        {"name": "dewow_median", "params": {"window_size": 11}},
        {"name": "remove_background_global"},
    ]

    results = process_batch(recipe, [str(f1)], max_workers=1)

    assert len(results) == 1
    res = results[0]
    assert res["status"] == "success"
    assert res["file"] == str(f1)
    assert res["num_steps"] == 3
    assert res["final_shape"] == [100, 50]


@patch("dig.processing.batch.DZTFile")
def test_batch_parallel_execution(mock_dzt, tmp_path):
    mock_instance = MagicMock()
    mock_instance.traces = np.random.rand(10, 10).astype(np.float32)
    mock_instance.metadata = {}
    mock_dzt.return_value = mock_instance

    files = []
    for i in range(3):
        f = tmp_path / f"test{i}.dzt"
        f.write_text("fake")
        files.append(str(f))

    recipe = [{"name": "remove_background_global"}]

    # Track progress
    progress_calls = []

    def progress_cb(completed, total):
        progress_calls.append((completed, total))

    results = process_batch(recipe, files, max_workers=2, progress_callback=progress_cb)

    assert len(results) == 3
    for res in results:
        assert res["status"] == "success"

    # Check progress callbacks: 0/3, 1/3, 2/3, 3/3 = 4 calls
    assert len(progress_calls) == 4
    assert progress_calls[-1] == (3, 3)
