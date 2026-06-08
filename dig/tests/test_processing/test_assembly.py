import numpy as np
import pytest

from dig.models.profile import Profile
from dig.processing.assembly import assemble_irregular_grid, assemble_regular_grid


def test_assemble_regular_grid():
    # Synthetic data
    p1 = Profile(name="line1", data=np.ones((100, 50)), trace_spacing_m=0.1, sample_interval_ns=0.5)
    p2 = Profile(
        name="line2", data=np.ones((100, 50)) * 2, trace_spacing_m=0.1, sample_interval_ns=0.5
    )

    grid = assemble_regular_grid([p1, p2], crossline_spacing_m=0.5)

    assert grid.data.shape == (100, 2, 50)
    assert grid.inline_spacing_m == 0.1
    assert grid.crossline_spacing_m == 0.5
    assert grid.sample_interval_ns == 0.5
    # Check data mapping
    np.testing.assert_array_equal(grid.data[:, 0, :], 1.0)
    np.testing.assert_array_equal(grid.data[:, 1, :], 2.0)


def test_assemble_regular_grid_mismatched_lengths():
    # Truncates to minimum length
    p1 = Profile(name="line1", data=np.ones((100, 60)), trace_spacing_m=0.1)
    p2 = Profile(name="line2", data=np.ones((80, 50)), trace_spacing_m=0.1)

    grid = assemble_regular_grid([p1, p2])
    assert grid.data.shape == (80, 2, 50)


def test_assemble_regular_grid_single_profile():
    p1 = Profile(name="line1", data=np.ones((100, 50)), trace_spacing_m=0.1)
    grid = assemble_regular_grid([p1])
    assert grid.data.shape == (100, 1, 50)


def test_assemble_regular_grid_empty():
    with pytest.raises(ValueError, match="No profiles provided"):
        assemble_regular_grid([])


def test_assemble_irregular_grid():
    # 2 profiles, 10 traces each, 50 samples
    p1 = Profile(name="line1", data=np.ones((10, 50)), trace_spacing_m=0.1)
    p2 = Profile(name="line2", data=np.ones((10, 50)) * 2, trace_spacing_m=0.1)

    # Fake coordinates (x, y)
    coords1 = np.column_stack((np.linspace(0, 9, 10), np.zeros(10)))
    coords2 = np.column_stack((np.linspace(0, 9, 10), np.ones(10)))

    # We will interpolate onto a grid with 1.0m spacing
    # This should yield x from 0 to 9, y from 0 to 1
    # Note: no CRS transform
    grid = assemble_irregular_grid(
        [p1, p2],
        [coords1, coords2],
        grid_spacing_m=1.0,
        method="linear",
        crs_from=None,
        crs_to=None,
    )

    # x points: 0, 1, ..., 8 (9 points)
    # y points: 0 (1 point)
    assert grid.data.shape == (9, 1, 50)

    # Values at y=0 should be 1.0
    assert np.allclose(grid.data[:, 0, :], 1.0)


def test_assemble_irregular_grid_empty():
    with pytest.raises(ValueError, match="Profiles and trace coordinates must be provided"):
        assemble_irregular_grid([], [])


def test_assemble_irregular_grid_mismatch_count():
    p1 = Profile(name="line1", data=np.ones((10, 50)), trace_spacing_m=0.1)
    coords = [np.ones((10, 2)), np.ones((10, 2))]
    with pytest.raises(ValueError, match="Number of profiles must match"):
        assemble_irregular_grid([p1], coords)


def test_assemble_irregular_grid_mismatch_traces():
    p1 = Profile(name="line1", data=np.ones((10, 50)), trace_spacing_m=0.1)
    coords = [np.ones((9, 2))]
    with pytest.raises(ValueError, match="has 10 traces but 9 coordinates"):
        assemble_irregular_grid([p1], coords)
