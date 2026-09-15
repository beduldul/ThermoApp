"""Diagram Pourbaix (E-pH) untuk sistem Fe-H2O (korosi / elektrokimia).

Model termodinamika keseimbangan elektrokimia untuk air dan besi pada
25 °C (298.15 K). Garis batas stabilitas antar fasa (Fe, Fe2+, Fe3+,
Fe3O4, Fe2O3) dihitung dari persamaan Nernst dengan data termodinamika
standar (sesuai Atlas Pourbaix / pustaka korosi).

CATATAN: model pendidikan fasa-penting; bukan diagram komersial penuh.
Konstanta garis solid (Fe3O4, Fe2O3) diambil dari literatur korosi
standar; nilai dihitung dari ΔG° reaksi pada 298 K.
"""

from __future__ import annotations
from typing import Any
import numpy as np


# Konstanta (298.15 K)
R = 8.314        # J/mol.K
T = 298.15
F = 96485.0      # C/mol
RTF = R * T / F  # 0.05916 V per dekade

# Potensial standar (V vs SHE)
E_Fe2_Fe = -0.440      # Fe2+ + 2e -> Fe
E_Fe3_Fe2 = 0.771      # Fe3+ + e -> Fe2+

# Aktivitas ion besi terlarut (konsentrasi acuan, M) — umum dipakai diagram
# Pourbaix teknis. Sama untuk Fe2+ dan Fe3+.
ACTIVITY = 1e-3


def water_lines(pH):
    """Garis batas air: atas = O2/H2O, bawah = H2O/H2."""
    pH = np.asarray(pH, dtype=float)
    e_o2 = 1.229 - 0.05916 * pH
    e_h2 = 0.0 - 0.05916 * pH
    return e_o2, e_h2


def metal_lines(pH):
    """Garis batas stabilitas besi terlarut (garis horizontal, 25 C)."""
    pH = np.asarray(pH, dtype=float)
    # Fe/Fe2+ : E = E0 + (0.05916/2)*log10(aFe2+)
    e_fe_fe2 = E_Fe2_Fe + (RTF / 2.0) * np.log10(ACTIVITY)
    # Fe2+/Fe3+ : E = E0 (standar, tidak bergantung pH)
    e_fe2_fe3 = E_Fe3_Fe2
    return np.full_like(pH, e_fe_fe2), np.full_like(pH, e_fe2_fe3)


def solid_lines(pH, a=ACTIVITY):
    """Garis batas fasa padat besi-oksida (diagonal, 25 C).

    Reaksi & tetapan (V vs SHE; a = aktivitas ion terlarut):
      - Fe3O4 + 8H+ + 8e- -> 3Fe  + 4H2O   : E = -0.085 - 0.0591 pH
      - 3Fe2+ + 4H2O -> Fe3O4 + 8H+ + 2e-  : E =  0.981 - 0.236 pH
                                                - 0.0886 log10(a)
      - 2Fe2+ + 3H2O -> Fe2O3 + 6H+ + 2e-  : E =  0.728 - 0.177 pH
                                                - 0.0591 log10(a)
      - 2Fe3O4 + H2O -> 3Fe2O3 + 2H+ + 2e- : E =  0.221 - 0.0591 pH
    Nilai tetapan dari literatur korosi (Pourbaix Atlas, 25 C).
    """
    pH = np.asarray(pH, dtype=float)
    loga = np.log10(a)
    e_fe3o4_fe = -0.085 - 0.0591 * pH                      # reduksi Fe3O4 -> Fe
    e_fe2_fe3o4 = 0.981 - 0.236 * pH - 0.0886 * loga       # Fe2+ -> Fe3O4
    e_fe2_fe2o3 = 0.728 - 0.177 * pH - 0.0591 * loga       # Fe2+ -> Fe2O3
    e_fe3o4_fe2o3 = 0.221 - 0.0591 * pH                    # Fe3O4 -> Fe2O3
    return (e_fe3o4_fe, e_fe2_fe3o4, e_fe2_fe2o3, e_fe3o4_fe2o3)


def compute_pourbaix(pH_min=0.0, pH_max=14.0, n=200):
    pH = np.linspace(pH_min, pH_max, n)
    e_o2, e_h2 = water_lines(pH)
    e_fe_fe2, e_fe2_fe3 = metal_lines(pH)
    (e_fe3o4_fe, e_fe2_fe3o4, e_fe2_fe2o3, e_fe3o4_fe2o3) = solid_lines(pH)
    return {
        "pH": pH,
        "e_o2": e_o2,
        "e_h2": e_h2,
        "e_fe_fe2": e_fe_fe2,
        "e_fe2_fe3": e_fe2_fe3,
        "e_fe3o4_fe": e_fe3o4_fe,
        "e_fe2_fe3o4": e_fe2_fe3o4,
        "e_fe2_fe2o3": e_fe2_fe2o3,
        "e_fe3o4_fe2o3": e_fe3o4_fe2o3,
    }


def plot_pourbaix(data, figsize=(8.0, 7.0)):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=figsize)

    pH = np.asarray(data["pH"])
    ax.plot(pH, data["e_o2"], color="blue", lw=1.5, label="O2/H2O (batas air)")
    ax.plot(pH, data["e_h2"], color="blue", lw=1.5, ls="--", label="H2O/H2")

    ax.plot(pH, data["e_fe_fe2"], color="darkred", lw=2.0, label="Fe/Fe2+")
    ax.plot(pH, data["e_fe2_fe3"], color="darkred", lw=2.0, ls="--", label="Fe2+/Fe3+")

    ax.plot(pH, data["e_fe3o4_fe"], color="darkgreen", lw=1.5, ls=":",
            label="Fe3O4/Fe")
    ax.plot(pH, data["e_fe2_fe3o4"], color="orange", lw=1.5,
            label="Fe2+/Fe3O4")
    ax.plot(pH, data["e_fe2_fe2o3"], color="purple", lw=1.5, ls="--",
            label="Fe2+/Fe2O3")
    ax.plot(pH, data["e_fe3o4_fe2o3"], color="brown", lw=1.5, ls=":",
            label="Fe3O4/Fe2O3")

    ax.axhline(0, color="gray", lw=0.6, ls=":")

    ax.set_xlabel("pH")
    ax.set_ylabel("Potensial E (V vs SHE)")
    ax.set_title("Diagram Pourbaix - Fe/H2O (298 K)")
    ax.set_ylim(-1.2, 1.8)
    ax.set_xlim(0, 14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    return fig
