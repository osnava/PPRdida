"""Auditoría del modelo PPR vs VUAA (2026-09-29): cascada desde los resultados
publicados antes de la auditoría hasta el modelo corregido (sim_ppr_vs_vuaa.py).

No escribe outputs; solo imprime. Pasos:
  C1  Bono de Fidelidad = 75% de la aportación comprometida del PRIMER año
      (45,000 en total), generado pro rata con los pagos comprometidos
      (45,000 / 300 = 150 por mes). El modelo anterior acumulaba 75% de CADA
      aportación (3,750/mes, 25x). CG 3.6 (bonificación parcial de los cargos
      cobrados, % de la aportación comprometida anual) y folleto Allianz p.2 y p.5
      (bono de hasta el 100% de las aportaciones comprometidas del primer año).
  C2  El Fondo de Bono también paga cargo administrativo y de gestión (CG 3.10.3).
  C3  Exención del retiro único = 90 UMA elevadas al año (RLISR 171, aplicable al
      PPR por la regla 3.17.6 RMF), no 90 UMA diarias.
  C4  VUAA: base de costo actualizada por inflación (Art. 129 LISR), corretaje
      contado una sola vez en la base y con IVA.
  C5  VUAA con el MISMO desembolso de bolsillo que el PPR (5k/mes).
  C6  Depreciación compuesta: 1.10 × 1.015 − 1 = 11.65% (antes 11.5%).
  C7  OCF vigente de VUAA 0.07% (antes se modelaba 0.08%); además se reportan
      corretaje de compra, OCF y corretaje de venta como costos totales.
  S95 Sensibilidad: excedente del PPR a la tasa efectiva del Art. 95 (RLISR 171).
  H   Estrategia híbrida: 5k/mes al PPR y la devolución del SAT al VUAA (no deducible,
      no tiene por qué pagar cargos del PPR); mismo bolsillo que el VUAA de C5.
  Fase de retiro 4% (sim_retiro_4pct): la base de costo ya no crece con el mercado
  (bug `b *= 1 + r_nom`), deflactor año por año e ISR latente del legado.

Uso: .venv/Scripts/python.exe src/auditoria.py
"""
import sys
from dataclasses import replace

from sim_ppr_vs_vuaa import (APORT_M, BONO_MES, BONO_PCT, BONO_RATE, EXENCION_UMAS, FX, INFLACION, IVA, Parametros,
                             MESES, MESES_REFUND, PLAZO_COMPROMETIDO, PLAZO_INICIAL, REFUND, UDI0, UMA0,
                             isr, sim_ppr, sim_vuaa)
from sim_retiro_4pct import filas_retiro

M = 1e6
INFL40 = (1 + INFLACION) ** (MESES / 12)
EXENCION_ANTES = 90                      # UMAs diarias (modelo anterior)
DEP_ANTES = 0.115                        # depreciación sumada, no compuesta (modelo anterior)
TASA95 = isr(650_000) / 650_000          # Art. 95: sueldo anual 600k + último sueldo mensual 50k
# resultados publicados antes de la auditoría (outputs del 2026-09-26)
ORIGINAL = {(0.10, 1.0): 21_510_586.332224876, (0.10, 0.5): 26_267_920.289197497,
            (DEP_ANTES, 1.0): 29_542_071.038593285, (DEP_ANTES, 0.5): 36_566_061.73894937}
VUAA_ORIGINAL = {0.10: 29_981_518.25756225, DEP_ANTES: 45_294_241.146410875}
RETIRO_ORIGINAL = {  # riqueza total con la regla del 4%, millones de pesos de hoy
    "VUAA mismos aportes · peso estable": 22.73, "PPR tope → reinvertido · peso estable": 15.29,
    "PPR mitad → reinvertido · peso estable": 18.68, "VUAA mismos aportes · peso -1.5%/año": 52.17,
    "PPR tope → reinvertido · peso -1.5%/año": 31.47, "PPR mitad → reinvertido · peso -1.5%/año": 38.95,
}


def ppr(gross, fee_scale, bono_mes=APORT_M * BONO_PCT, cargos_bono=False, bono_meses=PLAZO_COMPROMETIDO,
        con_refund=True):
    """Lazo de sim_ppr con C1-C2 como interruptores (apagados = modelo anterior).
    Devuelve (saldo mes 480, bono al mes 480, Fondo de Bono al mes 300)."""
    i_m = (1 + gross) ** (1 / 12) - 1
    i_b = (1 + BONO_RATE) ** (1 / 12) - 1
    fi = fr = fb = bk = fb300 = 0.0
    for m in range(1, MESES + 1):
        k = 1 - 0.001 * fee_scale * (1 + IVA)             # gestión, mensual anticipado
        fi *= k; fr *= k; bk *= k
        if cargos_bono:
            fb *= k
        if m <= PLAZO_INICIAL:
            fi += APORT_M
        else:
            fr += APORT_M
        if con_refund and m in MESES_REFUND:
            fr += REFUND
        if m <= bono_meses:
            fb += bono_mes
        fi *= 1 + i_m; fr *= 1 + i_m; bk *= 1 + i_m; fb *= 1 + i_b
        if m % 3 == 0 and m <= PLAZO_COMPROMETIDO:
            k = 1 - 0.015 * fee_scale * (1 + IVA)         # administrativo, trimestral vencido
            fi *= k
            if cargos_bono:
                fb *= k
        if m > PLAZO_INICIAL:
            f = 25 * UDI0 * (1 + INFLACION) ** ((m - 1) / 12) * fee_scale * (1 + IVA)
            t = fr + bk
            fr -= f * fr / t; bk -= f * bk / t
        if m == PLAZO_COMPROMETIDO:
            fb300 = fb
            bk += fb; fr += fi; fi = fb = 0.0
    return fi + fr + bk, bk, fb300


