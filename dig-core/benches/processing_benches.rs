use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use dig_core::dsp::{filter::{dewow, bandpass, sec_gain, agc}, migration::kirchhoff_migration};
use ndarray::Array2;

fn bench_filters(c: &mut Criterion) {
    let mut group = c.benchmark_group("dsp_filters");
    
    let sizes = [(100, 512), (1000, 1024), (5000, 2048)];
    
    for &(traces, samples) in &sizes {
        // We benchmark on flat data representing one trace for 1D filters,
        // or a flat dataset representing all data? Actually, the prompts says:
        // "Test at three sizes (100x512, 1000x1024, 5000x2048)"
        // Let's create a flat array of size traces * samples for 1D filters
        // but realistic filtering is per trace.
        // Let's benchmark the 1D filter on a single trace and multiply throughput,
        // or just apply it to the flattened array. Applying to flattened array
        // makes window_size cross traces, which is algorithmically identical to 
        // a single long trace in terms of performance.
        let flat_size = traces * samples;
        let data_1d = vec![1.0f32; flat_size];
        
        // 2D Array for Kirchhoff
        let data_2d = Array2::<f64>::zeros((traces, samples));
        
        let id_str = format!("{}x{}", traces, samples);

        group.bench_with_input(BenchmarkId::new("dewow", &id_str), &data_1d, |b, data| {
            b.iter(|| dewow(black_box(data), 50));
        });

        group.bench_with_input(BenchmarkId::new("bandpass", &id_str), &data_1d, |b, data| {
            b.iter(|| bandpass(black_box(data), 100.0, 10.0, 40.0));
        });

        group.bench_with_input(BenchmarkId::new("sec_gain", &id_str), &data_1d, |b, data| {
            b.iter(|| sec_gain(black_box(data), 100.0, 0.5));
        });

        group.bench_with_input(BenchmarkId::new("agc", &id_str), &data_1d, |b, data| {
            b.iter(|| agc(black_box(data), 50));
        });

        group.bench_with_input(BenchmarkId::new("apply_kirchhoff_migration", &id_str), &data_2d, |b, data| {
            // we use some small aperture for benchmarks
            b.iter(|| kirchhoff_migration(black_box(data.view()), 0.1, 0.1, 0.05, 30));
        });
    }
    
    group.finish();
}

criterion_group!(benches, bench_filters);
criterion_main!(benches);
