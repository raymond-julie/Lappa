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

# CLI smoke must succeed before an artifact is accepted.
"$DEST" version
"$DEST" demo
rm -rf "$OUT/lappa_data"

(
  cd "$OUT"
  sha256sum lappa-linux-x64 > SHA256SUMS.txt
)

echo "OK: $DEST"
ls -lh "$DEST" "$OUT/SHA256SUMS.txt"
