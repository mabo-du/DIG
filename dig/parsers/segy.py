"""SEG-Y format parser (stub)."""

from pathlib import Path


class SEGYFile:
    """SEG-Y format handler.

    SEG-Y is the Society of Exploration Geophysicists interchange
    format, widely used as a universal interoperability standard.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"SEG-Y file not found: {path}")

        self._text_header: str = ""
        self._binary_header: bytes = b""
        self._parse()

    def _parse(self) -> None:
        """Parse the 3200-byte EBCDIC text header and 400-byte binary header."""
        data = self.path.read_bytes()
        if len(data) < 3600:
            raise ValueError("File too small for SEG-Y header")

        # EBCDIC text header (bytes 0-3199)
        try:
            self._text_header = data[:3200].decode("cp037", errors="replace")
        except LookupError:
            self._text_header = data[:3200].decode("latin-1", errors="replace")

        self._binary_header = data[3200:3600]

    @property
    def text_header(self) -> str:
        return self._text_header

    def __repr__(self) -> str:
        return f"SEGYFile(path={self.path.name})"