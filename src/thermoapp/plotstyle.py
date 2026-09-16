"""Gaya plot konsisten bergaya Factsage untuk semua diagram.

Tujuan: tampilan rapi, lengkap, dan terbaca — legend di luar plot (tidak
menutupi kurva), grid lengkap dua sumbu, label tebal di ujung kurva, palet
kontras, judul bergaya. Dipakai oleh ellingham, gibbs, ttt, pourbaix, dan
diagram fasa biner.
"""

from __future__ import annotations
from typing import Any

import matplotlib

matplotlib.use("Agg")


PLOT_COLORS = [
    "#c22b2b",  # merah
    "#2166ac",  # biru tua
    "#2e8b57",  # hijau
    "#e08214",  # oranye
    "#6a3d9a",  # ungu
    "#17becf",  # cyan
    "#a0522d",  # coklat
    "#8c564b",  # coklat tua
    "#bc2fd7",  # magenta
    "#3cb44b",  # hijau terang
    "#f58231",  # oranye terang
    "#911eb4",  # ungu tua
]

# Palet per kategori (Gibbs-T)
CATEGORY_COLORS = {
    "Oksida": "#c22b2b",
    "Karbida": "#2166ac",
    "Nitrida": "#2e8b57",
    "Sulfida": "#e08214",
    "Klorida": "#6a3d9a",
}


def configure_axes(ax: Any, title: str, xlabel: str, ylabel: str, *,
                   xlog: bool = False, y_zero_line: bool = False) -> None:
    """Terapkan gaya sumbu bergaya Factsage ke axes matplotlib."""
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    if xlog:
        ax.set_xscale("log")
    ax.grid(True, which="both", alpha=0.35, lw=0.6, color="#444444")
    ax.tick_params(labelsize=9)
    # Garis tipis di kanan & atas biar seperti frame diagram
    try:
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    except Exception:  # pragma: no cover
        pass
    if y_zero_line:
        ax.axhline(0, color="#666666", lw=0.8, ls=":")


def legend_outside(fig: Any, ax: Any, ncol: int = 1, fontsize: int = 8) -> None:
    """Letakkan legend DI LUAR plot (kanan) supaya tidak menutupi kurva."""
    handles, labels = ax.get_legend_handles_labels()
    if not labels:
        return
    ax.legend(handles, labels, loc="center left", bbox_to_anchor=(1.02, 0.5),
              fontsize=fontsize, ncol=ncol, frameon=True,
              framealpha=0.95, edgecolor="#cccccc")
    fig.tight_layout(rect=(0, 0, 0.82, 1))


def text_color(i: int) -> str:
    """Warna untuk label ke-i (bergulir palet kontras)."""
    return PLOT_COLORS[i % len(PLOT_COLORS)]
