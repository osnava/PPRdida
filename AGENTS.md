# AGENTS.md — Guía para agentes trabajando en este repo

Proyecto de investigación financiera: **PPR OptiMaxx plus Art. 151 (Allianz México)
vs ETF VUAA (Vanguard S&P 500 UCITS Acc, BMV)**. El usuario hará dos tipos de
peticiones en español: **preguntar cualquier cosa sobre el PPR** (cargos, bono,
plazos, fiscalidad, definiciones del contrato) y **pedir simulaciones y
comparativos** ("¿qué pasa si aporto 10k?", "compáralo contra el NASDAQ",
"simula retirar a los 60"). Esta guía dice cómo atenderlas.

## Regla cero

No inventes números ni cláusulas. Todo dato del PPR sale del documento oficial
(CG OptiMaxx plus Art. 151, registro CNSF S0003-0247-2018; convertido en
`data/processed/`, PDF original en `data/raw/` — no versionado, descarga en el
README §7) y toda cifra fiscal lleva su año.
Si algo no está en el documento o en este archivo, dilo y búscalo/derívalo.

## Estado del modelo: AUDITORÍA + C7 2026-09-29 (leer primero)

Las correcciones de la auditoría **ya están aplicadas**: `src/sim_ppr_vs_vuaa.py`
es el modelo vigente y la única implementación (`sim_ppr`, `sim_vuaa`), y las
gráficas, el Excel, los JSON y el README están regenerados. `src/auditoria.py`
documenta la cascada desde la primera versión (números viejos) hasta la actual,
con check en ambos extremos. Cualquier cifra de la primera versión que veas en
la bitácora local (`NOTES.md`, no versionada) o en el historial está superada.

Correcciones clave de la auditoría (detalle y fuentes en `src/auditoria.py`):

