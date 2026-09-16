"""
ThermoApp Engine CLI — jembatan antara aplikasi SwiftUI native dan mesin
perhitungan Python (pycalphad + modul termodinamika).

Dipanggil oleh aplikasi macOS sebagai subprocess. Protokol:
    engine_cli.py <command> [--flag value ...]

Perintah:
    databases                 -> JSON daftar database CALPHAD
    equilibrium  --db --comp --T [--P]   -> JSON fasa kesetimbangan
    reaction     --reactants --products --T -> JSON dG,dH,dS
    phasediagram --db --A --B --tmin --tmax --nx --out -> tulis PNG
    ellingham    --oxids --reductants --tmin --tmax --out -> tulis PNG
    ttt          --c --mn --cr --mo --si --out -> tulis PNG
    gibbs        --categories --tmin --tmax --out -> tulis PNG
    pourbaix     --out -> tulis PNG

Output komputasi JSON pada stdout. Kode keluar: 0/sukses, 1/arg, 2/error.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import threading
import warnings
from dataclasses import dataclass, field
from pathlib import Path

warnings.filterwarnings("ignore")

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_here / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from thermoapp import engine, ellingham, ttt, gibbs, pourbaix


# Buffer per-perintah (dipakai mode daemon) supaya tiap command menghasilkan
# tepat satu baris JSON di stdout — aman dari output matplotlib/pycalphad lain.
# Thread-local: worker daemon yang berjalan paralel tidak saling menimpa.
_DAEMON_LOCAL = threading.local()


def _emit(data: dict) -> None:
    line = json.dumps(data, ensure_ascii=False)
    buf = getattr(_DAEMON_LOCAL, "buf", None)
    if buf is not None:
        buf.append(line)
    else:
        print(line, flush=True)


def cmd_databases(_args):
    _emit({"databases": engine.AVAILABLE_DATABASES})
    return 0


def cmd_equilibrium(args):
    try:
        comp = json.loads(args.comp)
    except json.JSONDecodeError as e:
        _emit({"error": f"JSON komposisi tidak valid: {e}"}); return 2
    if not isinstance(comp, dict) or not comp:
        _emit({"error": "Komposisi harus objek JSON non-kosong."}); return 2
    try:
        res = engine.compute_equilibrium(args.db, comp, float(args.T),
                                          float(args.P) if args.P else 101325.0)
    except Exception as e:
        _emit({"error": str(e)}); return 2
    comps_out = {ph: {el: c for el, c in zip(res.elements, vals)}
                 for ph, vals in res.compositions.items()}
    _emit({"temperature": res.temperature, "phases": res.phases,
           "fractions": [round(f, 6) for f in res.fractions],
           "compositions": comps_out, "elements": res.elements, "gm": res.gm})
    return 0


def cmd_reaction(args):
    try:
        rs = json.loads(args.reactants); ps = json.loads(args.products)
    except json.JSONDecodeError as e:
        _emit({"error": f"JSON spesies tidak valid: {e}"}); return 2
    try:
        res = engine.compute_reaction(rs, ps, float(args.T))
    except Exception as e:
        _emit({"error": str(e)}); return 2
    _emit({"temperature": res.temperature, "dg": res.dg, "dh": res.dh,
           "ds": res.ds, "feasible": res.feasible, "note": res.note})
    return 0


def _save(fig, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(path), dpi=120, bbox_inches="tight")
    plt.close(fig)
    _emit({"file": str(path), "ok": True})


def cmd_phasediagram(args):
    try:
        fig, _ = engine.compute_binary_diagram(args.db, args.A, args.B,
                                               t_min=float(args.tmin),
                                               t_max=float(args.tmax),
                                               n_x=int(args.nx))
    except Exception as e:
        _emit({"error": str(e)}); return 2
    _save(fig, args.out)
    return 0


def _parse_list(s):
    return json.loads(s) if s else None


def cmd_ellingham(args):
    try:
        oxids = _parse_list(args.oxids)
        reds = _parse_list(args.reductants)
        lines = ellingham.compute_ellingham_lines(oxids, reds,
                                                  t_min=float(args.tmin),
                                                  t_max=float(args.tmax))
        fig = ellingham.plot_ellingham(lines)
    except Exception as e:
        _emit({"error": str(e)}); return 2
    _save(fig, args.out)
    return 0


def cmd_ttt(args):
    try:
        data = ttt.compute_ttt(pct_c=float(args.c), pct_mn=float(args.mn),
                               pct_cr=float(args.cr), pct_mo=float(args.mo),
                               pct_si=float(args.si) if args.si else 0.1)
        fig = ttt.plot_ttt(data)
    except Exception as e:
        _emit({"error": str(e)}); return 2
    _save(fig, args.out)
    return 0


def cmd_gibbs(args):
    try:
        cats = _parse_list(args.categories)
        lines = gibbs.compute_gibbs_curves(categories=cats,
                                           t_min=float(args.tmin),
                                           t_max=float(args.tmax))
        fig = gibbs.plot_gibbs(lines)
    except Exception as e:
        _emit({"error": str(e)}); return 2
    _save(fig, args.out)
    return 0


def cmd_pourbaix(args):
    try:
        data = pourbaix.compute_pourbaix()
        fig = pourbaix.plot_pourbaix(data)
    except Exception as e:
        _emit({"error": str(e)}); return 2
    _save(fig, args.out)
    return 0


def cmd_labels(args):
    _emit({"oxidation": ellingham.oxidation_labels(),
           "reductants": ellingham.reductant_labels(),
           "species": engine.reaction_species()})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ThermoApp engine CLI")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("databases")

    pe = sub.add_parser("equilibrium")
    pe.add_argument("--db", required=True); pe.add_argument("--comp", required=True)
    pe.add_argument("--T", required=True); pe.add_argument("--P", required=False)

    pr = sub.add_parser("reaction")
    pr.add_argument("--reactants", required=True); pr.add_argument("--products", required=True)
    pr.add_argument("--T", required=True)

    pp = sub.add_parser("phasediagram")
    for a in ["--db", "--A", "--B", "--tmin", "--tmax", "--nx", "--out"]:
        pp.add_argument(a, required=True)

    peh = sub.add_parser("ellingham")
    peh.add_argument("--oxids", required=False); peh.add_argument("--reductants", required=False)
    peh.add_argument("--tmin", required=False, default="400")
    peh.add_argument("--tmax", required=False, default="1800")
    peh.add_argument("--out", required=True)

    pt = sub.add_parser("ttt")
    for a in ["--c", "--mn", "--cr", "--mo"]:
        pt.add_argument(a, required=False)
    pt.add_argument("--si", required=False); pt.add_argument("--out", required=True)

    pg = sub.add_parser("gibbs")
    pg.add_argument("--categories", required=False)
    pg.add_argument("--tmin", required=False, default="300")
    pg.add_argument("--tmax", required=False, default="1800")
    pg.add_argument("--out", required=True)

    pb = sub.add_parser("pourbaix")
    pb.add_argument("--out", required=True)

    sub.add_parser("labels")

    return p


_HANDLERS = {
    "databases": cmd_databases, "equilibrium": cmd_equilibrium,
    "reaction": cmd_reaction, "phasediagram": cmd_phasediagram,
    "ellingham": cmd_ellingham, "ttt": cmd_ttt,
    "gibbs": cmd_gibbs, "pourbaix": cmd_pourbaix,
    "labels": cmd_labels,
}


def main() -> int:
    p = build_parser()
    args = p.parse_args()
    return _HANDLERS[args.command](args)


@dataclass
class _DaemonReq:
    req_id: int
    cmd: str
    args: dict
    argv: list


def _convert_args(cmd: str, args: dict) -> list:
    """Ubah {k: v} menjadi argv JSON yang bisa di-parse argparse
    (memakai ulang build_parser sehingga handler/kode tak berubah)."""
    argv = [cmd]
    for k, v in sorted(args.items()):
        key = "--" + k
        if isinstance(v, (list, dict)):
            argv += [key, json.dumps(v, ensure_ascii=False)]
        elif v is not None:
            argv += [key, str(v)]
    return argv


def _run_one(parser, req):
    """Eksekusi satu permintaan; keluarkan satu baris JSON {id, ok, ...}."""
    buf: list[str] = []
    _DAEMON_LOCAL.buf = buf
    try:
        args = parser.parse_args(req.argv)
        _HANDLERS[args.command](args)
    except SystemExit:
        # parse_args gagal (arg required tidak ada) -> balas error
        buf = [json.dumps({"ok": False, "error": "argumen tidak lengkap",
                           "command": req.cmd})]
    except Exception as e:  # noqa: BLE001 — semua error jadi satu baris JSON
        buf = [json.dumps({"ok": False, "error": str(e), "command": req.cmd})]
    finally:
        _DAEMON_LOCAL.buf = None
    body = buf[-1] if buf else json.dumps({"ok": False,
                                           "error": "tidak ada output"})
    # tambahkan id untuk pairing dengan permintaan asal
    payload = json.loads(body)
    payload["id"] = req.req_id
    return json.dumps(payload, ensure_ascii=False)


def run_daemon() -> int:
    """Loop persisten: baca {id, cmd, args} per baris dari stdin dan tulis
    satu baris JSON {id, ok, ...} per permintaan ke stdout.

    Diproses SECARA SINKRON (satu per satu): tiap permintaan dieksekusi
    langsung dan hasilnya dicetak seketika. Tidak memakai ThreadPoolExecutor
    karena (1) balasan tak ter-hydrate sampai baris stdin berikutnya tiba —
    dengan stdin pipe yang TETAP TERBUKA (seperti dari app) loop membaca stdin
    selamanya dan balasan tak pernah keluar => deadlock; (2) matplotlib tidak
    thread-safe (deadlock bila savefig/close dipakai di worker thread).
    CLI memuat pycalphad+matplotlib SEKALI, jadi tetap cepat walau serial.
    """
    parser = build_parser()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"id": None, "ok": False,
                              "error": "JSON tidak valid"}), flush=True)
            continue
        cmd = req.get("command") or req.get("cmd")
        if cmd in ("shutdown", "exit"):
            break
        dreq = _DaemonReq(req_id=req.get("id", 0), cmd=cmd or "",
                          args=req.get("args", {}),
                          argv=_convert_args(cmd or "", req.get("args", {})))
        try:
            print(_run_one(parser, dreq), flush=True)
        except Exception as e:  # noqa: BLE001 — jangan pernah biarkan daemon mati
            print(json.dumps({"id": dreq.req_id, "ok": False,
                              "error": f"daemon: {e}"}), flush=True)
    return 0


if __name__ == "__main__":
    # Mode daemon: `engine_runner --daemon` / `python engine_cli.py --daemon`
    if "--daemon" in sys.argv[1:]:
        try:
            sys.exit(run_daemon())
        except Exception as e:
            print(json.dumps({"error": f"Daemon error: {e}"}), flush=True)
            sys.exit(2)
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"error": f"Internal error: {e}"}))
        sys.exit(2)
