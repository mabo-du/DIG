"""Tests for DIG parsers."""

import sys
import os
import math
import struct
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
from dig.parsers.dzt import DZTFile
from dig.parsers.dt1 import DT1File
from dig.parsers.magnetometry import MagnetometryFile
from dig.parsers.segy import SEGYFile


def _make_synthetic_dzt(
    nsamp: int = 512,
    bits: int = 16,
    nchan: int = 1,
    num_traces: int = 100,
    rh_data: int = 1024,
    rhf_range: float = 100.0,
    rhf_sps: float = 50.0,
    rhf_spm: float = 10.0,
    rhf_position: float = 2.0,
) -> bytes:
    """Build a synthetic DZT file with recognizable trace data."""
    header = bytearray(1024)
    header[0:2] = (1).to_bytes(2, 'little')           # rh_tag
    header[2:4] = rh_data.to_bytes(2, 'little', signed=True)  # rh_data
    header[4:6] = nsamp.to_bytes(2, 'little', signed=True)    # rh_nsamp
    header[6:8] = bits.to_bytes(2, 'little', signed=True)     # rh_bits
    header[10:14] = struct.pack('<f', rhf_sps)        # rhf_sps
    header[14:18] = struct.pack('<f', rhf_spm)        # rhf_spm
    header[22:26] = struct.pack('<f', rhf_position)   # rhf_position
    header[26:30] = struct.pack('<f', rhf_range)      # rhf_range
    header[52:54] = nchan.to_bytes(2, 'little', signed=True)  # rh_nchan

    bytes_per_sample = bits // 8
    trace_record_bytes = nsamp * bytes_per_sample * nchan
    trace_data = bytearray(num_traces * trace_record_bytes)

    for t in range(num_traces):
        offset = t * trace_record_bytes
        for s in range(nsamp):
            sample_offset = offset + s * bytes_per_sample
            if bits == 8:
                trace_data[sample_offset] = (t + s) & 0xFF
            elif bits == 16:
                val = (t * 100 + s) & 0xFFFF
                trace_data[sample_offset:sample_offset + 2] = \
                    val.to_bytes(2, 'little')
            elif bits == 32:
                val = (t * 1000 + s) & 0xFFFFFFFF
                trace_data[sample_offset:sample_offset + 4] = \
                    val.to_bytes(4, 'little')

    return bytes(header) + bytes(trace_data)


