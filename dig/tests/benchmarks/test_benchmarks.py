import numpy as np
import pytest

from dig.models.profile import Profile
from dig.models.survey import Survey
from dig.processing.assembly import assemble_regular_grid
from dig.processing.detection import blob_detection
from dig.processing.dewow import dewow_median
from dig.processing.gain import agc
from dig.processing.migration import stolt_migration
from dig.processing.pipeline import ProcessingPipeline


@pytest.fixture
def dummy_profile():
    data = np.random.randn(1000, 1024).astype(np.float32)
    return Profile(name="test_1000", data=data, sample_interval_ns=0.1, trace_spacing_m=0.05)


@pytest.fixture
def dummy_profiles():
    return [
        Profile(
            name=f"test_{i}",
            data=np.random.randn(1000, 1024).astype(np.float32),
            sample_interval_ns=0.1,
            trace_spacing_m=0.05,
        )
        for i in range(10)
    ]


@pytest.fixture
def dummy_survey(dummy_profiles):
    return Survey(name="bench_survey", profiles=dummy_profiles)


@pytest.mark.benchmark(group="migration")
def test_bench_stolt_migration(benchmark, dummy_profile):
    benchmark(stolt_migration, dummy_profile.data, 0.1, 0.1, 0.05)


@pytest.mark.benchmark(group="assembly")
def test_bench_assemble_regular_grid(benchmark, dummy_profiles):
    benchmark(assemble_regular_grid, dummy_profiles, 0.5)


@pytest.mark.benchmark(group="detection")
def test_bench_blob_detection(benchmark, dummy_profile):
    # blob_detection(data, min_sigma, max_sigma, num_sigma, threshold)
    benchmark(blob_detection, dummy_profile.data, 1.0, 10.0, 5, 0.2)


@pytest.mark.benchmark(group="pipeline")
def test_bench_e2e_pipeline(benchmark, dummy_profile):
    def run_pipeline():
        pipe = ProcessingPipeline(dummy_profile.data)
        pipe = pipe.process(dewow_median, window_size=51)
        pipe = pipe.process(agc, window_samples=51)
        pipe = pipe.process(
            stolt_migration, velocity_m_ns=0.1, sample_interval_ns=0.1, trace_spacing_m=0.05
        )
        return pipe

    benchmark(run_pipeline)
