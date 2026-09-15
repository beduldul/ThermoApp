"""
ThermoApp Engine Runner — entry point yang dibundel PyInstaller menjadi
binary mandiri untuk aplikasi macOS.

Menjalankan fungsionalitas engine_cli dengan argparse. Binary hasil
PyInstaller dapat dipanggil langsung oleh SwiftUI tanpa Python sistem.
"""

import sys
import os
from pathlib import Path

# Saat dibundel PyInstaller, _MEIPASS menunjuk ke folder ekstraksi sementara.
# pastikan paket thermoapp (engine.py) bisa diimpor dari sana.
if getattr(sys, "frozen", False):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
else:
    base = Path(__file__).resolve().parent

sys.path.insert(0, str(base))
sys.path.insert(0, str(base / "src"))

import engine_cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(engine_cli.main())
