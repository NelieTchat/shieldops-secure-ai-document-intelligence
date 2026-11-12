import sys
from pathlib import Path

# The agent code lives in src/investigator; put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
