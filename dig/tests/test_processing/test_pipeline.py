"""Tests for the immutable DAG processing pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json
import numpy as np
from dig.processing.pipeline import ProcessingPipeline, ProcessingNode
from dig.processing.dewow import dewow_fft
from dig.processing.background import remove_background_global
from dig.processing.gain import sec_gain


class TestProcessingPipeline:
    def test_create_pipeline(self):
        data = np.ones((5, 100))
        pipe = ProcessingPipeline(data)
        assert pipe.num_steps == 1
        assert pipe.current_step.name == "original"
        assert pipe.current_step.step_id == 0
        assert np.array_equal(pipe.data, data)
        assert np.array_equal(pipe.original_data, data)

    def test_single_processing_step(self):
        data = np.ones((3, 100)) * 5.0
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0, cutoff_hz=0.5)

        assert pipe.num_steps == 2
        assert pipe.current_step.name == "dewow_fft"
        assert pipe.current_step.step_id == 1
        assert pipe.current_step.parent_id == 0
        assert "sample_rate" in pipe.current_step.parameters
        assert np.all(np.abs(pipe.data) < 0.1)  # DC removed

    def test_chaining_multiple_steps(self):
        data = np.ones((3, 100)) * 5.0
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)
        pipe = pipe.process(remove_background_global)
        pipe = pipe.process(sec_gain, sample_rate=1000.0, alpha=0.5)

        assert pipe.num_steps == 4
        assert pipe.current_step.name == "sec_gain"
        assert pipe.current_step.step_id == 3
        assert pipe.current_step.parent_id == 2

    def test_original_data_preserved(self):
        """Original data must never be modified by processing."""
        data = np.ones((3, 100)) * 5.0
        original_copy = data.copy()
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)

        assert np.array_equal(pipe.original_data, original_copy)
        assert not np.array_equal(pipe.data, pipe.original_data)  # processed ≠ original

    def test_branching(self):
        """Non-linear undo: branch from a previous step."""
        data = np.ones((3, 100)) * 5.0
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)

        # Branch from step 0 (original data)
        branch = pipe.branch(step_id=0)
        assert branch.num_steps == 1
        assert branch.current_step.name == "original"
        assert np.array_equal(branch.data, data)

        # Apply different processing on the branch
        branch = branch.process(remove_background_global)
        assert branch.num_steps == 2
        assert branch.current_step.name == "remove_background_global"

        # Original pipeline unchanged
        assert pipe.current_step.name == "dewow_fft"

    def test_branch_invalid_step(self):
        data = np.ones((3, 100))
        pipe = ProcessingPipeline(data)

        import pytest
        with pytest.raises(ValueError, match="Step 99 not found"):
            pipe.branch(step_id=99)

    def test_export_history(self):
        data = np.ones((3, 100))
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)
        pipe = pipe.process(sec_gain, sample_rate=1000.0, alpha=0.5)

        history = pipe.export_history()
        assert len(history) == 3

        # Root node
        assert history[0]["name"] == "original"
        assert history[0]["step_id"] == 0
        assert history[0]["parent_id"] is None

        # First processing step
        assert history[1]["name"] == "dewow_fft"
        assert history[1]["step_id"] == 1
        assert history[1]["parent_id"] == 0
        assert history[1]["parameters"]["sample_rate"] == 1000.0

        # Second processing step
        assert history[2]["name"] == "sec_gain"
        assert history[2]["step_id"] == 2
        assert history[2]["parent_id"] == 1

    def test_export_history_json(self):
        data = np.ones((3, 100))
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)

        json_str = pipe.export_history_json()
        parsed = json.loads(json_str)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "original"
        assert parsed[1]["name"] == "dewow_fft"
        # JSON should include data shapes
        assert "data_shape" in parsed[0]

    def test_get_step(self):
        data = np.ones((3, 100))
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)

        step0 = pipe.get_step(0)
        assert step0.name == "original"
        assert step0.data is not None

        step1 = pipe.get_step(1)
        assert step1.name == "dewow_fft"

        import pytest
        with pytest.raises(ValueError):
            pipe.get_step(99)

    def test_repr(self):
        data = np.ones((3, 100))
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(dewow_fft, sample_rate=1000.0)
        rep = repr(pipe)
        assert "ProcessingPipeline" in rep
        assert "steps=2" in rep
        assert "dewow_fft" in rep

    def test_preserves_dtype(self):
        """Pipeline should consistently use float64."""
        data = np.ones((3, 100), dtype=np.float32)
        pipe = ProcessingPipeline(data)
        assert pipe.data.dtype == np.float64

        pipe = pipe.process(dewow_fft, sample_rate=1000.0)
        assert pipe.data.dtype == np.float64

    def test_empty_parameters_recorded(self):
        """Functions called without kwargs should record empty params dict."""
        data = np.ones((3, 100)) * 5.0
        pipe = ProcessingPipeline(data)
        pipe = pipe.process(remove_background_global)

        assert pipe.current_step.parameters == {}


class TestProcessingNode:
    def test_to_dict(self):
        node = ProcessingNode(
            step_id=1,
            name="test_func",
            parameters={"param1": 10.0},
            timestamp=1234567890.0,
            parent_id=0,
            data=np.array([1.0, 2.0]),
        )
        d = node.to_dict()
        assert d["step_id"] == 1
        assert d["name"] == "test_func"
        assert d["parameters"] == {"param1": 10.0}
        assert d["parent_id"] == 0
        assert "software_version" in d
        # Data should NOT be in dict
        assert "data" not in d