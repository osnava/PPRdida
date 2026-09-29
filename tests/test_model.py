"""Invariantes económicas y regresiones del caso publicado (tarifa ISR 2026)."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import rag
from sim_ppr_vs_vuaa import (FX, OCF, Parametros, bono_pct, isr, sim_ppr,
                             sim_vuaa)
from sim_retiro_4pct import filas_retiro
from sim_sensibilidad_fiscal import filas_fiscales


class ModeloBaseTest(unittest.TestCase):
    def test_tarifa_2026_y_devoluciones(self):
        self.assertAlmostEqual(isr(600_000) - isr(540_000), 14_112)
        self.assertEqual(isr(0), 0)
        devoluciones = Parametros().devoluciones()
        self.assertEqual((len(devoluciones), min(devoluciones), max(devoluciones)), (39, 18, 474))
        self.assertTrue(all(abs(x - 14_112) < 0.01 for x in devoluciones.values()))

    def test_ppr_regresion_publicada(self):
        esperados = (19_198_607.14, 23_151_937.68, 26_092_884.69, 32_313_172.24)
        actuales = [sim_ppr(g, fs)["neto"] for g, _ in FX for fs in (1.0, 0.5)]
        for actual, esperado in zip(actuales, esperados):
            self.assertAlmostEqual(actual, esperado, delta=0.05)

    def test_vuaa_costos_completos_y_valor_real(self):
        self.assertEqual(OCF, 0.0007)
        for g, _ in FX:
            r = sim_vuaa(g, con_refund=False)
            self.assertAlmostEqual(r["costos_total"],
                                   r["corretaje_compra"] + r["ocf"] + r["corretaje_venta"])
            self.assertAlmostEqual(r["neto"], r["saldo"] - r["impuesto"])
            self.assertAlmostEqual(r["neto_hoy"] * 1.04**40, r["neto"], delta=0.01)
            self.assertGreater(r["costos_total"], r["corretaje_compra"])

    def test_parametros_invalidos_no_producen_saldos_enganosos(self):
        with self.assertRaises(ValueError):
            sim_ppr(0.10, -0.5)
        with self.assertRaises(ValueError):
            sim_vuaa(-1.1)
        with self.assertRaises(ValueError):
            Parametros(ocf=-0.01)

    def test_bono_y_nuevos_aportes(self):
        self.assertEqual(bono_pct(60_000, 300), 0.75)
        self.assertEqual(bono_pct(90_000, 300), 1.0)
        self.assertEqual(bono_pct(60_000, 60), 0.0)
        cfg = Parametros(aportacion_mensual=10_000)
        self.assertEqual(cfg.devoluciones()[18], 14_112)
        self.assertAlmostEqual(sim_ppr(0.10, 1.0, config=cfg)["aportado"], 5_350_368)

    def test_inicio_parcial_y_retiro_anticipado(self):
        cfg = Parametros(mes_inicio=9)
        self.assertEqual(min(cfg.devoluciones()), 10)
        self.assertEqual(cfg.devoluciones()[10], 4_704)
        cfg_60 = Parametros(meses=420)
        self.assertEqual(len(sim_vuaa(0.10, config=cfg_60)["serie"]), 35)
        with self.assertRaisesRegex(ValueError, "antes de los 65"):
            sim_ppr(0.10, 1.0, config=cfg_60)

    def test_plazo_corto_no_permite_aportar_despues_en_la_misma_poliza(self):
        with self.assertRaisesRegex(ValueError, "cláusula 3.1"):
            sim_ppr(0.10, 1.0, config=Parametros(plazo_comprometido=240))
        cfg = Parametros(plazo_comprometido=240, meses=240, edad_inicial=45)
        self.assertGreater(sim_ppr(0.10, 1.0, config=cfg)["neto"], 0)

    def test_vuaa_corto_independiente_del_plazo_ppr(self):
        cfg = Parametros(aportacion_mensual=500, meses=12)
        r = sim_vuaa(0.10, con_refund=False, config=cfg)
        self.assertEqual(len(r["serie"]), 1)
        self.assertAlmostEqual(r["aportado"], 6_000)
        with self.assertRaisesRegex(ValueError, "12,000"):
            sim_ppr(0.10, 1.0, config=cfg)

    def test_exencion_y_articulo_95_como_sensibilidad(self):
        datos = filas_fiscales()
        self.assertEqual(len(datos["resultados"]), 24)
        filas = [r for r in datos["resultados"] if
                 r["fx"] == "peso estable" and r["cargos"] == "tope"]
        tarifa = sorted((r for r in filas if r["metodo_isr"] == "tarifa"),
                        key=lambda r: r["fraccion_exencion_consumida"])
        self.assertAlmostEqual(tarifa[0]["neto_ppr"], sim_ppr(0.10, 1.0)["neto"])
        self.assertGreater(tarifa[0]["neto_ppr"], tarifa[1]["neto_ppr"])
        self.assertGreater(tarifa[1]["neto_ppr"], tarifa[2]["neto_ppr"])
        art95 = next(r for r in filas if r["metodo_isr"] == "art95" and
                     r["fraccion_exencion_consumida"] == 0)
        self.assertGreater(art95["neto_ppr"], tarifa[0]["neto_ppr"])

    def test_retiro_primer_anio_neto(self):
        primera = filas_retiro()[0]
        self.assertLess(primera["retiro_anio1_neto_hoy"], primera["retiro_anio1_hoy"])
        self.assertAlmostEqual(primera["retiro_anio1_neto"], primera["serie"][0]["neto"])

    def test_rag_rechaza_modelo_distinto(self):
        if not (ROOT / "index" / "meta.json").exists():
            self.skipTest("El índice RAG opcional no existe")
        with patch.object(rag, "MODEL_NAME", "modelo-distinto"):
            with self.assertRaisesRegex(RuntimeError, "no corresponde"):
                rag.load()

    def test_json_base_conciliado(self):
        path = ROOT / "outputs" / "resultados_ppr_vs_vuaa.json"
        if not path.exists():
            self.skipTest("Aún no se han generado los resultados")
        datos = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(datos), 8)
        self.assertAlmostEqual(datos["VUAA mismo bolsillo · peso estable"]["neto"],
                               sim_vuaa(0.10, con_refund=False)["neto"], delta=0.01)


if __name__ == "__main__":
    unittest.main()
