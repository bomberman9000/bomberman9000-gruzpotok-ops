import hashlib
import tempfile
from pathlib import Path

from app.services.ingestion.runner import _file_checksum  # noqa: PLC2701


def test_checksum_stable():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as f:
        f.write("hello")
        p = Path(f.name)
    try:
        a = _file_checksum(p)
        b = _file_checksum(p)
        assert a == b
        assert len(a) == 64
    finally:
        p.unlink(missing_ok=True)


def test_checksum_changes():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.txt"
        p.write_text("a", encoding="utf-8")
        h1 = _file_checksum(p)
        p.write_text("b", encoding="utf-8")
        h2 = _file_checksum(p)
        assert h1 != h2
