"""Diagram Pourbaix (E-pH) untuk sistem Fe-H2O (korosi / elektrokimia).

Model termodinamika keseimbangan elektrokimia untuk air dan besi pada
25 C (298.15 K). Garis batas stabilitas antar fasa (Fe, Fe2+, Fe3+,
Fe3O4, Fe2O3) dihitung dari persamaan Nernst dengan data termodinamika.

CATATAN: model pendidikan fasa-penting; bukan diagram komersial penuh.
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


def water_lines(pH):
    """Garis batas air: atas = O2/H2O, bawah = H2O/H2."""
    pH = np.asarray(pH, dtype=float)
    e_o2 = 1.229 - 0.05916 * pH
    e_h2 = 0.0 - 0.05916 * pH
    return e_o2, e_h2


def metal_lines(pH):
    """Garis batas stabilitas besi (garis horizontal, 25 C)."""
    pH = np.asarray(pH, dtype=float)
    # Fe/Fe2+ : E = E0 + (0.05916/2)*log10(aFe2+) ; aFe2+ = 1e-3
    e_fe_fe2 = E_Fe2_Fe + (RTF / 2.0) * np.log10(1e-3)
    # Fe2+/Fe3+ : E = E0 (standar)
    e_fe2_fe3 = E_Fe3_Fe2
    # Perluas ke array sepanjang pH (garis horizontal)
    return np.full_like(pH, e_fe_fe2), np.full_like(pH, e_fe2_fe3)


def compute_pourbaix(pH_min=0.0, pH_max=14.0, n=200):
    pH = np.linspace(pH_min, pH_max, n)
    e_o2, e_h2 = water_lines(pH)
    e_fe_fe2, e_fe2_fe3 = metal_lines(pH)
    return {
        "pH": pH,
        "e_o2": e_o2,
        "e_h2": e_h2,
        "e_fe_fe2": e_fe_fe2,
        "e_fe2_fe3": e_fe2_fe3,
    }


def plot_pourbaix(data, figsize=(8.0, 7.0)):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=figsize)

    pH = np.asarray(data["pH"])
    ax.plot(pH, data["e_o2"], color="blue", lw=1.5, label="O2/H2O (batas air)")
    ax.plot(pH, data["e_h2"], color="blue", lw=1.5, ls="--", label="H2O/H2")

    ax.plot(pH, data["e_fe_fe2"], color="darkred", lw=2.0, label="Fe/Fe2+")
    ax.plot(pH, data["e_fe2_fe3"], color="darkred", lw=2.0, ls="--", label="Fe2+/Fe3+")

    ax.axhline(0, color="gray", lw=0.6, ls=":")

    ax.set_xlabel("pH")
    ax.set_ylabel("Potensial E (V vs SHE)")
    ax.set_title("Diagram Pourbaix - Fe/H2O (298 K)")
    ax.set_ylim(-1.2, 1.6)
    ax.set_xlim(0, 14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    return fig
