"""Sensibilidad de los cargos publicados en el folleto OptiMaxx plus 2025.

Conserva todos los supuestos del caso base: 5,000 MXN/mes durante 40 años,
devolución anual invertida en el PPR, 10% nominal USD, inflación 4%, dos
trayectorias cambiarias e ISR calculado con la tarifa nominal de 2026 congelada.
Las cifras del folleto (0.9% trimestral, 0.1% mensual y 15 UDIS/mes, más el
IVA supuesto en el modelo) se prueban como sensibilidad, no como tarifa
confirmada para una póliza concreta. El folleto 2025 y la CG 2018 difieren en
otros términos; este cálculo cambia únicamente las tres tarifas. En particular,
conserva la generación del bono durante el plazo comprometido interpretada de
CG 3.6, aunque los folletos 2023 y 2025, p. 10, la describen durante el primer
año. Comparación de mismo bolsillo: VUAA recibe solo los 5,000 MXN/mes.
"""
import json
import sys

from sim_ppr_vs_vuaa import (FX, IVA, OUT, TARIFA_FOLLETO_2025,
                             TOPE_ADMIN_TRIMESTRAL, TOPE_FIJO_UDIS_MENSUAL,
                             TOPE_GESTION_MENSUAL, sim_ppr, sim_vuaa)

FUENTE = ("https://www.allianz.com.mx/content/dam/onemarketing/iberolatam/"
          "allianz-mx/ahorro---plus/documentos---plus/"
          "Folleto%20OptiMaxx%20plus%202025.pdf#page=11")


def calcular():
    escenarios = {}
    for rendimiento, fx in FX:
        tope = sim_ppr(rendimiento, 1.0)
        mitad = sim_ppr(rendimiento, 0.5)
        folleto = sim_ppr(rendimiento, TARIFA_FOLLETO_2025)
        vuaa_bolsillo = sim_vuaa(rendimiento, con_refund=False)
        escenarios[fx] = {
            "ppr_tope_neto": tope["neto"],
            "ppr_mitad_neto": mitad["neto"],
            "ppr_folleto_neto": folleto["neto"],
            "ppr_folleto_neto_hoy": folleto["neto_hoy"],
            "ppr_folleto_cargos_cobrados": folleto["fees"],
            "ppr_folleto_isr_salida": folleto["impuesto"],
            "vuaa_mismo_bolsillo_neto": vuaa_bolsillo["neto"],
            "mejora_folleto_vs_tope": folleto["neto"] - tope["neto"],
            "brecha_folleto_vs_vuaa_mismo_bolsillo": vuaa_bolsillo["neto"] - folleto["neto"],
        }
    return {
        "fuente": FUENTE,
        "cargo_administrativo_trimestral": TOPE_ADMIN_TRIMESTRAL * TARIFA_FOLLETO_2025.administrativo,
        "cargo_gestion_mensual": TOPE_GESTION_MENSUAL * TARIFA_FOLLETO_2025.gestion,
        "cargo_fijo_udis_mensual_desde_mes_19": TOPE_FIJO_UDIS_MENSUAL * TARIFA_FOLLETO_2025.fijo,
        "iva_aplicado": IVA,
        "alcance": "sensibilidad híbrida: modelo CG 2018 con tarifas del folleto 2025; no equivale a póliza individual",
        "generacion_bono": "proporcional durante el plazo comprometido, interpretación de CG 3.6; los folletos 2023 y 2025, p. 10, describen generación durante el primer año",
        "escenarios": escenarios,
    }


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    resultado = calcular()
    (OUT / "resultados_tarifa_folleto.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    for fx, r in resultado["escenarios"].items():
        print(f"{fx}: tope {r['ppr_tope_neto']/1e6:.2f}M, "
              f"folleto {r['ppr_folleto_neto']/1e6:.2f}M, "
              f"mitad {r['ppr_mitad_neto']/1e6:.2f}M, "
              f"VUAA mismo bolsillo {r['vuaa_mismo_bolsillo_neto']/1e6:.2f}M")