def isr_ppr(saldo, exencion_uma, tasa95=None):
    exc = saldo - exencion_uma * UMA0 * INFL40
    if exc <= 0:
        return 0.0
    return exc * tasa95 if tasa95 else isr(exc)


def netos_ppr(gs, bono_mes, cargos_bono, exencion, tasa95=None, con_refund=True):
    out = {}
    for g in gs:
        for fs in (1.0, 0.5):
            s = ppr(g, fs, bono_mes, cargos_bono, con_refund=con_refund)[0]
            out[g, fs] = s - isr_ppr(s, exencion, tasa95)
    return out


def equilibrio(f):
    """fee_scale en [0, 1] donde f cruza cero; f < 0 = gana el PPR, f > 0 = gana el VUAA (bisección)."""
    lo, hi = 0.0, 1.0
    if f(lo) >= 0 or f(hi) <= 0:
        return lo if f(lo) >= 0 else hi
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if f(mid) > 0 else (mid, hi)
    return mid


def check():
    """Extremos de la cascada: todo apagado = resultados publicados antes de la auditoría;
    todo encendido = modelo corregido actual."""
    for (g, fs), neto in netos_ppr((0.10, DEP_ANTES), APORT_M * BONO_PCT, False, EXENCION_ANTES).items():
        assert abs(neto - ORIGINAL[g, fs]) < 1e-3
    for g, _ in FX:
        for fs in (1.0, 0.5):
            s, r = ppr(g, fs, BONO_MES, cargos_bono=True)[0], sim_ppr(g, fs)
            assert abs(s - r["saldo"]) < 1e-3 and abs(isr_ppr(s, EXENCION_UMAS) - r["impuesto"]) < 1e-3
    assert BONO_MES == 150.0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    check()

    # ---- 1. el bono del modelo anterior contra los cargos que dice "bonificar parcialmente"
    nuevo = sim_ppr(0.10, 1.0)
    cargos25 = sum(v[24] for v in nuevo["serie_cargos"].values())
    _, b40_antes, fb300_antes = ppr(0.10, 1.0)
    _, b40_gen, fb300_gen = ppr(0.10, 1.0, bono_meses=12)       # 3,750/mes solo el año 1 = 45k, sin cargos
    print("1) Fondo de Bono al año 25 vs cargos cobrados en el plazo (tope, peso estable)")
    print(f"   cargos cobrados años 1-25:           {cargos25 / M:6.2f}M")
    print(f"   Fondo de Bono del modelo anterior:   {fb300_antes / M:6.2f}M  ({fb300_antes / cargos25:.0%} de los cargos)")
    print(f"   Fondo de Bono corregido (CG 3.6):    {nuevo['bono_acreditado'] / M:6.2f}M  "
          f"({nuevo['bono_acreditado'] / cargos25:.0%} de los cargos)")
    print(f"   lectura más generosa (45k en el año 1, sin cargos): {fb300_gen / M:.2f}M al año 25, "
          f"{b40_gen / M:.2f}M al año 40 (modelo anterior: {b40_antes / M:.2f}M)\n")

    # ---- 2. cascada de correcciones, neto tras ISR al año 40 (millones nominales)
    antes, ahora = (0.10, DEP_ANTES), tuple(g for g, _ in FX)
    config_anterior = replace(Parametros(), ocf=0.0008)
    va_c4 = {g: sim_vuaa(g, config=config_anterior)["neto"] for g in antes}
    vb_c5 = {g: sim_vuaa(g, con_refund=False, config=config_anterior)["neto"] for g in antes}
    va_c6 = {g: sim_vuaa(g, config=config_anterior)["neto"] for g in ahora}
    vb_c6 = {g: sim_vuaa(g, con_refund=False, config=config_anterior)["neto"] for g in ahora}
    va = {g: sim_vuaa(g)["neto"] for g in ahora}
    vb = {g: sim_vuaa(g, con_refund=False)["neto"] for g in ahora}
    p3 = netos_ppr(antes, BONO_MES, True, EXENCION_UMAS)
    p6 = netos_ppr(ahora, BONO_MES, True, EXENCION_UMAS)
    ph = netos_ppr(ahora, BONO_MES, True, EXENCION_UMAS, con_refund=False)
    ph = {k: v + va[k[0]] - vb[k[0]] for k, v in ph.items()}     # + la devolución invertida en VUAA

    def fila(gs, p, vua, vub):
        return [x for g in gs for x in (p[g, 1.0], p[g, 0.5], vua.get(g), vub.get(g))]

    pasos = [
        ("modelo anterior (publicado)", fila(antes, netos_ppr(antes, APORT_M * BONO_PCT, False, EXENCION_ANTES), VUAA_ORIGINAL, {})),
        ("C1 bono = 75% del 1er año (45k)", fila(antes, netos_ppr(antes, BONO_MES, False, EXENCION_ANTES), VUAA_ORIGINAL, {})),
        ("C2 + cargos s/Fondo de Bono", fila(antes, netos_ppr(antes, BONO_MES, True, EXENCION_ANTES), VUAA_ORIGINAL, {})),
        ("C3 + exención 90 UMA anuales", fila(antes, p3, VUAA_ORIGINAL, {})),
        ("C4 + VUAA base Art.129, corretaje", fila(antes, p3, va_c4, {})),
        ("C5 + VUAA mismo bolsillo", fila(antes, p3, va_c4, vb_c5)),
        ("C6 + depreciación 11.65%", fila(ahora, p6, va_c6, vb_c6)),
        ("C7 + OCF VUAA 0.07% = actual", fila(ahora, p6, va, vb)),
        ("S95 excedente PPR a tasa Art.95", fila(ahora, netos_ppr(ahora, BONO_MES, True, EXENCION_UMAS, TASA95), va, vb)),
        ("H  PPR 5k + devolución a VUAA", fila(ahora, ph, va, vb)),
    ]
    print("2) Neto tras ISR al año 40, millones MXN nominales (VUAA ap. = mismos aportes; bol. = mismo bolsillo)")
    print(f"   {'':<36}{'--------- peso estable ---------':^40}{'-------- peso -1.5%/año --------':^40}")
    print(f"   {'paso':<36}" + "".join(f"{h:>10}" for h in ["PPR tope", "PPR mitad", "VUAA ap.", "VUAA bol."] * 2))
    for nombre, vals in pasos:
        print(f"   {nombre:<36}" + "".join(f"{x / M:10.2f}" if x is not None else f"{'-':>10}" for x in vals))
    print(f"   (tasa efectiva Art. 95 supuesta: {TASA95:.1%}; exención al año 40: "
          f"{EXENCION_UMAS * UMA0 * INFL40 / M:.2f}M vs {EXENCION_ANTES * UMA0 * INFL40 / M:.3f}M del modelo anterior)\n")

    print(f"   Bono al año 40 (tope, estable): anterior {b40_antes / M:.2f}M -> corregido {nuevo['bono'] / M:.2f}M; "
          f"saldo antes de ISR {ppr(0.10, 1.0)[0] / M:.2f}M -> {nuevo['saldo'] / M:.2f}M "
          f"(VUAA mismos aportes {sim_vuaa(0.10)['saldo_pre_venta'] / M:.2f}M)")
    sin = sim_ppr(0.10, 0.0)["saldo"]
    for fs, et in ((1.0, "tope"), (0.5, "mitad")):
        con = sim_ppr(0.10, fs)["saldo"]
        print(f"   Costo real de los cargos PPR {et} (saldo sin cargos - con cargos, año 40, estable): "
              f"{(sin - con) / M:.2f}M = {(sin - con) / sin:.0%} del saldo sin cargos")
    for g, fx in FX:
        pierna = va[g] - vb[g]
        e_ppr = equilibrio(lambda s: vb[g] - sim_ppr(g, s)["neto"])
        e_hib = equilibrio(lambda s: vb[g] - sim_ppr(g, s, con_refund=False)["neto"] - pierna)
        print(f"   Empate con VUAA mismo bolsillo ({fx}): PPR con cargos al {e_ppr:.0%} de los topes; "
              f"híbrido al {e_hib:.0%}")
    print()

    # ---- 3. regla del 4%: publicado vs corregido
    print("3) Regla del 4%, riqueza total en millones de pesos de hoy")
    print("   anterior = publicado (retiros ÷1.04^55 + legado; base creciendo con el mercado);"
          " actual = sim_retiro_4pct (deflactor anual, legado neto de ISR latente)")
    print(f"   {'escenario':<42}{'anterior':>10}{'actual':>10}{'ISR fase hoy':>14}{'retiro bruto año1 hoy':>23}")
    for d in filas_retiro():
        ant = RETIRO_ORIGINAL.get(d["escenario"])
        ant_txt = f"{ant:10.2f}" if ant else f"{'-':>10}"
        print(f"   {d['escenario']:<42}{ant_txt}{d['riqueza_hoy'] / M:10.2f}{d['isr_hoy'] / M:14.2f}"
              f"{d['retiro_anio1_hoy'] / 1e3:15.0f}k")
