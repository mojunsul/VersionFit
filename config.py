import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
