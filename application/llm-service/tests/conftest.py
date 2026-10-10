import os
import sys
from pathlib import Path

# Tests use their own internal token; the real service answers 503 without one.
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token-" + "x" * 30)

# The service uses flat imports (from config import ...), so put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
