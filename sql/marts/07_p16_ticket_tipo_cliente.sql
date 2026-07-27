-- Pregunta 16: ¿Cuál es el ticket promedio por tipo de cliente
--              (taller/empresa, particular, extranjero)?
--
-- El tipo se deriva del prefijo del documento cargado en core.dim_clientes:
--   J -> persona jurídica  = taller / empresa
--   V -> persona natural   = particular
--   E -> extranjero
-- El ticket es el total de la FACTURA, por eso primero se consolida fact_ventas
-- a nivel de nro_factura y luego se promedia.

DROP TABLE IF EXISTS marts.p16_ticket_por_tipo_cliente;

CREATE TABLE marts.p16_ticket_por_tipo_cliente AS
WITH facturas AS (
    SELECT
        fv.nro_factura,
        dc.tipo,
        COUNT(*)                       AS lineas,
        SUM(fv.cantidad)               AS unidades,
        ROUND(SUM(fv.subtotal_usd), 2) AS total_factura_usd
    FROM core.fact_ventas fv
    LEFT JOIN core.dim_clientes dc
        ON dc.sk_cliente = fv.sk_cliente
    GROUP BY fv.nro_factura, dc.tipo
)
SELECT
    COALESCE(tipo::TEXT, 'SD')                   AS codigo_tipo,
    CASE tipo
        WHEN 'J' THEN 'Taller / Empresa (jurídico)'
        WHEN 'V' THEN 'Particular (venezolano)'
        WHEN 'E' THEN 'Extranjero'
        ELSE          'Sin cliente identificado'
    END                                          AS tipo_cliente,
    COUNT(DISTINCT nro_factura)                  AS nro_facturas,
    ROUND(SUM(total_factura_usd), 2)             AS ingreso_total_usd,
    SUM(unidades)                                AS unidades_vendidas,
    ROUND(AVG(total_factura_usd), 2)             AS ticket_promedio_usd,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_factura_usd)::NUMERIC
    , 2)                                         AS ticket_mediano_usd,
    ROUND(MIN(total_factura_usd), 2)             AS ticket_minimo_usd,
    ROUND(MAX(total_factura_usd), 2)             AS ticket_maximo_usd,
    ROUND(AVG(lineas), 2)                        AS lineas_promedio_por_factura,
    ROUND(AVG(unidades), 2)                      AS unidades_promedio_por_factura,
    ROUND(
        100 * SUM(total_factura_usd)
            / NULLIF(SUM(SUM(total_factura_usd)) OVER (), 0)
    , 2)                                         AS pct_del_ingreso_total
FROM facturas
GROUP BY tipo
ORDER BY ticket_promedio_usd DESC;