class TestDZTParser:
    def test_dzt_raises_on_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            DZTFile("/nonexistent/file.dzt")

    def test_dzt_repr(self):
        data = _make_synthetic_dzt()
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            assert "DZTFile" in repr(dzt)
            assert "traces=100" in repr(dzt)
            assert "samples=512" in repr(dzt)
        finally:
            os.unlink(tmp_path)

    def test_dzt_header_metadata(self):
        data = _make_synthetic_dzt(
            nsamp=256, bits=16, nchan=1, num_traces=50,
            rhf_range=80.0, rhf_sps=60.0, rhf_spm=5.0, rhf_position=1.5,
        )
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            assert dzt.num_traces == 50
            assert dzt.samples_per_trace == 256
            assert dzt.bits_per_sample == 16
            assert dzt.channels == 1
            assert dzt.header_offset == 1024
            assert abs(dzt.time_window_ns - 80.0) < 0.01
            assert abs(dzt.traces_per_second - 60.0) < 0.01
            assert abs(dzt.traces_per_meter - 5.0) < 0.01
            assert abs(dzt.time_zero_ns - 1.5) < 0.01
            assert abs(dzt.sample_interval_ns - 80.0 / 256.0) < 0.001
        finally:
            os.unlink(tmp_path)

    def test_dzt_trace_data_values(self):
        """Verify trace data values match the synthetic pattern."""
        data = _make_synthetic_dzt(nsamp=64, bits=16, num_traces=10)
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            traces = dzt.traces
            assert traces.shape == (10, 64)
            assert traces.dtype == np.int16

            # Trace 0, sample 0 should be 0
            assert traces[0, 0] == 0
            # Trace 5, sample 3 should be 5*100 + 3 = 503
            assert traces[5, 3] == 503
            # Trace 9, sample 63 should be 9*100 + 63 = 963
            assert traces[9, 63] == 963
        finally:
            os.unlink(tmp_path)

    def test_dzt_get_trace(self):
        data = _make_synthetic_dzt(nsamp=32, bits=16, num_traces=20)
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            trace = dzt.get_trace(7)
            assert trace.shape == (32,)
            assert trace[0] == 700  # 7 * 100 + 0
            assert trace[15] == 715  # 7 * 100 + 15

            import pytest
            with pytest.raises(IndexError):
                dzt.get_trace(999)
        finally:
            os.unlink(tmp_path)

    def test_dzt_8bit(self):
        data = _make_synthetic_dzt(nsamp=128, bits=8, num_traces=15)
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            assert dzt.bits_per_sample == 8
            assert dzt.num_traces == 15
            assert dzt.samples_per_trace == 128
            assert dzt.traces.dtype == np.uint8
            # Trace 5, sample 3 = (5 + 3) & 0xFF = 8
            assert dzt.traces[5, 3] == 8
        finally:
            os.unlink(tmp_path)

    def test_dzt_32bit(self):
        data = _make_synthetic_dzt(nsamp=64, bits=32, num_traces=8)
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            assert dzt.bits_per_sample == 32
            assert dzt.num_traces == 8
            assert dzt.traces.dtype == np.int32
            # Trace 3, sample 5 = 3 * 1000 + 5 = 3005
            assert dzt.traces[3, 5] == 3005
        finally:
            os.unlink(tmp_path)

    def test_dzt_dzg_sidecar(self):
        """Test explicit DZG sidecar loading."""
        dzt_data = _make_synthetic_dzt(nsamp=64, num_traces=3)
        dzg_content = (
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n"
            "$GPGGA,123520,4807.040,N,01131.010,E,1,08,0.9,546.0,M,46.9,M,,*48\n"
            "$GPGGA,123521,4807.042,N,01131.020,E,1,08,0.9,546.5,M,46.9,M,,*49\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            dzt_path = Path(tmp) / "survey.dzt"
            dzg_path = Path(tmp) / "survey.dzg"
            dzt_path.write_bytes(dzt_data)
            dzg_path.write_text(dzg_content)

            dzt = DZTFile(str(dzt_path), dzg_path=str(dzg_path))
            assert dzt.has_gps
            assert len(dzt.gps_positions) == 3
            assert dzt.gps_positions[0][0] == 0  # trace index
            assert abs(dzt.gps_positions[0][1] - 48.1173) < 0.001  # lat
            assert abs(dzt.gps_positions[0][2] - 11.51667) < 0.001  # lon
            assert abs(dzt.gps_positions[0][3] - 545.4) < 0.01  # alt
            assert "gps=3 fixes" in repr(dzt)

    def test_dzt_dzg_auto_discovery(self):
        """Test automatic DZG sidecar discovery."""
        dzt_data = _make_synthetic_dzt(nsamp=64, num_traces=2)
        dzg_content = (
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n"
            "$GPGGA,123520,4807.040,N,01131.010,E,1,08,0.9,546.0,M,46.9,M,,*48\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            dzt_path = Path(tmp) / "survey.dzt"
            dzg_path = Path(tmp) / "survey.dzg"
            dzt_path.write_bytes(dzt_data)
            dzg_path.write_text(dzg_content)

            # Don't pass dzg_path — should auto-discover
            dzt = DZTFile(str(dzt_path))
            assert dzt.has_gps
            assert len(dzt.gps_positions) == 2

    def test_dzt_no_dzg(self):
        """File without DZG sidecar."""
        data = _make_synthetic_dzt(nsamp=64, num_traces=5)
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            assert not dzt.has_gps
            assert dzt.gps_positions == []
        finally:
            os.unlink(tmp_path)


class TestDT1Parser:
    def test_dt1_raises_on_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            DT1File("/nonexistent/file.dt1")

    def test_dt1_repr(self):
        with tempfile.NamedTemporaryFile(suffix=".dt1", delete=False) as f:
            # Write 128-byte trace header + 1024 bytes of trace data
            header = bytearray(128)
            header[0:4] = (1).to_bytes(4, 'little')  # trace_number
            f.write(bytes(header) + b"\x00" * 1024)
            tmp_path = f.name

        try:
            dt1 = DT1File(tmp_path)
            assert "DT1File" in repr(dt1)
        finally:
            os.unlink(tmp_path)


class TestMagnetometryParser:
    def test_magnetometry_raises_on_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            MagnetometryFile("/nonexistent/file.dat")

    def test_magnetometry_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create .grd file
            grd_content = "ROWS 4\nCOLS 3\nCELL_SIZE 0.5\nZIGZAG true\n"
            grd_path = Path(tmp) / "test.grd"
            grd_path.write_text(grd_content)

            # Create .dat file (4×3 = 12 int16 values)
            values = np.arange(12, dtype=np.int16)
            dat_path = Path(tmp) / "test.dat"
            dat_path.write_bytes(values.tobytes())

            mag = MagnetometryFile(str(dat_path), str(grd_path))
            assert mag.shape == (4, 3)
            assert mag.cell_size == 0.5

            # Check zig-zag reversal
            data = mag.data
            assert data[0, 0] == 0  # row 0 unchanged
            assert data[1, 0] == 5  # row 1 reversed (4,5,3 → 5,4,3)


class TestSEGYParser:
    def test_segy_raises_on_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            SEGYFile("/nonexistent/file.sgy")

    def test_segy_parse(self):
        with tempfile.NamedTemporaryFile(suffix=".sgy", delete=False) as f:
            # Write 3600-byte header
            f.write(b"\x00" * 3600)
            tmp_path = f.name

        try:
            segy = SEGYFile(tmp_path)
            assert "SEGYFile" in repr(segy)
        finally:
            os.unlink(tmp_path)