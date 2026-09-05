import sys
from pathlib import Path

# Allow `from app...` imports whether pytest runs from backend/ or the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
