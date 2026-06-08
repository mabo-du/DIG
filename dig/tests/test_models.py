"""Tests for DIG data models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np

from dig.models.audit import AuditTrail
from dig.models.grid import Grid3D
from dig.models.magnetometry_grid import MagnetometryGrid
from dig.models.profile import Profile
from dig.models.survey import Survey


class TestAuditTrail:
    def test_add_step(self):
        trail = AuditTrail()
        trail.add_step("dewow", {"window": 50})
        assert len(trail) == 1
        assert trail.steps[0].name == "dewow"

    def test_to_json_roundtrip(self):
        trail = AuditTrail()
        trail.add_step("dewow", {"window": 50})
        trail.add_step("bandpass", {"low": 100, "high": 500})
        json_str = trail.to_json()
        assert "dewow" in json_str
        assert "bandpass" in json_str

    def test_save_and_load(self, tmp_path):
        trail = AuditTrail()
        trail.add_step("test", {"param": 1})
        path = tmp_path / "audit.json"
        trail.save(str(path))
        loaded = AuditTrail.from_json(str(path))
        assert len(loaded) == 1
        assert loaded.steps[0].name == "test"


class TestSurvey:
    def test_survey_defaults(self):
        survey = Survey(path=Path("/test.dzt"), format="dzt")
        assert survey.format == "dzt"
        assert survey.num_traces == 0
        assert len(survey.audit) == 0

    def test_survey_repr(self):
        survey = Survey(path=Path("/test.dzt"), format="dzt", num_traces=100, samples_per_trace=512)
        assert "dzt" in repr(survey)
        assert "100" in repr(survey)


class TestProfile:
    def test_profile_properties(self):
        data = np.random.rand(50, 200)
        profile = Profile(name="test", data=data, trace_spacing_m=0.05, sample_interval_ns=0.1)
        assert profile.num_traces == 50
        assert profile.num_samples == 200
        assert abs(profile.time_window_ns - 20.0) < 0.01
        assert abs(profile.length_m - 2.5) < 0.01


class TestGrid3D:
    def test_grid_properties(self):
        data = np.random.rand(10, 20, 30)
        grid = Grid3D(data=data)
        assert grid.shape == (10, 20, 30)
        assert grid.time_slice(5).shape == (10, 20)
        assert grid.inline_section(3).shape == (20, 30)
        assert grid.crossline_section(10).shape == (10, 30)


class TestMagnetometryGrid:
    def test_extent(self):
        data = np.random.rand(50, 100)
        grid = MagnetometryGrid(
            data=data,
            cell_size_m=0.5,
            origin_easting=500000.0,
            origin_northing=5000000.0,
        )
        w, e, s, n = grid.extent_m
        assert abs(w - 500000.0) < 0.01
        assert abs(e - 500050.0) < 0.01
        assert abs(s - 5000000.0) < 0.01
        assert abs(n - 5000025.0) < 0.01
