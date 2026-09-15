#!/bin/bash
# =============================================================================
# Bangun ThermoApp.dmg — image distribusi yang bisa di-install teman-teman.
#
# DMG berisi ThermoApp.app + petunjuk singkat. Dibuat dengan hdiutil
# (built-in macOS), tanpa dependensi tambahan.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/out"
APP_DIR="$OUT/ThermoApp.app"
DMG="$OUT/ThermoApp.dmg"

if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: $APP_DIR tidak ada. Jalankan build.sh dulu."
    exit 1
fi

STAGING="$OUT/dmg_staging"
echo "==> Menyiapkan staging DMG..."
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP_DIR" "$STAGING/ThermoApp.app"

# Bekerja di direktori staging agar jalur relatif benar
echo "==> Membuat ThermoApp.dmg..."
hdiutil create \
    -volname "ThermoApp" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDZO \
    "$DMG" >/dev/null

rm -rf "$STAGING"

echo
echo "==> Selesai: $DMG ($(du -h "$DMG" | cut -f1))"
echo "   Uji:  open $DMG"
