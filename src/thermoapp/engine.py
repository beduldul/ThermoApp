"""
ThermoApp Engine — perhitungan termodinamika berbasis CALPHAD (pycalphad).

Modul ini menyediakan tiga inti perhitungan untuk aplikasi:
  1. Kesetimbangan fasa (minimasi energi Gibbs) — setara fungsi Equilib
  2. Termodinamika reaksi — ΔG, ΔH, ΔS vs T untuk suatu reaksi stoikiometri
  3. Diagram fasa biner — plot kurva likuidus/solidus

Sumber data: database CALPHAD format TDB yang dibundel bersama pycalphad
atau disediakan pengguna. Semua perhitungan terbuka dan dapat diverifikasi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pycalphad import Database, calculate, equilibrium, variables as v


# ---------------------------------------------------------------------------
# Basis data yang tersedia (bundled dengan pycalphad)
# ---------------------------------------------------------------------------

AVAILABLE_DATABASES: list[dict[str, str]] = [
    {"id": "alcrni", "file": "alcrni.tdb", "label": "Al-Cr-Ni", "elements": "Al-Cr-Ni"},
    {"id": "alni_dupin", "file": "alni_dupin_2001.tdb", "label": "Al-Ni (Dupin 2001)", "elements": "Al-Ni"},
    {"id": "alcocrni", "file": "alcocrni.tdb", "label": "Al-Co-Cr-Ni", "elements": "Al-Co-Cr-Ni"},
    {"id": "cfe_broshe", "file": "cfe_broshe.tdb", "label": "Fe-C (Broshé)", "elements": "Fe-C"},
    {"id": "femn", "file": "femn.tdb", "label": "Fe-Mn (cair)", "elements": "Fe-Mn"},
    {"id": "Al-Mg_Zhong", "file": "Al-Mg_Zhong.tdb", "label": "Al-Mg (Zhong)", "elements": "Al-Mg"},
    {"id": "cuo", "file": "cuo.tdb", "label": "Cu-O", "elements": "Cu-O"},
    {"id": "pbsn", "file": "pbsn.tdb", "label": "Pb-Sn", "elements": "Pb-Sn"},
    {"id": "crtiv_ghosh", "file": "crtiv_ghosh.tdb", "label": "Cr-Ti-V (Ghosh)", "elements": "Cr-Ti-V"},
    # Sistem biner tambahan (berguna utk praktikum diagram fasa)
    {"id": "alfe", "file": "alfe.tdb", "label": "Al-Fe", "elements": "Al-Fe"},
    {"id": "alfe_sundman", "file": "Al-Fe_sundman2009.tdb", "label": "Al-Fe (Sundman 2009)", "elements": "Al-Fe"},
    {"id": "alzn", "file": "alzn_mey.tdb", "label": "Al-Zn (Mey)", "elements": "Al-Zn"},
    {"id": "cumg", "file": "cumg.tdb", "label": "Cu-Mg", "elements": "Cu-Mg"},
    {"id": "ausn", "file": "AuSn-13Don.tdb", "label": "Au-Sn", "elements": "Au-Sn"},
    {"id": "cov", "file": "CoV-20Wan.tdb", "label": "Co-V (Wan)", "elements": "Co-V"},
]

# Nama lengkap file TDB yang dibundel pycalphad
_TDB_FILES = {
    "alcrni": "alcrni.tdb",
    "alni_dupin": "alni_dupin_2001.tdb",
    "alcocrni": "alcocrni.tdb",
    "cfe_broshe": "cfe_broshe.tdb",
    "femn": "femn.tdb",
    "Al-Mg_Zhong": "Al-Mg_Zhong.tdb",
    "cuo": "cuo.tdb",
    "pbsn": "pbsn.tdb",
    "crtiv_ghosh": "crtiv_ghosh.tdb",
    "alfe": "alfe.tdb",
    "alfe_sundman": "Al-Fe_sundman2009.tdb",
    "alzn": "alzn_mey.tdb",
    "cumg": "cumg.tdb",
    "ausn": "AuSn-13Don.tdb",
    "cov": "CoV-20Wan.tdb",
}

# Elemen yang diabaikan / "vacancy"
_VACANCY = "VA"


def resolve_tdb_path(db_id: str) -> str:
    """Mengembalikan path lengkap ke file TDB untuk id database tertentu."""
    filename = _TDB_FILES[db_id]
    import pycalphad
    from pathlib import Path

    pkg = Path(pycalphad.__file__).parent
    # pycalphad menyimpan TDB contoh di dalam paket
    candidate = pkg / filename
    if candidate.exists():
        return str(candidate)
    # fallback: cari secara rekursif
    for hit in pkg.rglob(filename):
        return str(hit)
    raise FileNotFoundError(f"TDB '{filename}' tidak ditemukan pada instalasi pycalphad")


def load_database(db_id: str) -> tuple[Database, dict[str, Any]]:
    """Memuat database CALPHAD dan mengembalikan (db, meta)."""
    path = resolve_tdb_path(db_id)
    db = Database(path)
    elements = sorted(e for e in db.elements if e != _VACANCY)
    phases = db.phases.keys()
    meta = {
        "id": db_id,
        "file": path,
        "elements": elements,
        "phases": sorted(phases),
    }
    return db, meta


# ---------------------------------------------------------------------------
# Data hasil perhitungan
# ---------------------------------------------------------------------------


@dataclass
class EquilibriumResult:
    temperature: float
    phases: list[str]
    fractions: list[float]
    compositions: dict[str, list[float]]  # phase -> list fraksi tiap elemen (sama urut elemen)
    elements: list[str]
    gm: float | None = None


@dataclass
class ReactionResult:
    temperature: float
    dg: float          # J/mol reaksi
    dh: float          # J/mol reaksi
    ds: float          # J/mol.K
    feasible: bool
    note: str = ""


@dataclass
class BinaryDiagram:
    db_id: str
    comp_1: str
    comp_2: str
    temperatures: list[float]
    t_liq: list[float]    # fraksi fasa cair pada tiap T
    t_sol: list[float]    # batas bawah kestabilan cair (likuidus) — placeholder
    points: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1. Kesetimbangan fasa (minimasi energi Gibbs) melalui pycalphad.equilibrium
# ---------------------------------------------------------------------------


def compute_equilibrium(
    db_id: str,
    composition: dict[str, float],
    temperature: float,
    pressure: float = 101325.0,
) -> EquilibriumResult:
    """
    Menghitung fasa-fasa setimbang pada T, P dan komposisi total tertentu.

    Parameters
    ----------
    db_id       : identitas database (kunci AVAILABLE_DATABASES)
    composition : dict {elemen: fraksi mol} — fraksi harus dijumlahkan ~1
    temperature : suhu dalam Kelvin
    pressure    : tekanan dalam Pa (default 1 atm = 101325 Pa)

    Returns
    -------
    EquilibriumResult berisi fraksi fasa setimbang.
    """
    if not composition:
        raise ValueError("Komposisi tidak boleh kosong")

    db, meta = load_database(db_id)
    db_elements = meta["elements"]            # huruf besar: ['AL','NI',...]
    elem_set = set(db_elements)

    # Normalisasi kunci komposisi ke simbologi elemen database (huruf besar).
    norm_comp: dict[str, float] = {}
    for el, f in composition.items():
        key = el.strip().upper()
        if key in elem_set:
            norm_comp[key] = norm_comp.get(key, 0.0) + float(f)
    if not norm_comp:
        raise ValueError(f"Tidak ada elemen valid dari komposisi {composition} "
                         f"(database {db_id} only has {db_elements})")

    total = sum(norm_comp.values())
    if total <= 0:
        raise ValueError("Fraksi komposisi harus positif.")
    comp = {el: f / total for el, f in norm_comp.items()}

    # Species untuk pycalphad: elemen aktif (huruf besar) + vacancy (VA).
    # Tanpa VA, koordinat 'component' pycalphad tidak terisi penuh dan
    # lower_convex_hull gagal ('X is not in list').
    species = sorted(comp.keys()) + [_VACANCY]

    # Kondisi komposisi: pycalphad membutuhkan kondisi independen.
    # Untuk sistem dengan N elemen aktif, berikan fraksi untuk (N-1) elemen
    # dan biarkan elemen terakhir sebagai dependent (sisanya terhitung via
    # total = 1 mol dengan v.N). Memberikan semua N elemen membuat DOF berlebih.
    conds = {
        v.P: pressure,
        v.T: temperature,
        v.N: 1.0,  # total 1 mol
    }
    active = sorted(comp.keys())
    for el in active[:-1]:
        conds[v.X(el)] = comp[el]

    eq = equilibrium(db, species, meta["phases"], conds)

    # Ekstraksi fasa setimbang. Hasil equilibrium berstruktur xarray dengan
    # dimensi (P, T, N, X..., n_phases). Untuk kondisi tunggal, ambil baris
    # pertama, lalu filter fasa yang aktif (NP tidak nan).
    phase_arr = np.asarray(eq.Phase.values)
    np_arr = np.asarray(eq.NP.values)
    gm_arr = np.asarray(eq.GM.values)

    # Rata-ratakan / ambil titik pertama
    first = tuple(0 for _ in range(phase_arr.ndim - 1))
    phases_slots = phase_arr[first]
    frac_slots = np_arr[first]

    phase_names = []
    fractions = []
    per_vertex: list[tuple[str, float]] = []  # (fasa, fraksi) per vertex
    for ph, frac in zip(phases_slots, frac_slots):
        name = str(ph)
        if name in ("", "nan", "None") or np.isnan(frac):
            continue
        if frac < 1e-9:  # abaikan fase dengan fraksi ~0
            continue
        phase_names.append(name)
        fractions.append(float(frac))
        per_vertex.append((name, float(frac)))

    # Konsolidasi fase duplikat (pycalphad bisa membagi satu fase atas beberapa
    # vertex sublattice). Gabungkan fraksi untuk nama fase yang sama.
    frac_by_name: dict[str, float] = {}
    order: list[str] = []
    for name, frac in zip(phase_names, fractions):
        if name not in frac_by_name:
            frac_by_name[name] = 0.0
            order.append(name)
        frac_by_name[name] += frac
    phase_names = order
    fractions = [frac_by_name[n] for n in order]

    # Komposisi tiap fasa dari eq.X. eq.X memiliki koordinat 'component'
    # (urutan elemen) dan 'vertex' (fasa). Nilai dummy (nan) = fasa tidak aktif.
    # PENTING: satu fase bisa menempati >1 vertex; rata-ratakan komposisinya
    # dengan bobot fraksi agar selaras dengan fraksi terkonsolidasi.
    components = [c for c in eq.X.coords["component"].values
                  if str(c) != _VACANCY]
    comp_values = np.asarray(eq.X.values)  # (N,P,T,..., vertex, component)
    first = tuple(0 for _ in range(comp_values.ndim - 2))
    comp_matrix = comp_values[first]  # (vertex, component)

    # Kolom index untuk tiap elemen aktif (bukan vacancy) pada comp_matrix.
    raw_components = list(eq.X.coords["component"].values)
    keep_idx = [i for i, c in enumerate(raw_components) if str(c) != _VACANCY]

    # Akumulasi komposisi terbobot per nama fasa.
    comp_sum: dict[str, np.ndarray] = {}
    comp_w: dict[str, float] = {}
    for vertex_i, (vname, vfrac) in enumerate(per_vertex):
        row = comp_matrix[vertex_i][keep_idx]   # kolom elemen aktif (tanpa VA)
        w = vfrac
        if vname not in comp_sum:
            comp_sum[vname] = np.zeros(len(components), dtype=float)
            comp_w[vname] = 0.0
        comp_sum[vname] += np.where(np.isnan(row), 0.0, row) * w
        comp_w[vname] += w

    phase_comp: dict[str, list[float]] = {}
    for name in phase_names:
        total = comp_w.get(name, 0.0)
        if total > 0:
            vals = comp_sum[name] / total
        else:
            vals = np.zeros(len(components))
        phase_comp[name] = [round(float(v), 6) if not np.isnan(v) else 0.0
                            for v in np.asarray(vals).ravel()]

    return EquilibriumResult(
        temperature=temperature,
        phases=phase_names,
        fractions=fractions,
        compositions=phase_comp,
        elements=components,
        gm=float(np.ravel(gm_arr)[0]) if gm_arr.size else None,
    )


# ---------------------------------------------------------------------------
# 2. Termodinamika reaksi — ΔG, ΔH, ΔS dari kapasitas panas standar
# ---------------------------------------------------------------------------

# Data referensi termokimia sederhana (J/mol, 298.15 K) untuk senyawa umum.
# Nilai Cp(T) didekati model a + bT + c/T^2  (range 298-2000 K) jika tersedia.
# Sumber: baris data standar NIST / literatur termokimia umum.
#
# Format: name -> {"Hf": ΔHf298 (J/mol), "S": S298 (J/mol.K),
#                  "a","b","c": koefisien cp = a + b*T + c*T^-2 }

# Data termokimia diperkaya dimuat dari modul terpisah thermo_data.py
# (JANAF/NIST/Barin-Kubaschewski) — mencakup oksida, sulfida, klorida,
# karbida, nitrida, karbonat, dsb.
from .thermo_data import THERMO_DATA as _THERMO


@dataclass
class _Specie:
    name: str
    stoich: float


def _parse_species_tokens(tokens: list[str]) -> list[_Specie]:
    """Parse daftar 'koef:name' menjadi list _Specie."""
    out = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            coef, name = tok.split(":", 1)
            coef = float(coef)
        else:
            name = tok
            coef = 1.0
        name = name.strip()
        if name and name not in _THERMO:
            raise ValueError(f"Spesies '{name}' tidak ada dalam basis termokimia bawaan")
        out.append(_Specie(name=name, stoich=coef))
    return out


def _cp(name: str, T: float) -> float:
    d = _THERMO[name]
    return d["a"] + d["b"] * T + d["c"] / (T * T)


def compute_reaction(
    reactants: list[str],
    products: list[str],
    temperature: float,
) -> ReactionResult:
    """
    Menghitung ΔG, ΔH, ΔS untuk reaksi:
        Σ ν_i · R_i  ->  Σ ν_j · P_j

    Menggunakan data termokimia standar (ΔHf298, S298, Cp(T)) dengan
    pendekatan Kirchhoff. Hasil dalam satuan J/mol reaksi.

    Parameters
    ----------
    reactants : list token "koef:spesies" (koef positif = jumlah mol reaktan)
    products  : list token "koef:spesies"
    temperature : suhu reaksi (K)
    """
    T = float(temperature)
    if T <= 0:
        raise ValueError("Suhu harus > 0 K")

    rs = _parse_species_tokens(reactants)
    ps = _parse_species_tokens(products)

    # Koefisien stoikiometri netto: produk bernilai +, reaktan bernilai -
    stoich: dict[str, float] = {}
    for s in ps:
        stoich[s.name] = stoich.get(s.name, 0.0) + s.stoich
    for s in rs:
        stoich[s.name] = stoich.get(s.name, 0.0) - s.stoich

    T0 = 298.15

    # ΔHf298, ΔS298, Δa, Δb, Δc (Hess law)
    dH0 = sum(nu * _THERMO[name]["Hf"] for name, nu in stoich.items())
    dS0 = sum(nu * _THERMO[name]["S"] for name, nu in stoich.items())
    da = sum(nu * _THERMO[name]["a"] for name, nu in stoich.items())
    db = sum(nu * _THERMO[name]["b"] for name, nu in stoich.items())
    dc = sum(nu * _THERMO[name]["c"] for name, nu in stoich.items())

    # Kirchhoff: ΔH(T) = ΔH0 + ∫ΔCp dT ; ΔS(T) = ΔS0 + ∫(ΔCp/T) dT
    # ∫ΔCp dT = da(T-T0) + db/2(T²-T0²) - dc(1/T - 1/T0)
    # ∫(ΔCp/T)dT = da ln(T/T0) + db(T-T0) - dc/2(1/T² - 1/T0²)
    dH = dH0 + da * (T - T0) + 0.5 * db * (T * T - T0 * T0) - dc * (1 / T - 1 / T0)
    dS = dS0 + da * np.log(T / T0) + db * (T - T0) - 0.5 * dc * (1 / (T * T) - 1 / (T0 * T0))
    dG = dH - T * dS

    return ReactionResult(
        temperature=T,
        dg=float(dG),
        dh=float(dH),
        ds=float(dS),
        feasible=bool(dG < 0),
        note=("Reaksi spontan (ΔG < 0)" if dG < 0 else "Reaksi tidak spontan (ΔG > 0)"),
    )


def reaction_species() -> list[str]:
    """Mengembalikan daftar semua spesies termokimia yang tersedia."""
    return sorted(_THERMO.keys())


# ---------------------------------------------------------------------------
# Helper: kurva Gibbs vs T untuk reaksi (dipakai diagram Ellingham dll.)
# ---------------------------------------------------------------------------


def _reaction_thermo_coeffs(reactants: list[str], products: list[str]):
    """Hitung (dH0, dS0, da, db, dc) untuk reaksi (basis per reaksi).

    Koefisien Cp netto (da, db, dc) dan nilai ΔH(298), ΔS(298) dihitung
    sekali, sehingga ΔG(T) dapat dievaluasi cepat pada banyak suhu.
    """
    rs = _parse_species_tokens(reactants)
    ps = _parse_species_tokens(products)

    stoich: dict[str, float] = {}
    for s in ps:
        stoich[s.name] = stoich.get(s.name, 0.0) + s.stoich
    for s in rs:
        stoich[s.name] = stoich.get(s.name, 0.0) - s.stoich

    dH0 = sum(nu * _THERMO[name]["Hf"] for name, nu in stoich.items())
    dS0 = sum(nu * _THERMO[name]["S"] for name, nu in stoich.items())
    da = sum(nu * _THERMO[name]["a"] for name, nu in stoich.items())
    db = sum(nu * _THERMO[name]["b"] for name, nu in stoich.items())
    dc = sum(nu * _THERMO[name]["c"] for name, nu in stoich.items())
    return dH0, dS0, da, db, dc


def _dg_from_coeffs(coeffs, T: float) -> float:
    """Evaluasi ΔG(T) dari koefisien Kirchhoff (dH0, dS0, da, db, dc)."""
    dH0, dS0, da, db, dc = coeffs
    T0 = 298.15
    dH = dH0 + da * (T - T0) + 0.5 * db * (T * T - T0 * T0) - dc * (1 / T - 1 / T0)
    dS = dS0 + da * np.log(T / T0) + db * (T - T0) - 0.5 * dc * (1 / (T * T) - 1 / (T0 * T0))
    return dH - T * dS


def reaction_gibbs_curve(
    reactants: list[str],
    products: list[str],
    temperatures: list[float] | np.ndarray,
) -> list[float]:
    """Kurva ΔG (J/mol reaksi) terhadap suhu untuk reaksi stoikiometri."""
    coeffs = _reaction_thermo_coeffs(reactants, products)
    return [float(_dg_from_coeffs(coeffs, T)) for T in temperatures]


def reaction_coeffs(reactants: list[str], products: list[str]):
    """Expose koefisien termokimia reaksi (untuk UI menampilkan persamaan)."""
    return _reaction_thermo_coeffs(reactants, products)


# ---------------------------------------------------------------------------
# 3. Diagram fasa biner (kurva likuidus) dari database CALPHAD
# ---------------------------------------------------------------------------


def compute_binary_diagram(
    db_id: str,
    comp_1: str,
    comp_2: str,
    t_min: float = 400.0,
    t_max: float = 2000.0,
    n_x: int = 50,
) -> tuple[Any, "BinaryDiagram"]:
    """
    Menghitung diagram fasa biner T-X menggunakan map biner pycalphad
    (ZPF boundary sets) dan mengembalikan (figure matplotlib, metadata).

    Returns
    -------
    (fig, meta) : figure matplotlib berisi kurva fasa, dan dict metadata.
    """
    import matplotlib
    import matplotlib.pyplot as plt

    db, meta_db = load_database(db_id)
    elements = meta_db["elements"]  # huruf besar: ['CO','V',...]

    # Normalisasi huruf: UI mengirim "Co"/"V" tapi simbol TDB adalah "CO"/"V".
    elem_set = {e.upper(): e for e in elements}
    c1 = elem_set.get(comp_1.strip().upper())
    c2 = elem_set.get(comp_2.strip().upper())
    if c1 is None or c2 is None:
        raise ValueError(f"Elemen {comp_1}/{comp_2} tidak ada di database {db_id} "
                         f"(tersedia: {elements})")

    # Komponen: dua elemen yang dipilih + VA (vacancy) jika ada di database
    components = [c1, c2]
    if "VA" in db.elements:
        components.append("VA")

    # T sebagai potensial, X(comp_2) sebagai koordinat komposisi
    t_span = max(t_max - t_min, 10)
    conds = {
        v.P: 101325.0,
        v.N: 1.0,
        v.T: (t_min, t_max, t_span / 40),
        v.X(c2): (0.0, 1.0, 1.0 / n_x),
    }

    from pycalphad.plot.binary import binplot

    try:
        ax = binplot(db, components, meta_db["phases"], conds)
    except Exception:
        # fallback tanpa VA
        ax = binplot(db, [c1, c2], meta_db["phases"], conds)

    from . import plotstyle
    plotstyle.configure_axes(
        ax,
        f"Diagram Fasa Biner {c1}–{c2} ({db_id})",
        f"Fraksi mol {c2}",
        "Temperatur (K)",
    )
    plotstyle.legend_outside(ax.get_figure(), ax, fontsize=8)
    fig = ax.get_figure()

    bd = BinaryDiagram(
        db_id=db_id,
        comp_1=c1,
        comp_2=c2,
        temperatures=[],
        t_liq=[],
        t_sol=[],
    )
    return fig, bd
