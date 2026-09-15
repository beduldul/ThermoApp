"""
Diagram TTT (Time-Temperature-Transformation) untuk baja karbon.

Model **pendidikan** berbasis literatur metalurgi (model fenomonologis):

  - Temperatur eutektoid:  A1 = 723 °C (baja hipo-eutektoid & eutektoid)
  - Kurva fasa difusif (perlit / bainit) berbentuk "C" (nose) dihitung
    dengan model Kirkaldy yang disederhanakan:
        t(f) ∝ G(f) · exp(Q/(R·T)) · (ΔT)^-3 ,   ΔT = A1 − T
    Q = energi aktivasi difusi karbon dalam austenit ≈ 179 kJ/mol.
  - Suhu martensit-start (Ms) & finish (Mf) dihitung dengan persamaan
    Andrews (bergantung komposisi %C, %Mn, %Cr, %Mo):
        Ms (K) = 772 − 423·(%C) − 26.5·(%Mn) − 12.1·(%Cr) − 30.0·(%Mo)

CATATAN PENTING: Model ini ditujukan untuk **memahami konsep** (bentuk
kurva-C, nose, pengaruh suhu & komposisi), BUKAN untuk data eksperimen
presisi pabrik. Nilai absolut t bergantung pada model/grade baja.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

R = 8.314  # J/mol.K
Q_DIFF = 179000.0  # J/mol — aktivasi difusi C dalam austenit
A1_C = 723.0  # °C eutektoid


@dataclass
class TTTData:
    """Kurva TTT yang dihitung."""

    temperatures_c: list[float]      # suhu (°C) pada tiap titik
    t_start_s: list[float]           # waktu mulai transformasi difusif (s)
    t_finish_s: list[float]          # waktu selesai transformasi difusif (s)
    ms_c: float                      # martensit start (°C)
    mf_c: float                      # martensit finish (°C)
    steel_label: str


def ms_andrews(pct_c: float, pct_mn: float = 0.5,
               pct_cr: float = 0.0, pct_mo: float = 0.0,
               pct_n: float = 0.0, pct_si: float = 0.0) -> float:
    """Suhu martensit-start (Ms) via persamaan Andrews (*C)."""
    # Andrews: Ms(C) = 539 - 423C - 30.4Mn - 17.7Ni - 12.1Cr - 7.5Mo - 7.5Si
    # (versi umum yang paling banyak dipakai)
    return 539.0 - 423.0 * pct_c - 30.4 * pct_mn - 12.1 * pct_cr \
        - 7.5 * pct_mo - 7.5 * pct_si


def _avrami_time(f: float) -> float:
    """Faktor waktu untuk fraksi transformasi f (model Kirkaldy)."""
    # G(f) sebanding dengan (-ln(1-f))^0.5 (pendekatan Avrami)
    # Dinormalisasi agar f=0.5 -> 1
    import math

    if f <= 0:
        return 0.0
    if f >= 0.999:
        f = 0.999
    g = math.sqrt(-math.log(1 - f))
    g_half = math.sqrt(-math.log(0.5))
    return g / g_half


def compute_ttt(
    pct_c: float = 0.8,
    pct_mn: float = 0.5,
    pct_cr: float = 0.0,
    pct_mo: float = 0.0,
    pct_si: float = 0.1,
    t_min_c: float = 150.0,
    t_max_c: float = A1_C - 1.0,
    n_points: int = 120,
    tau_scale: float = 1.0,
) -> TTTData:
    """
    Menghitung kurva TTT untuk baja karbon.

    Parameters
    ----------
    pct_* : komposisi (wt%).
    tau_scale : faktor skala waktu (1.0 = kalibrasi dasar; naikkan/urutkan
                untuk mendekati grade baja tertentu).
    """
    A1 = A1_C  # °C

    ms = ms_andrews(pct_c, pct_mn, pct_cr, pct_mo, 0.0, pct_si)
    mf = ms - 200.0  # pendekatan: Mf ~ Ms - 200°C (umum pd baja karbon)

    # Hanya dihitung untuk T < A1 (transformasi difusif mengarah ke bawah)
    temps_c = np.linspace(max(t_min_c, 1.0), A1, n_points)

    t_start_s: list[float] = []
    t_finish_s: list[float] = []

    for T_c in temps_c:
        T_k = T_c + 273.15
        dT = A1 - T_c  # undercooling (C)
        if dT <= 0:
            t_start_s.append(float("inf"))
            t_finish_s.append(float("inf"))
            continue

        # Model Kirkaldy (disederhanakan) untuk baja:
        #   t(s) = K * exp(Q/(R*T)) * (dT)^-3  * G(f)
        # K dikalibrasi agar nose ~1-2 detik pada baja eutektoid 0.8%C.
        K = 6.2e-4
        exp_term = np.exp(Q_DIFF / (R * T_k))
        dT_term = dT ** (-3.0)

        t_start_s.append(tau_scale * K * exp_term * dT_term * _avrami_time(0.01))
        t_finish_s.append(tau_scale * K * exp_term * dT_term * _avrami_time(0.99))

    label = f"Baja C {pct_c:.2f}% · Mn {pct_mn:.1f}%"
    return TTTData(
        temperatures_c=[float(x) for x in temps_c],
        t_start_s=t_start_s,
        t_finish_s=t_finish_s,
        ms_c=float(ms),
        mf_c=float(mf),
        steel_label=label,
    )


def plot_ttt(data: TTTData, figsize: tuple[float, float] = (8.0, 7.0)) -> Any:
    """Render diagram TTT (sumbu-x log waktu)."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)

    # Batasi data terhingga (hindari inf pada T dekat A1)
    ts = np.array(data.t_start_s)
    tf = np.array(data.t_finish_s)
    Ts = np.array(data.temperatures_c)
    mask_s = np.isfinite(ts)
    mask_f = np.isfinite(tf)

    ax.semilogx(ts[mask_s], Ts[mask_s], color="#d62728", lw=2.0, label="Start (1%)")
    ax.semilogx(tf[mask_f], Ts[mask_f], color="#1f77b4", lw=2.0, label="Finish (99%)")

    # Garis eutektoid
    ax.axhline(A1_C, color="gray", lw=1.0, ls="--")
    ax.text(1e-3, A1_C + 6, "A1 (723°C)", fontsize=9, color="gray")

    # Garis Ms / Mf
    ax.axhline(data.ms_c, color="purple", lw=1.2, ls=":")
    ax.axhline(data.mf_c, color="purple", lw=1.2, ls=":")
    ax.text(1e-3, data.ms_c + 6, f"Ms ({data.ms_c:.0f}°C)", fontsize=9, color="purple")
    ax.text(1e-3, data.mf_c - 20, f"Mf ({data.mf_c:.0f}°C)", fontsize=9, color="purple")

    # Region label
    mid = 10 ** (0.5 * (np.log10(ts[mask_s].min() + 1e-12) + np.log10(ts[mask_s].max())))
    ax.text(mid, (A1_C + data.ms_c) / 2 + 10, "Perlit (di atas ~550°C)\nBainit (di bawah)",
            fontsize=9, ha="center", va="center", alpha=0.7)
    ax.text(mid, (data.ms_c + data.mf_c) / 2 - 20, "Martensit",
            fontsize=9, ha="center", va="center", color="purple", alpha=0.8)

    ax.set_xlabel("Waktu (detik)")
    ax.set_ylabel("Temperatur (°C)")
    ax.set_title(f"Diagram TTT — {data.steel_label}")
    ax.set_ylim(bottom=max(data.mf_c - 40, 0), top=A1_C + 30)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    return fig
