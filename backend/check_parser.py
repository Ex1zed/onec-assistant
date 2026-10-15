import sys
from pathlib import Path

from app.config import CONFIG_SRC
from app.parser import parse_module

root = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_SRC
files = 0
procs = 0
for f in root.rglob("*.bsl"):
    files += 1
    found = list(parse_module(f))
    procs += len(found)
    print(f"{f.relative_to(root).as_posix()}: {[p['name'] for p in found]}")
print(f"files: {files}, procedures: {procs}")
