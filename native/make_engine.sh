#!/bin/bash
# =============================================================================
# Bangun engine_runner (binary mandiri Python) dengan PyInstaller.
#
# Hasil: dist/engine_runner — binary relocatable yang mengemas pycalphad,
# numpy, scipy, matplotlib, dan seluruh database TDB.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo "ERROR: venv tidak ditemukan. Jalankan setup_venv.sh dulu."
    exit 1
fi

echo "==> Membangun engine_runner dengan PyInstaller..."
cd "$ROOT"
"$VENV_PY" -m PyInstaller native/engine_runner.spec --noconfirm --clean 2>&1 | \
    grep -E "ERROR|Warning: Library|completed successfully|WARNING: Failed" || true

if [ ! -x "$ROOT/dist/engine_runner" ]; then
    echo "ERROR: build PyInstaller gagal — dist/engine_runner tidak ada."
    exit 1
fi
echo "==> Berhasil: dist/engine_runner ($(du -h "$ROOT/dist/engine_runner" | cut -f1))"
