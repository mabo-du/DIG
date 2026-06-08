//! Digital Signal Processing routines.
//!
//! SIMD-accelerated implementations of common GPR processing filters.
//! All functions operate on flat f32 slices for zero-copy PyO3 interop.

pub mod filter;
pub mod migration;
