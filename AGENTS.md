# AGENTS.md — Asistente para OptiMaxx plus Art. 151

Este repositorio sirve para **consultar las Condiciones Generales del PPR
OptiMaxx plus de Allianz México** y para **crear simulaciones de ahorro y retiro**.
Responde en español, con la conclusión al inicio y los supuestos a la vista.
Explica el mecanismo en lenguaje sencillo antes de dar detalles técnicos.

## Fuentes y límites

- La fuente contractual es
  `data/processed/CG-OptiMaxx-plus-Art.151-CNSF-S0003-0247-2018.md`
  (Condiciones Generales, registro CNSF S0003-0247-2018). **Este Markdown está
  versionado.** El PDF original no se incluye; el README indica cómo obtenerlo
  del portal de Allianz. Si una conversión parece ambigua, verifica el PDF.
- Para la regla fiscal de retiro consulta también
  `data/processed/RMF-2026-regla-3.17.6.md`, versionada. Si la pregunta requiere
  legislación, UMA, UDI, tarifas o costos **vigentes**, verifica la fuente
  oficial actual y declara el año. No presentes una regla o tarifa de 2026 como
  si fuera automáticamente vigente en años posteriores.
- El folleto comercial de Allianz ayuda a interpretar el bono y publica cargos
  de 0.9% trimestral administrativo, 0.1% mensual de gestión y 15 UDIS/mes de
  cargo fijo. Son cifras publicadas para el producto, no prueba de la tarifa de
  una póliza individual. Las Condiciones Generales prevalecen ante una
  discrepancia. Los enlaces al folleto oficial están en el README.
  Antes de usar un PDF local comprueba que comienza con `%PDF-`: una respuesta
  de Cloudflare guardada con esa extensión puede ser HTML, no una fuente.
- `src/sim_ppr_vs_vuaa.py` es una **implementación de supuestos**, no una fuente
  contractual ni un cálculo fiscal personal. No inventes cláusulas, cargos
  efectivos de una póliza, rendimientos ni devoluciones del SAT. Si falta la
  carátula o un dato personal, identifica el supuesto que usas y su efecto.

## Cómo responder preguntas sobre el PPR

1. Busca primero la sección del contrato en el Markdown versionado. Puedes usar
   `rg -n "término" data/processed/CG-OptiMaxx-plus-Art.151-CNSF-S0003-0247-2018.md`.
   Si el índice RAG está disponible, usa `python src/rag.py search "consulta" -k 5`
   y `python src/rag.py show <chunk_id>`. Si falta `index/`, ejecuta
   `python src/rag.py build`; el índice es regenerable y no está versionado.
2. Lee el pasaje completo antes de concluir. **Cita la cláusula exacta** en la
   respuesta, por ejemplo «cláusula 3.14.2». Para afirmaciones fiscales cita
   también la regla o el artículo y el año aplicable.
3. Distingue entre lo que permite el contrato, lo que depende de la carátula y
   lo que solo supone el modelo. Si no hay base documental suficiente, dilo y
   señala qué documento o dato resolvería la duda.

Mapa de secciones útiles: **3.1** aportaciones y plazos; **3.6** Bono de
Fidelidad; **3.10.3 y 3.12** fondos y cargos; **3.14** retiros y cargos de salida;
**3.20** deducción; **3.21** tratamiento fiscal de retiros.

Puntos que suelen cambiar la respuesta:

- Los porcentajes de cargos de 3.12 son **topes («hasta»)**, no los cargos
  necesariamente contratados. El folleto publica 0.9% / 0.1% / 15 UDIS, que
  equivale al 60% / 100% / 60% de los tres topes. Para calcular un caso personal,
  pide la póliza y un desglose escrito de los cargos aplicables; no presupongas
  que la carátula por sí sola los enumera.
- El bono de 3.6 se calcula sobre la **aportación comprometida del primer año**,
  según monto y plazo; las aportaciones adicionales no elevan ese porcentaje.
  Los folletos 2023 y 2025 (p. 10) describen su generación durante el primer
  año; la CG 3.6 la vincula a los pagos de las Aportaciones Comprometidas. El
  modelo interpreta esta última como generación proporcional durante todo el
  plazo. Declara esa diferencia: no atribuyas los $150/mes al folleto.
  El Fondo de Bono paga cargos (3.10.3) y solo se acredita al cumplir el plazo y
  las condiciones de 3.6. Una vez acreditado, queda por defecto en renta fija de
  corto plazo hasta recibir instrucciones del titular (3.6).
- La cláusula 3.1 solo permite seguir aportando a **la misma póliza** después
  del Plazo Comprometido cuando este fue de 25 años. Con un plazo menor haría
  falta otra póliza. La cláusula 3.21 de este producto dispone un retiro en una
  ocasión y en su totalidad.
- La exención del retiro único puede compartirse con otras pensiones (RMF 2026,
  regla 3.17.6.V). El tratamiento del excedente requiere los datos fiscales del
  titular; presenta el artículo 95 solo como sensibilidad hasta validarlo para
  ese caso.

