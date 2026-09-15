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

    norm = sum(composition.values())
    comp = {el: f / norm for el, f in composition.items()}

    db, meta = load_database(db_id)
    species = list(comp.keys())

    # Kondisi komposisi: pycalphad membutuhkan kondisi independen.
    # Untuk sistem dengan N elemen aktif, berikan fraksi untuk (N-1) elemen
    # dan biarkan elemen terakhir sebagai dependent (sisanya terhitung via
    # total = 1 mol dengan v.N). Memberikan semua N elemen membuat DOF berlebih.
    conds = {
        v.P: pressure,
        v.T: temperature,
        v.N: 1.0,  # total 1 mol
    }
    active = list(comp.keys())
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
    for ph, frac in zip(phases_slots, frac_slots):
        name = str(ph)
        if name in ("", "nan", "None") or np.isnan(frac):
            continue
        if frac < 1e-9:  # abaikan fase dengan fraksi ~0
            continue
        phase_names.append(name)
        fractions.append(float(frac))

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
    components = list(eq.X.coords["component"].values)
    comp_values = np.asarray(eq.X.values)  # (N,P,T,..., vertex, component)
    # ambil potongan pertama (kondisi tunggal) -> (vertex, component)
    first = tuple(0 for _ in range(comp_values.ndim - 2))
    comp_matrix = comp_values[first]  # (vertex, component)

    phase_comp: dict[str, list[float]] = {}
    for idx, name in enumerate(frac_by_name.keys()):
        comps_ph = []
        for ci, el in enumerate(components):
            val = comp_matrix[idx, ci]
            comps_ph.append(round(float(val), 6) if not np.isnan(val) else 0.0)
        phase_comp[name] = comps_ph

    return EquilibriumResult(
        temperature=temperature,
        phases=phase_names,
        fractions=fractions,
        compositions=phase_comp,
        elements=species,
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

_THERMO = {
    # Zat sederhana (elemen) — Hf=0, data Cp dari JANAF/NIST
    "Fe(s)":       {"Hf": 0.0,       "S": 27.28, "a": 17.49,   "b": 0.024452,  "c": 0.0},
    "Fe(l)":       {"Hf": 13808.0,   "S": 34.04, "a": 41.84,   "b": 0.0,       "c": 0.0},
    "O2(g)":       {"Hf": 0.0,       "S": 205.15, "a": 29.53,  "b": 0.0089,    "c": -1.9e5},
    "Al(s)":       {"Hf": 0.0,       "S": 28.30, "a": 20.67,   "b": 0.012388,  "c": 0.0},
    "Al(l)":       {"Hf": 10713.0,   "S": 38.49, "a": 31.75,   "b": 0.0,       "c": 0.0},
    "C(s,grafit)": {"Hf": 0.0,       "S": 5.74,  "a": 17.17,   "b": 0.00427,   "c": -8.8e4},
    "Ti(s)":       {"Hf": 0.0,       "S": 30.72, "a": 22.01,   "b": 0.010038,  "c": 0.0},
    "Si(s)":       {"Hf": 0.0,       "S": 18.83, "a": 22.82,   "b": 0.003856,  "c": -3.5e5},
    "Cu(s)":       {"Hf": 0.0,       "S": 33.15, "a": 22.64,   "b": 0.005351,  "c": 0.0},
    "Ni(s)":       {"Hf": 0.0,       "S": 29.87, "a": 16.99,   "b": 0.02946,   "c": 0.0},
    "Mg(s)":       {"Hf": 0.0,       "S": 32.68, "a": 22.30,   "b": 0.01025,   "c": -0.43e5},
    "Zn(s)":       {"Hf": 0.0,       "S": 41.63, "a": 22.38,   "b": 0.010038,  "c": 0.0},
    "CO2(g)":      {"Hf": -393509.0, "S": 213.79, "a": 44.14,  "b": 0.00904,   "c": -8.5e5},
    "CO(g)":       {"Hf": -110525.0, "S": 197.66, "a": 28.41,  "b": 0.00410,   "c": 0.0},
    "H2(g)":       {"Hf": 0.0,       "S": 130.68, "a": 28.84,  "b": 0.00076,   "c": 0.0},
    "H2O(g)":      {"Hf": -241818.0, "S": 188.83, "a": 30.09,  "b": 0.01072,   "c": 0.0},
    "H2O(l)":      {"Hf": -285830.0, "S": 69.95,  "a": 75.29,  "b": 0.0,       "c": 0.0},
    "N2(g)":       {"Hf": 0.0,       "S": 191.61, "a": 28.90,  "b": 0.00164,   "c": 0.0},
    "NH3(g)":      {"Hf": -46110.0,  "S": 192.45, "a": 29.75,  "b": 0.02511,   "c": -1.5e6},
    "Cl2(g)":      {"Hf": 0.0,       "S": 223.08, "a": 36.90,  "b": 0.00025,   "c": -2.8e5},
    "NaCl(s)":     {"Hf": -411153.0, "S": 72.11,  "a": 50.71,  "b": 0.01674,   "c": 0.0},
    "CaCO3(s)":    {"Hf": -1206920.0,"S": 92.90,  "a": 82.34,  "b": 0.04986,   "c": -1.0e6},
    "CaO(s)":      {"Hf": -635090.0, "S": 38.07,  "a": 49.62,  "b": 0.00452,   "c": -6.9e5},
    "CaCl2(s)":    {"Hf": -795790.0, "S": 104.60, "a": 71.88,  "b": 0.01364,   "c": 0.0},
    "SiO2(s,quartz)":{"Hf": -910700.0,"S": 41.46, "a": 44.60,  "b": 0.00778,   "c": -1.1e6},
    "FeO(s)":      {"Hf": -272044.0, "S": 60.75,  "a": 50.15,  "b": 0.00862,   "c": 0.0},
    "Fe2O3(s)":    {"Hf": -824248.0, "S": 87.40,  "a": 98.28,  "b": 0.07778,   "c": -1.4e6},
    "Fe3O4(s)":    {"Hf": -1118384.0,"S": 146.1,  "a": 160.14, "b": 0.01716,   "c": 0.0},
    "Al2O3(s)":    {"Hf": -1675690.0,"S": 50.92,  "a": 114.77, "b": 0.01280,   "c": -3.5e6},
    "TiO2(s,ru)":  {"Hf": -944747.0, "S": 50.62,  "a": 73.35,  "b": 0.00332,   "c": -1.7e6},
    "MgO(s)":      {"Hf": -601241.0, "S": 26.85,  "a": 42.26,  "b": 0.00739,   "c": -6.2e5},
    "CuO(s)":      {"Hf": -155850.0, "S": 42.59,  "a": 42.84,  "b": 0.00877,   "c": -1.4e6},
    "Cu2O(s)":     {"Hf": -170707.0, "S": 92.93,  "a": 72.38,  "b": 0.02316,   "c": 0.0},
    "ZnO(s)":      {"Hf": -350460.0, "S": 43.65,  "a": 49.00,  "b": 0.00532,   "c": -9.0e5},
    "FeS(s)":      {"Hf": -100416.0, "S": 60.29,  "a": 50.21,  "b": 0.02929,   "c": 0.0},
}


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
    elements = meta_db["elements"]
    if comp_1 not in elements or comp_2 not in elements:
        raise ValueError(f"Elemen {comp_1}/{comp_2} tidak ada di database {db_id}")

    # Komponen: dua elemen yang dipilih + VA (vacancy) jika ada di database
    components = [comp_1, comp_2]
    if "VA" in db.elements:
        components.append("VA")

    # T sebagai potensial, X(comp_2) sebagai koordinat komposisi
    t_span = max(t_max - t_min, 10)
    conds = {
        v.P: 101325.0,
        v.N: 1.0,
        v.T: (t_min, t_max, t_span / 40),
        v.X(comp_2): (0.0, 1.0, 1.0 / n_x),
    }

    from pycalphad.plot.binary import binplot

    try:
        ax = binplot(db, components, meta_db["phases"], conds)
    except Exception:
        # fallback tanpa VA
        ax = binplot(db, [comp_1, comp_2], meta_db["phases"], conds)

    ax.set_xlabel(f"Fraksi mol {comp_2}")
    ax.set_ylabel("Temperatur (K)")
    ax.set_title(f"Diagram Fasa Biner {comp_1}–{comp_2} ({db_id})")
    fig = ax.get_figure()

    bd = BinaryDiagram(
        db_id=db_id,
        comp_1=comp_1,
        comp_2=comp_2,
        temperatures=[],
        t_liq=[],
        t_sol=[],
    )
    return fig, bd
