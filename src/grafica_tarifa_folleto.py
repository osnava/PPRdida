"""Gráfica 07: efecto de las tarifas publicadas en el folleto Allianz 2025.

Usa los mismos supuestos de resultados_tarifa_folleto.json: 5,000 MXN/mes,
40 años, 10% nominal USD, inflación 4%, IVA 16% supuesto sobre los cargos y
tarifa ISR 2026 congelada. Solo cambian las tres tarifas del PPR; se conserva
la generación del bono durante el plazo interpretada de CG 3.6.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

BASE = Path(__file__).resolve().parent.parent
RESULTADOS = BASE / "outputs" / "resultados_tarifa_folleto.json"
SALIDA = BASE / "outputs" / "graficas" / "07_tarifa_folleto.png"

datos = json.loads(RESULTADOS.read_text(encoding="utf-8"))["escenarios"]
filas = [
    ("PPR · tope contractual", "ppr_tope_neto", "#1f77b4"),
    ("PPR · folleto 2025", "ppr_folleto_neto", "#17becf"),
    ("PPR · mitad hipotética", "ppr_mitad_neto", "#ff7f0e"),
    ("VUAA · mismo bolsillo", "vuaa_mismo_bolsillo_neto", "#74c476"),
]
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))

for ax, (fx, caso) in zip(axes, datos.items()):
    y = np.arange(len(filas))
    valores = [caso[clave] / 1e6 for _, clave, _ in filas]
    ax.barh(y, valores, color=[color for _, _, color in filas], height=0.62)
    for yi, valor in zip(y, valores):
        ax.text(valor + 0.35, yi, f"\\${valor:.2f}M", va="center",
                fontsize=10, fontweight="bold")
    ax.set_yticks(y, [nombre for nombre, _, _ in filas])
    ax.invert_yaxis()
    ax.set_xlim(0, max(valores) * 1.23)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f} M"))
    ax.set_xlabel("Millones de MXN nominales al año 40")
    mejora = caso["mejora_folleto_vs_tope"] / 1e6
    ax.set_title(f"{fx.capitalize()}\nFolleto frente al tope: +\\${mejora:.2f}M",
                 fontsize=10.5, fontweight="bold")
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)

fig.suptitle("OptiMaxx plus: efecto de los cargos publicados en el folleto 2025",
             fontsize=13, fontweight="bold", y=0.97)
fig.text(0.5, 0.04,
         "Mismo aporte de bolsillo: 5,000 MXN/mes. El PPR reinvierte la devolución fiscal. "
         "Folleto = sensibilidad de tarifas; no acredita cargos de una póliza.",
         ha="center", fontsize=8.5, color="#444444")
fig.tight_layout(rect=(0, 0.09, 1, 0.94), w_pad=2.8)
SALIDA.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(SALIDA, dpi=160)
plt.close(fig)
print("OK:", SALIDA)
