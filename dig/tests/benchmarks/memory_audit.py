import tracemalloc

import numpy as np

from dig.models.profile import Profile
from dig.processing.assembly import assemble_regular_grid
from dig.processing.dewow import dewow_median
from dig.processing.gain import agc
from dig.processing.pipeline import ProcessingPipeline


def audit_assembly(profiles, label="assembly"):
    tracemalloc.start()

    _grid = assemble_regular_grid(profiles, 0.5)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"[{label}] Peak memory: {peak / 1024 / 1024:.2f} MB")
    return peak


def audit_pipeline(profile, label="pipeline"):
    tracemalloc.start()

    pipe = ProcessingPipeline(profile.data)
    # 10 step pipeline
    for i in range(5):
        pipe = pipe.process(dewow_median, window_size=51)
        pipe = pipe.process(agc, window_samples=51)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"[{label}] Peak memory: {peak / 1024 / 1024:.2f} MB")
    return peak


if __name__ == "__main__":
    # Medium size: 1000x1024
    med_profiles = [
        Profile(
            name=f"test_{i}",
            data=np.random.randn(1000, 1024).astype(np.float32),
            sample_interval_ns=0.1,
            trace_spacing_m=0.05,
        )
        for i in range(10)
    ]
    audit_assembly(med_profiles, "Assembly Medium (10 profiles 1000x1024)")
    audit_pipeline(med_profiles[0], "Pipeline Medium (1000x1024)")

    # Large size: 5000x2048
    large_profiles = [
        Profile(
            name=f"test_{i}",
            data=np.random.randn(5000, 2048).astype(np.float32),
            sample_interval_ns=0.1,
            trace_spacing_m=0.05,
        )
        for i in range(10)
    ]
    audit_assembly(large_profiles, "Assembly Large (10 profiles 5000x2048)")
    audit_pipeline(large_profiles[0], "Pipeline Large (5000x2048)")
