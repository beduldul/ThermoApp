"""Plot dG vs T untuk reaksi pembentukan senyawa (stabilitas termodinamika)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
from . import engine


@dataclass
class GibbsLine:
    label: str
    category: str
    temperatures: list
    dg: list


FORMATION_REACTIONS = [
    ("2Fe + O2 -> 2FeO",        "Oksida",  ["2:Fe(s)", "1:O2(g)"], ["2:FeO(s)"]),
    ("2Al + 1.5O2 -> Al2O3",    "Oksida",  ["2:Al(s)", "1.5:O2(g)"], ["1:Al2O3(s)"]),
    ("Si + O2 -> SiO2",         "Oksida",  ["1:Si(s)", "1:O2(g)"], ["1:SiO2(s,quartz)"]),
    ("Ti + O2 -> TiO2",         "Oksida",  ["1:Ti(s)", "1:O2(g)"], ["1:TiO2(s,ru)"]),
    ("2Mg + O2 -> 2MgO",        "Oksida",  ["2:Mg(s)", "1:O2(g)"], ["2:MgO(s)"]),
    ("Ca + 0.5O2 -> CaO",       "Oksida",  ["1:Ca(s)", "0.5:O2(g)"], ["1:CaO(s)"]),
    ("Zn + 0.5O2 -> ZnO",       "Oksida",  ["1:Zn(s)", "0.5:O2(g)"], ["1:ZnO(s)"]),
    ("2Cu + 0.5O2 -> Cu2O",     "Oksida",  ["2:Cu(s)", "0.5:O2(g)"], ["1:Cu2O(s)"]),
    ("2Ni + O2 -> 2NiO",        "Oksida",  ["2:Ni(s)", "1:O2(g)"], ["2:NiO(s)"]),
    ("2Mn + O2 -> 2MnO",        "Oksida",  ["2:Mn(s)", "1:O2(g)"], ["2:MnO(s)"]),
    ("3Fe + C -> Fe3C",         "Karbida", ["3:Fe(s)", "1:C(s,grafit)"], ["1:Fe3C(s)"]),
    ("Si + C -> SiC",           "Karbida", ["1:Si(s)", "1:C(s,grafit)"], ["1:SiC(s)"]),
    ("Ti + C -> TiC",           "Karbida", ["1:Ti(s)", "1:C(s,grafit)"], ["1:TiC(s)"]),
    ("W + C -> WC",             "Karbida", ["1:W(s)", "1:C(s,grafit)"], ["1:WC(s)"]),
    ("3Si + 2N2 -> Si3N4",      "Nitrida", ["3:Si(s)", "2:N2(g)"], ["1:Si3N4(s)"]),
    ("2Al + N2 -> 2AlN",        "Nitrida", ["2:Al(s)", "1:N2(g)"], ["2:AlN(s)"]),
    ("2Ti + N2 -> 2TiN",        "Nitrida", ["2:Ti(s)", "1:N2(g)"], ["2:TiN(s)"]),
    ("Fe + S -> FeS",           "Sulfida", ["1:Fe(s)", "1:S(s)"], ["1:FeS(s)"]),
    ("Fe + S2 -> FeS2",         "Sulfida", ["1:Fe(s)", "1:S2(g)"], ["1:FeS2(s)"]),
    ("2Cu + S -> Cu2S",         "Sulfida", ["2:Cu(s)", "1:S(s)"], ["1:Cu2S(s)"]),
    ("Zn + S -> ZnS",           "Sulfida", ["1:Zn(s)", "1:S(s)"], ["1:ZnS(s,sfal)"]),
    ("Mn + S -> MnS",           "Sulfida", ["1:Mn(s)", "1:S(s)"], ["1:MnS(s)"]),
    ("Na + 0.5Cl2 -> NaCl",     "Klorida", ["1:Na(s)", "0.5:Cl2(g)"], ["1:NaCl(s)"]),
    ("Ca + Cl2 -> CaCl2",       "Klorida", ["1:Ca(s)", "1:Cl2(g)"], ["1:CaCl2(s)"]),
    ("2Al + 3Cl2 -> 2AlCl3",    "Klorida", ["2:Al(s)", "3:Cl2(g)"], ["2:AlCl3(s)"]),
]

CATEGORY_COLORS = {
    "Oksida": "#d62728", "Karbida": "#1f77b4", "Nitrida": "#2ca02c",
    "Sulfida": "#ff7f0e", "Klorida": "#9467bd",
}


def formation_labels():
    return [label for label, _, _, _ in FORMATION_REACTIONS]


def compute_gibbs_curves(labels=None, categories=None, t_min=300.0, t_max=1800.0, n_points=200):
    temps = list(np.linspace(t_min, t_max, n_points))
    out = []
    for label, category, reactants, products in FORMATION_REACTIONS:
        if labels is not None and label not in labels:
            continue
        if categories is not None and category not in categories:
            continue
        dg = engine.reaction_gibbs_curve(reactants, products, temps)
        out.append(GibbsLine(label, category, temps, dg))
    return out


def plot_gibbs(lines, title="Energi Bebas Gibbs vs Temperatur", figsize=(9.0, 7.0)):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=figsize)
    for line in lines:
        color = CATEGORY_COLORS.get(line.category, "#333333")
        ax.plot(line.temperatures, [g / 1000 for g in line.dg], label=line.label, color=color, lw=1.6)
        ax.annotate(line.label.split("->")[-1].strip(),
                    xy=(line.temperatures[-1], line.dg[-1] / 1000),
                    xytext=(6, 0), textcoords="offset points",
                    fontsize=7, color=color, va="center")
    ax.axhline(0, color="gray", lw=0.8, ls=":")
    ax.set_xlabel("Temperatur (K)")
    ax.set_ylabel("dG (kJ / mol senyawa)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    return fig
