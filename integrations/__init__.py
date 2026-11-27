"""Top-level integration layer (mirrors backend adapters)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

try:
    from app.integrations.adapters import ADAPTERS, catalog
except Exception:
    ADAPTERS = {}

    def catalog():
        return []
