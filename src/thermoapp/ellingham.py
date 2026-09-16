"""
Diagram Ellingham — ΔG° vs T untuk reaksi oksidasi logam (per mol O₂).

Setiap reaksi dinyatakan sebagai:  (2x/y)·M + O₂ → (2/y)·MₓO_y
dengan ΔG° per mol O₂. Semakin negatif (semakin rendah garis), semakin
stabil oksidanya dan semakin kuat reduktor logamnya.

Garis reduktor karbon:
    C + O₂ → CO₂      (memotong menurun/landai)
    2C + O₂ → 2CO     (ΔG menurun dengan T — penting di metalurgi ekstraksi)
Garis reduktor hidrogen:
    2H₂ + O₂ → 2H₂O

Kegunaan praktis: suhu di mana garis 2C+O₂→2CO berada DI BAWAH garis
oksida tertentu = suhu di mana karbon dapat mereduksi oksida tersebut.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from . import engine

# Reaksi oksidasi standar: (label, reaktan, produk) — per 1 mol O2.
# Koefisien dibulatkan ke pecahan yang paling sederhana.
OXIDATION_REACTIONS: list[tuple[str, list[str], list[str]]] = [
    # (nama logam, reaktan, produk)
    ("4/3Fe → 2/3Fe₂O₃",  ["1.3333:Fe(s)", "1:O2(g)"], ["0.6667:Fe2O3(s)"]),
    ("3/2Fe → 1/2Fe₃O₄",  ["1.5:Fe(s)", "1:O2(g)"], ["0.5:Fe3O4(s)"]),
    ("2Fe → 2FeO",        ["2:Fe(s)", "1:O2(g)"], ["2:FeO(s)"]),
    ("4/3Al → 2/3Al₂O₃",  ["1.3333:Al(s)", "1:O2(g)"], ["0.6667:Al2O3(s)"]),
    ("Si → SiO₂",         ["1:Si(s)", "1:O2(g)"], ["1:SiO2(s,quartz)"]),
    ("Ti → TiO₂",         ["1:Ti(s)", "1:O2(g)"], ["1:TiO2(s,ru)"]),
    ("2Mg → 2MgO",        ["2:Mg(s)", "1:O2(g)"], ["2:MgO(s)"]),
    ("2Ca → 2CaO",        ["2:Ca(s)", "1:O2(g)"], ["2:CaO(s)"]),
    ("2Mn → 2MnO",        ["2:Mn(s)", "1:O2(g)"], ["2:MnO(s)"]),
    ("4/3Cr → 2/3Cr₂O₃",  ["1.3333:Cr(s)", "1:O2(g)"], ["0.6667:Cr2O3(s)"]),
    ("4/3V → 2/3V₂O₃",    ["1.3333:V(s)", "1:O2(g)"], ["0.6667:V2O3(s)"]),
    ("Mo → MoO₃",         ["1:Mo(s)", "1:O2(g)"], ["1:MoO3(s)"]),
    ("W → WO₃",           ["1:W(s)", "1:O2(g)"], ["1:WO3(s)"]),
    ("2Co → 2CoO",        ["2:Co(s)", "1:O2(g)"], ["2:CoO(s)"]),
    ("2Ni → 2NiO",        ["2:Ni(s)", "1:O2(g)"], ["2:NiO(s)"]),
    ("Sn → SnO₂",         ["1:Sn(s)", "1:O2(g)"], ["1:SnO2(s)"]),
    ("2Pb → 2PbO",        ["2:Pb(s)", "1:O2(g)"], ["2:PbO(s,red)"]),
    ("2Zn → 2ZnO",        ["2:Zn(s)", "1:O2(g)"], ["2:ZnO(s)"]),
    ("4Cu → 2Cu₂O",       ["4:Cu(s)", "1:O2(g)"], ["2:Cu2O(s)"]),
]

# Garis reduktor (opsional, ditampilkan tersendiri).
REDUCTANT_REACTIONS: dict[str, tuple[list[str], list[str]]] = {
    "C → CO₂":   (["1:C(s,grafit)", "1:O2(g)"], ["1:CO2(g)"]),
    "2C → 2CO":  (["2:C(s,grafit)", "1:O2(g)"], ["2:CO(g)"]),
    "2H₂ → 2H₂O": (["2:H2(g)", "1:O2(g)"], ["2:H2O(g)"]),
}

@dataclass
class EllinghamLine:
    label: str
    temperatures: list[float]
    dg: list[float]  # J per mol O2
    is_reductant: bool = False


def oxidation_labels() -> list[str]:
    """Label reaksi oksidasi yang tersedia (untuk UI)."""
    return [label for label, _, _ in OXIDATION_REACTIONS]


def reductant_labels() -> list[str]:
    return list(REDUCTANT_REACTIONS.keys())


def compute_ellingham_lines(
    oxidation: list[str] | None = None,
    reductants: list[str] | None = None,
    t_min: float = 300.0,
    t_max: float = 2000.0,
    n_points: int = 200,
) -> list[EllinghamLine]:
    """Hitung kurva ΔG vs T untuk reaksi oksidasi & reduktor terpilih.

    Parameters
    ----------
    oxidation : label oksidasi yang digambar (None = semua)
    reductants : label reduktor yang digambar (None = C→CO dan 2C→2CO)

    Returns
    -------
    list[EllinghamLine]
    """
    if oxidation is None:
        oxidation = [label for label, _, _ in OXIDATION_REACTIONS]
    if reductants is None:
        reductants = ["C → CO₂", "2C → 2CO"]

    temps = list(np.linspace(t_min, t_max, n_points))
    lines: list[EllinghamLine] = []

    for label, reactants, products in OXIDATION_REACTIONS:
        if label not in oxidation:
            continue
        dg = engine.reaction_gibbs_curve(reactants, products, temps)
        lines.append(EllinghamLine(label, temps, dg, is_reductant=False))

    for label in reductants:
        if label not in REDUCTANT_REACTIONS:
            continue
        reactants, products = REDUCTANT_REACTIONS[label]
        dg = engine.reaction_gibbs_curve(reactants, products, temps)
        lines.append(EllinghamLine(label, temps, dg, is_reductant=True))

    return lines


def plot_ellingham(
    lines: list[EllinghamLine],
    title: str = "Diagram Ellingham",
    figsize: tuple[float, float] = (9.5, 7.0),
) -> Any:
    """Render diagram Ellingham menjadi figure matplotlib.

    Gaya Factsage: oksida = garis padat berwarna (palet kontras), reduktor =
    garis putus-putus tebal. Legend ditaruh DI LUAR plot agar tidak menutupi
    kurva; label produk diberikan di ujung garis.
    """
    from . import plotstyle
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    ox_idx = 0
    for line in lines:
        if line.is_reductant:
            color = "#c22b2b" if line.label.startswith("C") else "#2166ac"
            lw = 3.0
            ls = "--"
        else:
            color = plotstyle.text_color(ox_idx)
            ox_idx += 1
            lw = 1.8
            ls = "-"
        ax.plot(line.temperatures, [g / 1000 for g in line.dg],
                label=line.label, color=color, lw=lw, ls=ls, zorder=3)
        # Anotasi label di ujung kanan garis (tebal, ringkas)
        end_dg = line.dg[-1] / 1000
        ax.annotate(line.label,
                    xy=(line.temperatures[-1], end_dg),
                    xytext=(7, 0), textcoords="offset points",
                    fontsize=8.5, color=color, va="center", fontweight="bold")

    plotstyle.configure_axes(
        ax, title,
        "Temperatur (K)",
        "ΔG° (kJ / mol O₂)",
        y_zero_line=True,
    )
    ax.set_xlim(left=min(l.temperatures[0] for l in lines))
    plotstyle.legend_outside(fig, ax, fontsize=8)
    return fig
