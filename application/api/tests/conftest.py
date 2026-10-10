import os
import sys
from pathlib import Path

# Tests use their own secrets; the real service refuses to run without them.
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-only-" + "x" * 16)
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token-" + "x" * 30)

# The service uses flat imports (from config import ...), so put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
