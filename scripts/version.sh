#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import pathlib, tomllib
p = pathlib.Path("pyproject.toml")
v = tomllib.loads(p.read_text())["project"]["version"]
print(v)
PY
