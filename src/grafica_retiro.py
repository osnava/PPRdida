"""Gráfica 05: fase de retiro con regla del 4% (riqueza total en pesos de hoy)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from sim_ppr_vs_vuaa import FX

BASE = Path(__file__).resolve().parent.parent   # raíz del proyecto
OUT = BASE / "outputs" / "graficas"
COLOR = {"VUAA mismos aportes": "#2ca02c", "VUAA mismo bolsillo": "#74c476",
         "PPR tope": "#1f77b4", "PPR mitad": "#ff7f0e"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

filas = json.loads((BASE / "outputs" / "resultados_retiro_4pct.json").read_text(encoding="utf-8"))
n = len(filas) // len(FX)

fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
for k, (ax, (_, fx)) in enumerate(zip(axes, FX)):
    grupo = filas[k * n:(k + 1) * n]
    nombres = [d["escenario"].split(" · ")[0] for d in grupo]
    colores = [COLOR[nm.split(" →")[0]] for nm in nombres]
    retiros = [d["neto_hoy"] / 1e6 for d in grupo]
    legados = [(d["legado_hoy"] - d["latente_hoy"]) / 1e6 for d in grupo]
    y = range(len(grupo))
    ax.barh(y, retiros, color=colores, label="Retiros netos 65→95 (pesos de hoy)")
    ax.barh(y, legados, left=retiros, color=colores, alpha=0.45, label="Legado año 70 neto de ISR latente (pesos de hoy)")
    for yi, d, r, l in zip(y, grupo, retiros, legados):
        ax.text(r + l + 0.4, yi, f"\\${r + l:.1f}M\nretiro neto año 1: \\${d['retiro_anio1_neto_hoy'] / 1e3:,.0f}k/año"
                                 f"\nISR fase: \\${d['isr_hoy'] / 1e6:.2f}M", va="center", fontsize=8.5)
    ax.set_yticks(list(y))
    ax.set_yticklabels(nombres, fontsize=9.5)
    ax.set_xlim(0, max(r + l for r, l in zip(retiros, legados)) * 1.75)
    ax.set_title(fx, fontsize=10.5)
    ax.set_xlabel("Millones MXN de 2026")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f} M"))
axes[0].invert_yaxis()   # eje y compartido: invertir una sola vez
axes[1].tick_params(labelleft=False)

fig.suptitle("Fase de retiro con la regla del 4% (65→95 años) · riqueza total en pesos de hoy",
             fontsize=11, fontweight="bold")
fig.tight_layout()
# leyenda de figura después del layout: anclada a un eje, tight_layout la cuenta como parte del panel y los separa
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.5, 0.0),
           ncol=2, frameon=False, fontsize=9)
fig.savefig(OUT / "05_fase_retiro_4pct.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("OK:", OUT / "05_fase_retiro_4pct.png")
