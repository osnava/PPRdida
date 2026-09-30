"""PPR OptiMaxx plus (Art. 151) vs ETF VUAA (BMV) — 5,000 MXN/mes durante 40 años.

Dos equivalencias (auditoría 2026-09-29, ver src/auditoria.py):
  - MISMOS APORTES (la elegida por el usuario): 5,000/mes + el equivalente de la
    devolución anual del SAT ($14,112) en ambos; en el PPR lo aporta el reembolso,
    en el VUAA sale del bolsillo (2.95M de bolsillo vs 2.40M del PPR).
  - MISMO BOLSILLO (comparación justa): el VUAA recibe solo los 5,000/mes.
La devolución llega cada junio (mes 18, 30, ..., 474; 39 pagos; la del año 40 cae fuera).

Supuestos fiscales (2026, congelados nominalmente por simplificación):
  - Asalariado, 600k/año → tramo 23.52% (tarifa anual ISR 2026).
  - Deducción PPR: min(10% ingresos, 5 UMA anuales) = 60,000 exacto →
    devolución = 60,000 × 23.52% = $14,112/año.
  - Salida PPR (mes 480, 65 años, CG 3.21): retiro único, exento hasta 90 UMA
    elevadas al año (art. 171 RLISR, aplicable al PPR por la regla 3.17.6 RMF) y
    tarifa anual sobre el excedente. Conservador en dos cosas: el art. 171 remite
    el excedente al art. 95 (tasa efectiva, menos impuesto) y el art. 152
    actualiza la tarifa con la inflación.
  - Salida VUAA: 10% definitivo sobre la ganancia (Art. 129 LISR), retenido
    por la casa de bolsa; costo de adquisición actualizado por inflación.

Supuestos de mercado: S&P 500 nominal 10%/año (supuesto del usuario);
FX estable (10% en MXN) y depreciación del peso 1.5%/año (1.10 × 1.015 − 1 = 11.65% en MXN).
Inflación 4% (crece UDI del cargo fijo, UMA de la exención y referencia del bono).

Cargos PPR según Condiciones Generales (topes, "hasta"): administrativo 1.5%
trimestral sobre Fondo Inicial (aportaciones meses 1-18) durante el Plazo
Comprometido de 25 años; gestión 0.1% mensual sobre el fondo total; fijo 25
UDIS/mes desde el mes 19; todo +IVA. Bono de Fidelidad (CG 3.6):
75% de la aportación comprometida del primer año (45,000 en total). El modelo
interpreta su generación conforme a los pagos comprometidos como un reparto
entre los 300 pagos (150/mes). Los folletos Allianz 2023 y 2025, p. 10,
describen en cambio su generación con los pagos iniciales del primer año;
se conserva la interpretación de la CG, que prevalece. Rinde inflación+5% (tope 9%),
paga cargo administrativo y de gestión (3.10.3) y se acredita al mes 300.
Se supone que entonces el titular instruye invertirlo en la misma alternativa
de mercado; CG 3.6 indica renta fija de corto plazo por defecto hasta recibir
instrucciones, cuyo rendimiento no se conoce aquí.
VUAA: corretaje 0.25% + IVA por operación (supuesto GBM/Bursanet) + OCF 0.07% (Vanguard México, 2026).
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent   # raíz del proyecto
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------------ parámetros
MESES = 480
APORT_M = 5_000.0
INFLACION = 0.04
IVA = 0.16
TOPE_ADMIN_TRIMESTRAL = 0.015
TOPE_GESTION_MENSUAL = 0.001
TOPE_FIJO_UDIS_MENSUAL = 25
UDI0 = 8.826356          # MXN/UDI, 26-sep-2026
UMA0 = 117.31            # MXN/día, 2026
REFUND = 14_112.0        # 60,000 × 23.52%
MESES_REFUND = set(range(18, 475, 12))
PLAZO_COMPROMETIDO = 300
PLAZO_INICIAL = 18
BONO_PCT = 0.75          # tabla 3.6: 60k anuales, plazo >= 20 años
BONO_MES = APORT_M * 12 * BONO_PCT / PLAZO_COMPROMETIDO   # 45,000 en total, pro rata: 150/mes
BONO_RATE = min(INFLACION + 0.05, 0.09)
EXENCION_UMAS = 90 * 30.4 * 12   # 90 UMA elevadas al año (UMA anual INEGI = diaria × 30.4 × 12)
CORRETAJE = 0.0025 * (1 + IVA)
OCF = 0.0007
FX = [(0.10, "peso estable"), (1.10 * 1.015 - 1, "peso -1.5%/año")]

TARIFA = [  # anual ISR 2026 (SAT/RMF 2026, Anexo 8)
    (0.01, 10_135.11, 0.0, 0.0192), (10_135.12, 86_022.11, 194.59, 0.064),
    (86_022.12, 151_176.19, 5_051.37, 0.1088), (151_176.20, 175_735.66, 12_140.13, 0.16),
    (175_735.67, 210_403.69, 16_069.64, 0.1792), (210_403.70, 424_353.97, 22_282.14, 0.2136),
    (424_353.98, 668_840.14, 67_981.92, 0.2352), (668_840.15, 1_276_925.98, 125_485.07, 0.30),
    (1_276_925.99, 1_702_567.97, 307_910.81, 0.32), (1_702_567.98, 5_107_703.92, 444_116.23, 0.34),
]
TOPE_35 = 5_107_703.92


def isr(x: float) -> float:
    if x <= 0:
        return 0.0
    for li, ls, cuota, tasa in TARIFA:
        if x <= ls:
            return cuota + tasa * (x - li)
    return isr(TOPE_35) + 0.35 * (x - TOPE_35)


def bono_pct(aportacion_anual: float, plazo_meses: int) -> float:
    """Porcentaje de la tabla 3.6 según compromiso anual y plazo contratado."""
    if not 60 <= plazo_meses <= 300 or plazo_meses % 12:
        raise ValueError("El Plazo Comprometido debe ser de 5 a 25 años completos")
    if aportacion_anual < 12_000:
        raise ValueError("La tabla 3.6 empieza en 12,000 MXN anuales")
    columna = 0 if aportacion_anual < 36_000 else 1 if aportacion_anual < 60_000 else 2 if aportacion_anual < 90_000 else 3
    fila = 0 if plazo_meses < 120 else 1 if plazo_meses < 180 else 2 if plazo_meses < 240 else 3
    return (
        (0.0, 0.0, 0.0, 0.0),
        (0.05, 0.15, 0.25, 0.35),
        (0.30, 0.40, 0.50, 0.60),
        (0.55, 0.65, 0.75, 1.00),
    )[fila][columna]


@dataclass(frozen=True)
class EscalasCargosPPR:
    """Fracción de cada tope de la CG 3.12; permite tarifas no uniformes."""

    administrativo: float
    gestion: float
    fijo: float

    def __post_init__(self):
        if min(self.administrativo, self.gestion, self.fijo) < 0:
            raise ValueError("Las escalas de cargos no pueden ser negativas")


TARIFA_FOLLETO_2025 = EscalasCargosPPR(0.6, 1.0, 0.6)


@dataclass(frozen=True)
class Parametros:
    """Supuestos nominales; el mes 1 es enero de 2026 salvo mes_inicio distinto.

    La devolución usa la tarifa 2026 congelada y solo deduce los pagos mensuales
    del titular; no calcula una segunda deducción por reinvertir la devolución.
    Los cargos PPR son los topes de la cláusula 3.12 multiplicados por fee_scale
    (uniforme) o por EscalasCargosPPR (una escala por cargo).
    El ISR de salida usa toda la exención salvo exencion_ya_usada_mxn, que se
    expresa en pesos nominales del año de retiro. art95 es una sensibilidad.
    """

    aportacion_mensual: float = APORT_M
    ingreso_anual: float = 600_000.0
    edad_inicial: int = 25
    meses: int = MESES
    mes_inicio: int = 1
    plazo_comprometido: int = PLAZO_COMPROMETIDO
    plazo_inicial: int = PLAZO_INICIAL
    inflacion: float = INFLACION
    iva: float = IVA
    udi_inicial: float = UDI0
    uma_diaria: float = UMA0
    corretaje_pct: float = 0.0025
    ocf: float = OCF
    exencion_ya_usada_mxn: float = 0.0
    metodo_isr_retiro: str = "tarifa"
    otros_ingresos_gravables: float = 0.0
    ultimo_sueldo_mensual: float = 0.0

    def __post_init__(self):
        if not 1 <= self.mes_inicio <= 12 or self.meses <= 0:
            raise ValueError("Mes de inicio u horizonte inválido")
        if self.aportacion_mensual < 0:
            raise ValueError("La aportación mensual no puede ser negativa")
        if self.ingreso_anual < 0 or self.inflacion < 0 or self.exencion_ya_usada_mxn < 0:
            raise ValueError("Ingreso, inflación y exención utilizada no pueden ser negativos")
        if self.iva < 0 or self.udi_inicial <= 0 or self.uma_diaria <= 0:
            raise ValueError("IVA, UDI o UMA fuera de rango")
        if self.corretaje_pct < 0 or self.ocf < 0 or self.otros_ingresos_gravables < 0:
            raise ValueError("Costos u otros ingresos gravables no pueden ser negativos")
        if self.edad_inicial < 0:
            raise ValueError("edad_inicial no puede ser negativa")
        if self.metodo_isr_retiro not in ("tarifa", "art95"):
            raise ValueError("metodo_isr_retiro debe ser 'tarifa' o 'art95'")
        if self.metodo_isr_retiro == "art95" and self.ultimo_sueldo_mensual <= 0:
            raise ValueError("art95 requiere ultimo_sueldo_mensual explícito")

    def devoluciones(self) -> dict[int, float]:
        """Aportaciones del año fiscal y devolución en junio del año siguiente."""
        por_anio: dict[int, float] = {}
        for m in range(1, self.meses + 1):
            anio = (self.mes_inicio + m - 2) // 12
            por_anio[anio] = por_anio.get(anio, 0.0) + self.aportacion_mensual
        devoluciones = {}
        for anio, pagado in por_anio.items():
            mes_devolucion = (anio + 1) * 12 + 7 - self.mes_inicio
            if mes_devolucion > self.meses:
                continue
            uma_anual = self.uma_diaria * 30.4 * 12 * (1 + self.inflacion) ** anio
            deduccion = min(pagado, self.ingreso_anual * 0.10, 5 * uma_anual)
            devoluciones[mes_devolucion] = isr(self.ingreso_anual) - isr(self.ingreso_anual - deduccion)
        return devoluciones


def impuesto_retiro(excedente: float, config: Parametros) -> float:
    """ISR atribuible al PPR bajo la tarifa base o sensibilidad Art. 95."""
    if excedente <= 0:
        return 0.0
    if config.metodo_isr_retiro == "tarifa":
        return isr(excedente)
    ordinario = config.otros_ingresos_gravables
    sueldo = min(excedente, config.ultimo_sueldo_mensual)
    base = ordinario + sueldo
    tasa = isr(base) / base
    return isr(base) - isr(ordinario) + tasa * (excedente - sueldo)


# ------------------------------------------------------------------ simulaciones
def sim_ppr(gross_anual: float, fee_scale: float | EscalasCargosPPR, con_refund: bool = True,
            config: Parametros | None = None):
    """Serie anual del saldo contable sin bono no acreditado y desglose final.

    La serie excluye el Fondo de Bono antes de cumplir el plazo y no es valor de
    rescate: antes de ese plazo faltarían cargos por retiro (3.14.2). fee_scale=0
    da el plan sin cargos; EscalasCargosPPR permite las tarifas del folleto.
    Rendimiento, inflación, cargos y fiscalidad los fija gross_anual y config
    (tarifa 2026 congelada).
    """
    cfg = config or Parametros()
    if gross_anual <= -1:
        raise ValueError("El rendimiento debe ser mayor a -100%")
    escalas = fee_scale if isinstance(fee_scale, EscalasCargosPPR) else EscalasCargosPPR(
        fee_scale, fee_scale, fee_scale)
    pct_bono = bono_pct(cfg.aportacion_mensual * 12, cfg.plazo_comprometido)
    if cfg.plazo_inicial != 18:
        raise ValueError("El Plazo Inicial de esta póliza es 18 meses (cláusula 3.1)")
    if cfg.meses < cfg.plazo_comprometido:
        raise ValueError("Un retiro antes del Plazo Comprometido requiere modelar los cargos de la cláusula 3.14.2")
    if cfg.meses > cfg.plazo_comprometido and cfg.plazo_comprometido < 300:
        raise ValueError("La cláusula 3.1 solo permite seguir aportando en la misma póliza tras un plazo de 25 años")
    if cfg.edad_inicial + cfg.meses / 12 < 65:
        raise ValueError("Retirar el PPR antes de los 65 requiere el tratamiento fiscal anticipado de la cláusula 3.21.2")
    devoluciones = cfg.devoluciones() if con_refund else {}
    bono_mes = cfg.aportacion_mensual * 12 * pct_bono / cfg.plazo_comprometido
    i_m = (1 + gross_anual) ** (1 / 12) - 1
    i_b = (1 + min(cfg.inflacion + 0.05, 0.09)) ** (1 / 12) - 1
    g = TOPE_GESTION_MENSUAL * escalas.gestion * (1 + cfg.iva)      # gestión, mensual anticipado
    a = TOPE_ADMIN_TRIMESTRAL * escalas.administrativo * (1 + cfg.iva)      # administrativo, trimestral vencido
    fi = fr = fb = bk = bono_acreditado = 0.0
    fees = {"administrativo": 0.0, "gestion": 0.0, "fijo": 0.0}
    serie_cargos = {k: [] for k in fees}
    aportado = 0.0
    serie = []
    for m in range(1, cfg.meses + 1):
        fees["gestion"] += g * (fi + fr + fb + bk)      # el Fondo de Bono también paga (3.10.3)
        fi *= 1 - g; fr *= 1 - g; fb *= 1 - g; bk *= 1 - g

        aportado += cfg.aportacion_mensual
        if m <= cfg.plazo_inicial:
            fi += cfg.aportacion_mensual
        else:
            fr += cfg.aportacion_mensual
        reembolso = devoluciones.get(m, 0.0)
        fr += reembolso
        aportado += reembolso
        if m <= cfg.plazo_comprometido:
            fb += bono_mes

        fi *= 1 + i_m; fr *= 1 + i_m; bk *= 1 + i_m; fb *= 1 + i_b

        if m % 3 == 0 and m <= cfg.plazo_comprometido:
            fees["administrativo"] += a * (fi + fb)
            fi *= 1 - a; fb *= 1 - a
        if m > cfg.plazo_inicial:
            udi = cfg.udi_inicial * (1 + cfg.inflacion) ** ((m - 1) / 12)
            f = TOPE_FIJO_UDIS_MENSUAL * udi * escalas.fijo * (1 + cfg.iva)
            total = fr + bk
            if total:
                fr -= f * fr / total; bk -= f * bk / total
            fees["fijo"] += f
        if m == cfg.plazo_comprometido:
            bono_acreditado = fb
            bk += fb; fr += fi; fi = 0.0; fb = 0.0
        if m % 12 == 0:
            serie.append(fi + fr + bk)
            for k in fees:
                serie_cargos[k].append(fees[k])
    saldo = fi + fr + bk
    exencion_total = EXENCION_UMAS * cfg.uma_diaria * (1 + cfg.inflacion) ** (cfg.meses / 12)
    exencion_disponible = max(0.0, exencion_total - cfg.exencion_ya_usada_mxn)
    impuesto = impuesto_retiro(saldo - exencion_disponible, cfg)
    return {
        "serie": serie, "serie_cargos": serie_cargos, "aportado": aportado, "bono": bk,
        "bono_acreditado": bono_acreditado, "saldo": saldo, "fees": fees, "impuesto": impuesto,
        "neto": saldo - impuesto, "bolsillo": cfg.aportacion_mensual * cfg.meses,
        "exencion_disponible": exencion_disponible,
        "neto_hoy": (saldo - impuesto) / (1 + cfg.inflacion) ** (cfg.meses / 12),
    }


def sim_vuaa(gross_anual: float, con_refund: bool = True, costos: float = 1.0,
             config: Parametros | None = None):
    """con_refund=False: mismo bolsillo que el PPR (sin el equivalente de la devolución).
    costos=0: mismas aportaciones sin corretaje ni OCF (para medir su costo real).
    Rendimiento, inflación y tarifas fiscales siguen config; tarifa ISR 2026
    congelada nominalmente y 10% definitivo sobre ganancia Art. 129.
    """
    cfg = config or Parametros()
    if gross_anual <= -1 or costos < 0:
        raise ValueError("El rendimiento debe ser mayor a -100% y costos no puede ser negativo")
    devoluciones = cfg.devoluciones() if con_refund else {}
    corretaje_pct = cfg.corretaje_pct * (1 + cfg.iva)
    i_m = (1 + gross_anual) ** (1 / 12) - 1
    saldo = aportado = corretaje = ocf = base = 0.0
    serie, serie_costos = [], []
    for m in range(1, cfg.meses + 1):
        entrada = cfg.aportacion_mensual + devoluciones.get(m, 0.0)
        aportado += entrada
        c = corretaje_pct * costos * entrada
        corretaje += c
        saldo += entrada - c
        saldo *= 1 + i_m
        o = saldo * cfg.ocf * costos / 12
        ocf += o
        saldo -= o
        # Art. 129: costo de adquisición (lo pagado, corretaje incluido) actualizado por inflación a la venta
        base += entrada * (1 + cfg.inflacion) ** ((cfg.meses - m) / 12)
        if m % 12 == 0:
            serie.append(saldo)
            serie_costos.append(corretaje + ocf)
    corretaje_venta = saldo * corretaje_pct * costos
    venta = saldo - corretaje_venta
    impuesto = 0.10 * max(0.0, venta - base)
    return {
        "serie": serie, "serie_costos": serie_costos, "aportado": aportado,
        "corretaje": corretaje,  # alias histórico: solo compras
        "corretaje_compra": corretaje, "corretaje_venta": corretaje_venta,
        "ocf": ocf, "costos_total": corretaje + corretaje_venta + ocf,
        "saldo": venta, "impuesto": impuesto, "neto": venta - impuesto, "bolsillo": aportado,
        "saldo_pre_venta": saldo, "base": base,       # para el escenario de retiros graduales
        "neto_hoy": (venta - impuesto) / (1 + cfg.inflacion) ** (cfg.meses / 12),
    }


ESCENARIOS = []
for _g, _fx in FX:
    ESCENARIOS += [
        (f"PPR tope · {_fx}", sim_ppr(_g, 1.0)),
        (f"PPR mitad tope · {_fx}", sim_ppr(_g, 0.5)),
        (f"VUAA mismos aportes · {_fx}", sim_vuaa(_g)),
        (f"VUAA mismo bolsillo · {_fx}", sim_vuaa(_g, con_refund=False)),
    ]

if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    resultado = {nombre: {k: v for k, v in r.items() if not k.startswith("serie")} | {"serie": r["serie"]}
                 for nombre, r in ESCENARIOS}
    (OUT / "resultados_ppr_vs_vuaa.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    M = 1e6
    print(f"{'escenario':<38}{'bolsillo':>11}{'aportado':>11}{'comisiones':>12}{'bono':>11}{'saldo':>11}{'impuesto':>12}{'NETO':>11}")
    for nombre, r in ESCENARIOS:
        com = sum(r["fees"].values()) if "fees" in r else r["costos_total"]
        bono = r.get("bono", 0.0)
        print(f"{nombre:<38}{r['bolsillo']/M:>10.2f}M{r['aportado']/M:>10.2f}M{com/M:>11.2f}M{bono/M:>10.2f}M{r['saldo']/M:>10.2f}M{r['impuesto']/M:>11.2f}M{r['neto']/M:>10.2f}M")
