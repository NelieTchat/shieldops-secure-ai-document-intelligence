import os
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "shieldops_test")
os.environ.setdefault("DB_USER", "test-user")
os.environ.setdefault("DB_PASSWORD", "test-password-only")
import sys
from pathlib import Path

# The service uses flat imports (from config import ...), so put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