- **C1 — Bono de Fidelidad (el error más grande).** Es 75% de la aportación
  comprometida del **primer año** (60k × 75% = 45,000 MXN en total), generado
  pro rata con los pagos (150/mes durante el Plazo Comprometido). NO es 75% de
  cada aportación anual (eso lo sobreestimaba ~25x). Fuentes: CG 3.6 (bonificación
  *parcial* de cargos) y folleto Allianz ("hasta el 100% de tus aportaciones
  comprometidas del primer año").
- **C2** El Fondo de Bono también paga cargo administrativo y de gestión (CG 3.10.3).
- **C3 — Exención de salida del PPR.** Retiro único exento hasta **90 UMA
  elevadas al año** (RLISR art. 171, aplicable al PPR por regla 3.17.6 RMF;
  ~$3.85M en 2026, ~$18.5M al año 40), no 90 UMA diarias. El excedente tributa
  "en términos del art. 95" (tasa efectiva; ver sensibilidad configurable en
  `src/sim_sensibilidad_fiscal.py`). La regla 3.17.6.V exige considerar también
  otras pensiones; el caso base supone toda la exención disponible. Validar con
  contador el cálculo personal del excedente y los otros ingresos del retiro.
- **C4** La base de costo del VUAA SÍ se actualiza por inflación (Art. 129 LISR).
- **C5/C6** El versus se reporta con el VUAA en **mismos aportes** y en **mismo
  bolsillo** (la justa), y la depreciación del peso es compuesta (11.65% en MXN).
- **C7** El OCF vigente del VUAA es 0.07% (Vanguard México, 2026); el Excel y
  la consola reportan compra, OCF y venta en el costo total del ETF.
- **Bug corregido en la fase 4%:** la base de costo no crece con el mercado
  (`b *= 1 + r_nom` era el bug); crece con la inflación (Art. 129).
- **Lectura corregida del versus:** el VUAA sigue ganando casi todo, pero **por
  los cargos del PPR** (gestión ~1.39%/año efectivo sobre todo el fondo durante
  40 años), no por el ISR de salida (que casi desaparece con la exención C3).
  El bono NO compensa los cargos. La variable decisiva son los cargos reales de
  la carátula de la póliza.
- Resultados vigentes (neto año 40, peso estable / -1.5%): PPR tope 19.2 / 26.1
  · PPR mitad 23.2 / 32.3 · VUAA mismos aportes 30.5 / 47.7 · VUAA mismo bolsillo
  25.1 / 39.4 · Híbrido (5k PPR + devolución al VUAA) 20.8-25.3 / 30.4-35.7.
  Empate con VUAA mismo bolsillo: PPR con cargos al 31% / 11% de los topes;
  híbrido al 53% / 25%.

## Preguntas sobre el PPR: usa el RAG

El documento convertido está en `data/processed/*.md` (76 páginas → 83 chunks
por sección numerada). Consulta con el índice híbrido BM25+embeddings:

```bash
.venv/Scripts/python.exe src/rag.py search "cargo por retiro parcial" -k 5
.venv/Scripts/python.exe src/rag.py show <chunk_id>   # texto completo del chunk
```

- Si `index/` no existe o el RAG pide reconstruirlo por cambio de documento:
  `src/rag.py build` primero (usa fastembed, sin torch). El índice verifica la
  huella de la CG y no elige un Markdown alternativo arbitrario.
- Fallback si el RAG falla: `grep -n "<término>" data/processed/*.md`.
- **Cita siempre la sección** (ej. "cláusula 3.14.1") — es el ancla verificable.
- Para el bono y material comercial, contrasta CG con el folleto oficial de
  Allianz (`Folleto - PLUS.pdf`; URL de descarga en el README, §7): la CG manda
  en conflicto.
- Estructura del documento: secciones 1-2 (intro/coberturas), 3.x (el core:
  aportaciones, bono, cargos, retiros, fiscal), 4-5 (definiciones/cláusulas),
  7-8 (otras cláusulas/glosario), 9-10 (transcripción de artículos LISR, contacto).

### Cifras de referencia verificadas (2026)

- Cargos PPR (topes, "hasta", +16% IVA): administrativo 1.5% trimestral sobre
  el Fondo Inicial (aportaciones de los primeros 18 meses) durante el Plazo
  Comprometido; gestión 0.1% mensual sobre el fondo total; fijo 25 UDIS/mes
  desde el mes 19 (cláusula 3.12). Efectivo combinado de la gestión ≈1.39%/año
  con IVA sobre todo el fondo.
- Plazo Comprometido: 5 a 25 años máximo (3.1). Plazo Inicial: primeros 18 meses.
  Solo se puede seguir aportando a la misma póliza tras el plazo si fue de 25
  años; con un plazo menor se requiere otra póliza (3.1).
- Bono de Fidelidad (3.6 + folleto): % de la aportación comprometida del
  **primer año** según tabla (75% para 60k/año, plazo >=20 años); acumula a
  inflación+5% (tope 9%); se acredita solo al cumplir el Plazo Comprometido
  (condiciones 3.6 a/b). Las Aportaciones Adicionales (p.ej. la devolución del
  SAT) no cuentan para el bono.
- Retiro total antes del plazo (3.14.2): cobro diferido de los cargos restantes
  + 1% por retiro. Fuera del plazo (3.14.3): sin cargo.
- Salida fiscal del PPR (3.21.1): retiro único tratado como pensión; exención
  90 UMA anuales (RLISR 171 / RMF 3.17.6); excedente según art. 95. Aportaciones
  deducidas → el excedente sobre la exención es gravable.
- Salida VUAA: 10% definitivo sobre la ganancia (Art. 129 LISR), base de costo
  actualizable por inflación, retención por la casa de bolsa.
- Fiscal 2026: tarifa anual ISR (marginal 23.52% en 424k-669k); deducción PPR =
  min(10% del ingreso, 5 UMA anuales) → devolución 14,112/año con 600k de
  ingreso y 60k aportados; UMA $117.31/día; UDI $8.826356.
- VUAA: OCF 0.07% (Vanguard México, 2026); corretaje 0.25% + IVA por operación
  es un supuesto de intermediario, incluye compra y venta.

## Simulaciones y comparativos

El modelo vive en `src/sim_ppr_vs_vuaa.py`: `sim_ppr(gross, fee_scale,
con_refund=True, config=Parametros(...))` y `sim_vuaa(gross,
con_refund=True, costos=1.0, config=Parametros(...))`; `FX` trae los dos
escenarios cambiarios. Para escenarios nuevos, **importa esas funciones**;
no copies el lazo mensual (así se propagó el error del bono a tres scripts).

```bash
.venv/Scripts/python.exe src/generar_todo.py     # Excel completo, JSON, PNG y auditoría
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe src/sim_sensibilidad_fiscal.py  # exención 0/50/100%, tarifa/Art.95
```

Perillas habituales: `gross_anual` (rendimiento), `fee_scale` (tope vs mitad; 0 =
sin cargos), `con_refund` (devolución al plan o no), `costos` del VUAA y
`Parametros(aportacion_mensual, ingreso_anual, edad_inicial, meses, mes_inicio,
plazo_comprometido, exencion_ya_usada_mxn, metodo_isr_retiro, ...)`. La
devolución y el porcentaje del bono se derivan de las entradas.
Para un "versus" nuevo (otro ETF, otro ingreso, aportes crecientes, retiro a los
60): crea `src/sim_<nombre>.py` siguiendo los patrones existentes. El modelo
rechaza el retiro PPR antes de 65 porque falta el tratamiento de retiro
anticipado de la cláusula 3.21.2; implémentalo para ese escenario antes de
publicar un neto.

### Reglas de modelado

1. **Declara cada supuesto** en la respuesta y en el docstring: rendimiento, tipo
   de cambio, inflación, tarifas fiscales (congeladas en 2026 nominal — decirlo
   siempre), cargos al tope vs mitad.
2. Define el marco de comparación y dilo: **mismos aportes totales** o **mismo
   desembolso de bolsillo** (dan resultados distintos; la auditoría reporta
   ambos, y el híbrido "5k al PPR + devolución al VUAA").
3. Cifras nominales MXN por defecto; si comparas entre décadas, presenta también
   pesos de hoy (deflacta a 4% con `INFLACION`; deflactor año por año, no un
   promedio).
4. La devolución del SAT (14,112/año con 600k de ingreso) llega y se invierte en
   junio del año siguiente (meses 18, 30, ..., 474; 39 pagos si se inicia en
   enero). El modelo calcula el primer año parcial si cambia `mes_inicio`, con
   tarifa 2026 congelada; no vuelve a deducir el reembolso reinvertido.
5. Todo resultado va a `outputs/` (PNG en `outputs/graficas/`, JSON con prefijo
   `resultados_`). Nombres numerados siguiendo los existentes (07, 08, ...).
6. **Revisa cada gráfica nueva con el modelo de visión antes de entregarla** —
   en este proyecto ha encontrado etiquetas cruzadas, leyendas sobre barras y
   texto en modo matemático por `$` sin escapar (usa `\\$` en matplotlib).
   Y evita los vicios detectados en las gráficas 01/03/06: no apiles ISR sobre
   el saldo como si fuera riqueza, no muestres el Fondo de Bono como disponible
   antes del año 25, y no compares cargos nominales sin capitalizar.
7. Actualiza la bitácora local `NOTES.md` (no versionada) con hallazgos y
   decisiones al terminar cada escenario.

## Entorno

Windows + Git Bash. Python del proyecto: `.venv/Scripts/python.exe` (creado con
`uv venv --python 3.12`; instalar con `uv pip install --python
.venv/Scripts/python.exe -r requirements.txt`). fastembed descarga el modelo la
primera vez (~120 MB). Para reconvertir el PDF: `docling convert data/raw/*.pdf
--to md --output data/processed --image-export-mode placeholder`. Orden del
pipeline completo en `README.md`.

## Tono

Español, directo, con conclusión al inicio. El usuario no es actuario: explica
el mecanismo en una frase y da el número; deja los supuestos visibles y
separados del resultado. Este repo es educativo, no asesoría financiera.
