import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OK = sorted((ROOT / "examples" / "ok").glob("*.sipl"))
BAD = sorted((ROOT / "examples" / "bad").glob("*.sipl"))
