import os
import sys
from pathlib import Path

# Tests use their own secret; the real service refuses to run without one.
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-only-" + "x" * 16)

# The service uses flat imports (from config import ...), so put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
