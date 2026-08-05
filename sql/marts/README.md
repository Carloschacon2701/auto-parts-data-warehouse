# Marts

Cada archivo `.sql` de esta carpeta materializa una o más tablas en el esquema
`marts` que responden a una pregunta de negocio. `run_pipeline.py` los ejecuta en
orden alfabético después de `sql/core/`, así que el prefijo numérico importa.

Convención de nombres de tabla: `p<NN>_<tema>`, donde `NN` es el número de la
pregunta en el índice del profesor.

| Archivo | Pregunta | Tablas generadas |
|---|---|---|
| `01-schema.sql` | — | crea el esquema `marts` |
| `02_p01_top_productos.sql` | **1.** ¿Cuáles son los 10 repuestos más vendidos por cantidad y por monto? | `p01_top_productos` |
| `03_p04_margen.sql` | **4.** ¿Cuál es el margen de ganancia por producto, marca y categoría? | `p04_margen` |
| `04_p06_inventario_muerto.sql` | **6.** ¿Qué productos llevan más tiempo sin venderse y cuánto capital inmovilizan? | `p06_inventario_muerto`, `p06_inventario_muerto_resumen` |
| `05_p13_evolucion_ventas.sql` | **13.** ¿Cómo evolucionan las ventas por día, semana, mes y año? | `p13_evolucion_ventas` |
| `06_p15_dias_feriados.sql` | **15.** ¿Qué días de la semana o feriados presentan mayor volumen de ventas? | `p15_ventas_por_dia_semana`, `p15_ventas_feriado_vs_normal`, `p15_ventas_por_feriado` |
| `07_p16_ticket_tipo_cliente.sql` | **16.** ¿Cuál es el ticket promedio por tipo de cliente? | `p16_ticket_por_tipo_cliente` |
| `08_p18_mix_monedas.sql` | **18.** ¿Qué porcentaje de las ventas se realiza en Bs, USD y COP? | `p18_mix_monedas`, `p18_mix_monedas_mensual` |
| `09_p19_impacto_tipo_cambio.sql` | **19.** ¿Cómo afecta la variación del tipo de cambio a los ingresos y márgenes? | `p19_tipo_cambio_mensual`, `p19_correlacion_fx`, `p19_margen_por_moneda` |

## Criterios de cálculo comunes

- **Ingreso**: `fact_ventas.subtotal_usd`, ya normalizado a USD en `core` con la tasa
  del día de la venta (`dim_tiempo`). Todas las medidas del hecho van en USD; la
  moneda en que se cobró es contexto y vive en `dim_moneda`.
- **Margen realizado**: `subtotal_usd - (cantidad * dim_producto.costo_usd)`. Es el
  margen de lo efectivamente vendido, no el margen teórico de la lista de precios.
- **Ticket**: total de la **factura** (`nro_factura`), no de la línea. Por eso las
  consultas de ticket consolidan primero a nivel de factura.
- **Fecha de corte**: la última fecha con ventas registradas en el DWH. Se usa como
  "hoy" en la pregunta 6 para no depender de `CURRENT_DATE`.
- **Tipo de cliente** (pregunta 16): se deriva del prefijo del documento —
  `J` = taller/empresa, `V` = particular, `E` = extranjero.

## Informe PDF

`python reports/generate_report.py` consulta estas tablas y genera
`reports/Informe_Preguntas_Negocio.pdf`, con la respuesta desarrollada a cada
pregunta: gráficos, tablas de resultados e interpretación. Si cambian los datos o
las consultas, basta volver a correr el pipeline y regenerar el informe.

## Consultar los resultados

```sql
SELECT * FROM marts.p01_top_productos ORDER BY ranking_por_cantidad;
SELECT * FROM marts.p04_margen WHERE nivel = 'CATEGORIA' ORDER BY margen_usd DESC;
SELECT * FROM marts.p06_inventario_muerto WHERE es_inventario_muerto ORDER BY capital_inmovilizado_usd DESC;
SELECT * FROM marts.p13_evolucion_ventas WHERE granularidad = 'MES' ORDER BY periodo_inicio;
SELECT * FROM marts.p15_ventas_por_dia_semana ORDER BY ranking_ingreso_promedio;
SELECT * FROM marts.p16_ticket_por_tipo_cliente ORDER BY ticket_promedio_usd DESC;
SELECT * FROM marts.p18_mix_monedas ORDER BY pct_por_monto DESC;
SELECT * FROM marts.p19_tipo_cambio_mensual ORDER BY mes_inicio;
```
