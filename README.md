# ThermoApp

Aplikasi termodinamika **open-source** untuk macOS — dibuat untuk kebutuhan
praktikum Metalurgi. Menghitung **kesetimbangan fasa**, **termodinamika reaksi**
(ΔG, ΔH, ΔS), dan **diagram fasa biner** langsung di Mac, tanpa perlu Windows.

Dibangun di atas mesin CALPHAD terbuka [`pycalphad`](https://pycalphad.readthedocs.io),
pustaka yang dipakai luas di riset dan pendidikan termodinamika material.

> **Bukan** tiruan dari software komersial berlisensi (mis. FactSage). Ini adalah
> tool open-source yang sah dan gratis. Database yang dibundel adalah database
> publik/akademik contoh dari pycalphad.

---

## Fitur

| Modul | Fungsi | Analog dengan |
|-------|--------|---------------|
| **Equilib** | Kesetimbangan fasa via minimasi energi Gibbs | modul Equilib |
| **Reaksi** | ΔG, ΔH, ΔS reaksi stoikiometri (koreksi Kirchhoff) | modul Reaktion |
| **Diagram Fasa Biner** | Kurva likuidus/solidus T–X (ZPF boundaries) | modul Phase Diagram |

- Aplikasi **macOS native** (SwiftUI) — jendela, menu, dan tombol khas macOS.
- Mesin perhitungan Python (pycalphad) dibundel sebagai runtime mandiri,
  sehingga **tidak perlu menginstal Python**.
- Bisa didistribusikan sebagai `.dmg` dan di-double-click.

---

## Cara memakai (untuk end user)

### Instal
1. Unduh `ThermoApp.dmg`.
2. Buka DMG (klik dua kali), lalu **seret `ThermoApp.app` ke folder Applications**
   (atau jalankan langsung dari DMG).
3. Saat pertama dibuka, macOS mungkin menampilkan peringatan "app from an
   unidentified developer" karena ditandatangani ad-hoc (tanpa Developer ID):
   - Klik kanan `ThermoApp.app` -> **Open** -> **Open**.
   - atau: System Settings -> Privacy & Security -> "Open Anyway".

### Gunakan
1. **Equilib** — pilih database, atur komposisi & suhu, klik `Hitung Kesetimbangan`.
2. **Reaksi** — isi reaktan & produk (format `koefisien:spesies`), atur suhu, klik `Hitung Reaksi`.
3. **Diagram Fasa** — pilih database & dua elemen, atur rentang suhu, klik `Gambar Diagram Fasa`.

### Contoh cepat
- **Equilib**: database `Al-Ni`, Al=0.5, Ni=0.5, T=1700 K -> fasa `LIQUID`; T=1000 K -> fasa padat.
- **Reaksi**: `FeO(s) + C(s,grafit) -> Fe(s) + CO(g)` @1200 K -> spontan (ΔG < 0).
- **Diagram**: database `Pb-Sn`, elemen Pb & Sn -> kurva eutektik di sekitar 456 K.

---

## Pengembangan (build dari source)

### Prasyarat
- macOS 14+ (arm64 / Apple Silicon)
- Xcode / Xcode Command Line Tools (`swiftc`)
- Python 3.10–3.12

### 1. Siapkan venv
```bash
cd thermoapp
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install pycalphad numpy matplotlib streamlit pyinstaller
```

### 2. Bangun engine mandiri (PyInstaller)
```bash
./native/make_engine.sh        # -> dist/engine_runner (binary Python mandiri)
```

### 3. Bangun aplikasi `.app`
```bash
./native/build.sh              # -> out/ThermoApp.app
```

### 4. Uji
```bash
open out/ThermoApp.app         # jalankan aplikasi
```

### 5. Buat `.dmg`
```bash
./native/make_dmg.sh           # -> out/ThermoApp.dmg
```

---

## Struktur proyek

```
thermoapp/
├── engine_cli.py              # CLI bridge: JSON in / JSON+PNG out
├── engine_runner.py           # entry point PyInstaller
├── src/thermoapp/
│   └── engine.py              # mesin perhitungan (equilibrium, reaksi, diagram)
├── native/
│   ├── ThermoApp/             # source SwiftUI
│   │   ├── EngineBridge.swift # panggil engine Python dari Swift
│   │   ├── Models.swift
│   │   ├── ContentView.swift
│   │   └── Views/             # Home, Equilib, Reaksi, Diagram Fasa
│   ├── engine_runner.spec     # spec PyInstaller
│   ├── build.sh               # build .app
│   ├── make_engine.sh         # build engine mandiri
│   └── make_dmg.sh            # build .dmg
└── out/                       # hasil build (.app, .dmg)
```

---

## Mesin perhitungan

### Kesetimbangan fasa
Menggunakan `pycalphad.equilibrium` — minimasi energi Gibbs global. Input:
komposisi (fraksi mol), suhu (K), tekanan (Pa). Output: fasa setimbang, fraksi,
komposisi tiap fasa, energi Gibbs total.

### Termodinamika reaksi
ΔG(T), ΔH(T), ΔS(T) dihitung dari data termokimia standar (ΔHf, S298, Cp)
dengan koreksi **Kirchhoff**:
- Σνᵢ·Xᵢ -> Σνⱼ·Xⱼ
- ΔH(T)=ΔH₀+∫ΔCp dT ; ΔS(T)=ΔS₀+∫(ΔCp/T)dT ; ΔG=ΔH−TΔS

### Diagram fasa biner
Algoritme **ZPF (Zero Phase Fraction) boundary** dari pycalphad
(`map_binary`) menghasilkan kurva likuidus & solidus akurat, bukan sekadar grid.

---

## Verifikasi

Suite uji menjalankan 5 kasus dengan nilai fisik yang diperiksa:
1. Al-Ni @1700 K -> `LIQUID`
2. Al-Ni @1000 K -> bukan cair
3. `FeO + C -> Fe + CO` @1200 K -> ΔG ≈ **−18.9 kJ** (spontan)
4. `FeO -> Fe + ½O₂` @1200 K -> ΔG > 0 (tidak spontan)
5. Diagram Pb-Sn -> PNG kurva eutektik ter-generate

Semua lulus (5/5).

---

## Database CALPHAD dibundel

| ID | Sistem |
|----|--------|
| `alcrni` | Al-Cr-Ni |
| `alni_dupin` | Al-Ni |
| `alcocrni` | Al-Co-Cr-Ni |
| `cfe_broshe` | Fe-C |
| `femn` | Fe-Mn |
| `Al-Mg_Zhong` | Al-Mg |
| `cuo` | Cu-O |
| `pbsn` | Pb-Sn |
| `crtiv_ghosh` | Cr-Ti-V |

File `.tdb` eksternal dapat dimuat dengan memodifikasi `AVAILABLE_DATABASES`
di `src/thermoapp/engine.py`.

---

## Catatan
- **Bukan clone FactSage.** Untuk kerja produksi/verifikasi yang mensyaratkan
  FactSage asli, gunakan FactSage (Windows) — aplikasi ini adalah alternatif
  open-source yang sah untuk keperluan pembelajaran.
- Satuan: suhu **K**, energi **J**, tekanan **Pa**.
- Database bundled adalah contoh akademik; untuk hasil kuantitatif yang harus
  dipertanggungjawabkan, gunakan database tervalidasi yang sesuai.

## Lisensi
MIT — silakan gunakan, modifikasi, dan bagikan.

---

Dibuat untuk praktikum Metalurgi · open-source di GitHub · berjalan asli di macOS.
