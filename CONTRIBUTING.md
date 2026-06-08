# Contributing to DIG

First off, thank you for considering contributing to DIG! It's people like you that make open-source archaeological tools a reality.

## Development Setup

DIG uses a hybrid architecture: a Rust backend for high-performance DSP and parsing, and a Python frontend for UI and orchestration.

### Prerequisites
1. **Rust Toolchain**: Install from [rustup.rs](https://rustup.rs/).
2. **Python 3.9+**: We recommend using a virtual environment (`venv`).
3. **Maturin**: Used for building and publishing Rust-based Python packages.

### Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mark/DIG.git
   cd DIG
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
   ```

3. **Install build dependencies:**
   ```bash
   pip install -U pip maturin
   pip install -r requirements-dev.txt # if available, or just install pytest
   ```

4. **Build the Rust backend & install the Python package in editable mode:**
   ```bash
   maturin develop --release
   ```
   *Note: Omit `--release` if you need debug symbols for the Rust core.*

### Running Tests

We use `pytest` for the Python suite and `cargo test` for the Rust core.

```bash
# Run Python tests
pytest dig/tests/

# Run Rust tests
cd dig-core
cargo test
```

## Pull Request Process

1. Ensure any new parsing features include a robust set of tests (especially when handling broken/proprietary binary headers).
2. If changing the `dig-core` DSP pipeline, please add or run benchmarks using `cargo bench` to ensure performance hasn't regressed.
3. Update the `CHANGELOG.md` with your changes.
