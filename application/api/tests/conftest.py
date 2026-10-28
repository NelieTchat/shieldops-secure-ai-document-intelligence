import os
import sys
from pathlib import Path

# Tests use their own secrets; the real service refuses to run without them.
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-only-" + "x" * 16)
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token-" + "x" * 30)
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "shieldops_test")
os.environ.setdefault("DB_USER", "test-user")
os.environ.setdefault("DB_PASSWORD", "test-password-only")
os.environ.setdefault("REGISTRATION_ENABLED", "true")

# The service uses flat imports (from config import ...), so put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_login_throttle():
    from routes import auth_routes
    auth_routes.reset_login_throttle()
    yield
