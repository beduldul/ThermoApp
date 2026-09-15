"""
ThermoApp Engine CLI — jembatan antara aplikasi SwiftUI native dan mesin
perhitungan Python (pycalphad).

Dipanggil oleh aplikasi macOS sebagai subprocess. Protokol:
    engine_cli.py <command> [--flag value ...]

Perintah:
    databases
        Mengembalikan daftar database CALPHAD yang tersedia (JSON).

    equilibrium --db ID --comp '{"AL":0.5,"NI":0.5}' --T 1500 [--P 101325]
        Menghitung kesetimbangan fasa. Mengembalikan JSON: {phases, fractions,
        compositions, elements, gm}.

    reaction --reactants '["1:FeO(s)","1:C(s,grafit)"]'
              --products '["1:Fe(s)","1:CO(g)"]' --T 1200
        Menghitung ΔG, ΔH, ΔS reaksi. Mengembalikan JSON.

    phasediagram --db ID --A AL --B NI --tmin 300 --tmax 2000 --nx 50 --out FILE.png
        Menghitung diagram fasa biner dan menulis PNG ke --out.

Semua output computasi berupa JSON valid pada stdout (baris terakhir).

Kode keluar: 0 sukses, 1 argumen salah, 2 error perhitungan.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Pastikan paket thermoapp dapat diimpor (relatif terhadap file ini)
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_here / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from thermoapp import engine


def _emit(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def cmd_databases(_args):
    _emit({"databases": engine.AVAILABLE_DATABASES})
    return 0


def cmd_equilibrium(args):
    try:
        comp = json.loads(args.comp)
    except json.JSONDecodeError as e:
        _emit({"error": f"JSON komposisi tidak valid: {e}"})
        return 2
    if not isinstance(comp, dict) or not comp:
        _emit({"error": "Komposisi harus berupa objek JSON non-kosong."})
        return 2
    try:
        res = engine.compute_equilibrium(
            args.db, comp, float(args.T), float(args.P) if args.P else 101325.0
        )
    except Exception as e:
        _emit({"error": str(e)})
        return 2

    comps_out = {}
    for ph, vals in res.compositions.items():
        comps_out[ph] = {el: c for el, c in zip(res.elements, vals)}

    _emit(
        {
            "temperature": res.temperature,
            "phases": res.phases,
            "fractions": [round(f, 6) for f in res.fractions],
            "compositions": comps_out,
            "elements": res.elements,
            "gm": res.gm,
        }
    )
    return 0


def cmd_reaction(args):
    try:
        reactants = json.loads(args.reactants)
        products = json.loads(args.products)
    except json.JSONDecodeError as e:
        _emit({"error": f"JSON daftar spesies tidak valid: {e}"})
        return 2
    try:
        res = engine.compute_reaction(reactants, products, float(args.T))
    except Exception as e:
        _emit({"error": str(e)})
        return 2
    _emit(
        {
            "temperature": res.temperature,
            "dg": res.dg,
            "dh": res.dh,
            "ds": res.ds,
            "feasible": res.feasible,
            "note": res.note,
        }
    )
    return 0


def cmd_phasediagram(args):
    out_path = Path(args.out)
    try:
        fig, _bd = engine.compute_binary_diagram(
            args.db,
            args.A,
            args.B,
            t_min=float(args.tmin),
            t_max=float(args.tmax),
            n_x=int(args.nx),
        )
    except Exception as e:
        _emit({"error": str(e)})
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=120, bbox_inches="tight")
    plt.close(fig)
    _emit({"file": str(out_path), "ok": True})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ThermoApp engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("databases")

    p_eq = sub.add_parser("equilibrium")
    p_eq.add_argument("--db", required=True)
    p_eq.add_argument("--comp", required=True)
    p_eq.add_argument("--T", required=True)
    p_eq.add_argument("--P", required=False)

    p_rx = sub.add_parser("reaction")
    p_rx.add_argument("--reactants", required=True)
    p_rx.add_argument("--products", required=True)
    p_rx.add_argument("--T", required=True)

    p_pd = sub.add_parser("phasediagram")
    p_pd.add_argument("--db", required=True)
    p_pd.add_argument("--A", required=True)
    p_pd.add_argument("--B", required=True)
    p_pd.add_argument("--tmin", required=True)
    p_pd.add_argument("--tmax", required=True)
    p_pd.add_argument("--nx", required=True)
    p_pd.add_argument("--out", required=True)

    args = parser.parse_args()
    handlers = {
        "databases": cmd_databases,
        "equilibrium": cmd_equilibrium,
        "reaction": cmd_reaction,
        "phasediagram": cmd_phasediagram,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": f"Internal error: {e}"}))
        sys.exit(2)
