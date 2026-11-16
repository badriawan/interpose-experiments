#!/usr/bin/env bash
set -euo pipefail
RUNTIME_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -I -B "$RUNTIME_DIR/simulator_process.py" "$@"
