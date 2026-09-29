"""Primera prueba: solo comisiones del PPR OptiMaxx plus Art. 151, sin devolución del SAT.

Caso: 5,000 MXN/mes durante 40 años (480 meses). Usa sim_ppr, así que la
estructura de cargos y el Bono de Fidelidad son los del modelo central (ver su
docstring: CG 3.12, 3.6, 3.10.3). "Costo en riqueza" = saldo del mismo plan con
cargos en cero menos saldo con cargos, al año 40.

Escenarios: bruto 10% nominal (supuesto del usuario, S&P 500 histórico USD),
techo de cargos vs mitad del techo; y 7% bruto como versión "realista/moderada".
"""
from sim_ppr_vs_vuaa import sim_ppr

M = 1e6

print(f"{'escenario':<38}{'aportado':>11}{'cargos pagados':>16}{'saldo sin cargos':>18}{'saldo con cargos':>18}{'costo riqueza':>15}")
for nombre, gross, scale in [
    ("10% bruto, cargos al tope (peor caso)", 0.10, 1.0),
    ("10% bruto, cargos a mitad de tope", 0.10, 0.5),
    ("7% bruto, cargos al tope", 0.07, 1.0),
]:
    r = sim_ppr(gross, scale, con_refund=False)
    sin = sim_ppr(gross, 0.0, con_refund=False)["saldo"]
    print(f"{nombre:<38}{r['aportado']/M:>10.2f}M{sum(r['fees'].values())/M:>15.2f}M{sin/M:>17.2f}M"
          f"{r['saldo']/M:>17.2f}M{(sin - r['saldo'])/M:>14.2f}M")

r = sim_ppr(0.10, 1.0, con_refund=False)
print("\nDesglose de cargos (10% bruto, topes):")
for k, v in r["fees"].items():
    print(f"  {k:<15} ${v:,.0f} MXN")
print(f"  {'IVA incluido':<15} en las cifras anteriores")
print(f"\nBono de Fidelidad acreditado en el mes 300: ${r['bono_acreditado']:,.0f} MXN (vale ${r['bono']:,.0f} al año 40)")
print(f"Saldo sin contar el bono: ${r['saldo'] - r['bono']:,.0f} MXN")
