#!/usr/bin/env bash
# Build Lappa Linux x64 release binary (PyInstaller onefile)
# Usage: bash scripts/build_release.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="$ROOT/packages/server"
OUT="$ROOT/dist/release"

cd "$SERVER"
python -m pip install -U pip
python -m pip install -e ".[release]"

rm -rf build dist
python -m PyInstaller --noconfirm --clean lappa.spec

mkdir -p "$OUT"
BIN="$SERVER/dist/lappa"
test -f "$BIN"
DEST="$OUT/lappa-linux-x64"
cp "$BIN" "$DEST"
chmod +x "$DEST"

# smoke
"$DEST" version || true
"$DEST" demo || true

echo "OK: $DEST"
ls -lh "$DEST"
