#!/bin/bash
# =============================================================================
# Build ThermoApp.app untuk macOS (Apple Silicon / Intel).
#
# Prasyarat:
#   - Xcode command line tools / Xcode terinstall (swiftc)
#   - PyInstaller sudah membangun dist/engine_runner (lihat make_engine.sh)
#
# Hasil:
#   out/ThermoApp.app  — aplikasi macOS lengkap yang bisa di-double-click.
# =============================================================================
set -euo pipefail

# Direktori root proyek (thermoapp)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NATIVE="$ROOT/native"
OUT="$ROOT/out"
APP_NAME="ThermoApp"
APP_DIR="$OUT/$APP_NAME.app"

echo "==> Root proyek: $ROOT"

# 1. Periksa engine runner sudah dibangun
ENGINE_BIN="$ROOT/dist/engine_runner"
if [ ! -x "$ENGINE_BIN" ]; then
    echo "ERROR: dist/engine_runner tidak ditemukan. Jalankan make_engine.sh dulu."
    exit 1
fi
echo "==> Engine runner: $ENGINE_BIN ($(du -h "$ENGINE_BIN" | cut -f1))"

# 2. Kompilasi Swift
echo "==> Mengompilasi SwiftUI binary..."
rm -rf "$OUT" && mkdir -p "$OUT"
SWIFT_SOURCES=(
    "$NATIVE/ThermoApp/ThermoAppApp.swift"
    "$NATIVE/ThermoApp/ContentView.swift"
    "$NATIVE/ThermoApp/Models.swift"
    "$NATIVE/ThermoApp/EngineBridge.swift"
    "$NATIVE"/ThermoApp/Views/*.swift
)
swiftc -O -whole-module-optimization \
    -target arm64-apple-macos14.0 \
    -o "$OUT/ThermoApp_bin" \
    "${SWIFT_SOURCES[@]}"
echo "==> Binary Swift selesai."

# 3. Susun struktur bundle .app
echo "==> Menyusun struktur .app..."
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

cp "$OUT/ThermoApp_bin" "$APP_DIR/Contents/MacOS/$APP_NAME"
cp "$NATIVE/Info.plist" "$APP_DIR/Contents/Info.plist"
cp "$ENGINE_BIN" "$APP_DIR/Contents/Resources/engine_runner"
chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"
chmod +x "$APP_DIR/Contents/Resources/engine_runner"

# 4. Tanda tangan ad-hoc (tanpa Developer ID; cukup untuk diinstall lokal)
echo "==> Menandatangani (ad-hoc)..."
codesign --force --deep --sign - "$APP_DIR" 2>/dev/null || \
    codesign --force --sign - "$APP_DIR"

# 5. Bersihkan binary sementara
rm -f "$OUT/ThermoApp_bin"

echo
echo "==> Selesai: $APP_DIR"
echo "   Uji:  open $APP_DIR"
