"""Tests for DIG parsers."""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
from dig.parsers.dzt import DZTFile
from dig.parsers.dt1 import DT1File
from dig.parsers.magnetometry import MagnetometryFile
from dig.parsers.segy import SEGYFile


class TestDZTParser:
    def test_dzt_raises_on_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            DZTFile("/nonexistent/file.dzt")

    def test_dzt_repr(self):
        # Create a minimal synthetic DZT file with valid header
        with tempfile.NamedTemporaryFile(suffix=".dzt", delete=False) as f:
            header = bytearray(1024)
            # Set required header fields (little-endian int16)
            header[0:2] = (1).to_bytes(2, 'little')       # rh_tag
            header[2:4] = (1024).to_bytes(2, 'little')    # rh_data
            header[4:6] = (512).to_bytes(2, 'little')     # rh_nsamp
            header[6:8] = (16).to_bytes(2, 'little')      # rh_bits
            header[52:54] = (1).to_bytes(2, 'little')     # rh_nchan
            data = b"\x00" * (512 * 512 * 2)
            f.write(bytes(header) + data)
            tmp_path = f.name

        try:
            dzt = DZTFile(tmp_path)
            assert "DZTFile" in repr(dzt)
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