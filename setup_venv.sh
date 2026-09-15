#!/bin/bash
# =============================================================================
# Siapkan virtual environment dan install dependencies ThermoApp.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Membuat venv di $ROOT/.venv ..."
python3 -m venv "$ROOT/.venv"

echo "==> Install dependencies ..."
"$ROOT/.venv/bin/pip" install --upgrade pip
"$ROOT/.venv/bin/pip" install \
    pycalphad \
    numpy \
    matplotlib \
    streamlit \
    pyinstaller

echo
echo "==> Selesai. Uji:"
echo "   ./.venv/bin/python -c \"import pycalphad; print(pycalphad.__version__)\""