## Cómo crear simulaciones y comparativos

Antes de calcular, define **aportación, ingreso, edad y horizonte, plazo de la
póliza, rendimiento, tipo de cambio, inflación, cargos, costos del ETF y
tratamiento fiscal**. Di si comparas:

- **Mismo bolsillo:** ambos reciben el mismo dinero del titular; en el caso
  base, `sim_vuaa(..., con_refund=False)`.
- **Mismos aportes:** el VUAA recibe además el equivalente de la devolución que
  se reinvierte en el PPR; ese extra sale del bolsillo del titular en el VUAA;
  en el caso base, `sim_vuaa(..., con_refund=True)`.

El modelo vigente está en `src/sim_ppr_vs_vuaa.py`:

```python
from sim_ppr_vs_vuaa import Parametros, sim_ppr, sim_vuaa

cfg = Parametros(aportacion_mensual=10_000, ingreso_anual=600_000)
ppr = sim_ppr(0.10, fee_scale=1.0, config=cfg)
vuaa_mismo_bolsillo = sim_vuaa(0.10, con_refund=False, config=cfg)
```

Ejecuta ese código desde un script en `src/`, o añade `src/` al `PYTHONPATH`.
`fee_scale=1` usa los topes contractuales modelados, `0.5` la mitad de **cada**
cargo como sensibilidad hipotética y `0` mide el plan sin cargos. El folleto
mantiene la gestión al tope, así que `fee_scale=0.5` no representa su tarifa.
Para esa sensibilidad, usa `sim_ppr(0.10, TARIFA_FOLLETO_2025)` e importa la
constante del mismo módulo. `src/sim_tarifa_folleto.py` genera el JSON con ambos
escenarios cambiarios; no presenta esa mezcla de folleto 2025 y CG 2018 como
tarifa comprobada para una póliza.
`Parametros` deriva la devolución anual y el porcentaje del
bono de las entradas. El caso base del código usa aportación de 5,000 MXN/mes,
ingreso de 600,000 MXN/año, edad inicial 25, 40 años de horizonte y 25 años de
Plazo Comprometido. **La tarifa ISR 2026 queda congelada en pesos nominales**;
la devolución se invierte en junio del año siguiente. Las cifras son escenarios,
no pronósticos.

Para escenarios nuevos:

1. **Importa el modelo central.** Crea `src/sim_<tema>.py` para la salida del
   escenario; no copies el lazo mensual del PPR o VUAA. Si falta una perilla
   (por ejemplo, aportaciones crecientes), amplía el modelo central y prueba
   que el caso base conserva sus resultados.
2. Para otro ETF, verifica su índice, divisa, costo anual, corretaje y régimen
   fiscal. No cambies solo el rendimiento dejando implícitos el OCF y el ISR de
   VUAA. Para un retiro PPR antes de los 65 años o antes del Plazo Comprometido,
   implementa y verifica primero los cargos y el tratamiento fiscal aplicables;
   `sim_ppr` rechaza esos casos. Tampoco extiendas aportaciones a una póliza de
   plazo menor de 25 años después de su vencimiento.
3. Declara en el docstring y en la respuesta todos los supuestos, incluidos
   cargos al tope o a mitad, año de las reglas fiscales y marco de comparación.
   Presenta MXN nominales y, si comparas décadas, también pesos del año base
   deflactados año por año. Muestra una sensibilidad cuando una hipótesis pueda
   cambiar la conclusión.
4. Guarda JSON nuevos con prefijo `outputs/resultados_` y gráficas PNG en
   `outputs/graficas/` con el siguiente número disponible. Revisa visualmente
   cada gráfica: no presentes el Fondo de Bono como disponible antes del plazo,
   un saldo antes del retiro como valor de rescate, ni ISR como riqueza; compara
   costos capitalizados si hablas del efecto de cargos a largo plazo.
5. Añade pruebas para la lógica nueva, actualiza el README con los supuestos y
   resultados reproducibles, e incorpora el escenario a `src/generar_todo.py`
   cuando deba formar parte de los entregables estándar. Ese comando reconstruye
   el Excel completo; ejecutar `src/graficas_tablas.py` por separado lo recrea y
   puede quitar hojas añadidas por otros scripts.

## Verificación y entrega

Instala `requirements.txt` en Python 3.12. En Windows, la ruta del intérprete
del proyecto es `.venv/Scripts/python.exe`; en Unix, `.venv/bin/python`. Para
reproducir los entregables estándar y comprobar el modelo:

```bash
python src/generar_todo.py
python -m unittest discover -s tests -v
```

El RAG puede descargar su modelo de embeddings la primera vez. Para preguntas
puntuales basta leer el Markdown versionado; no hace falta regenerar gráficas.
En la respuesta final, separa **resultado, supuestos y límites**. Este proyecto
es educativo y no sustituye la revisión de la póliza ni el cálculo fiscal
individual.
