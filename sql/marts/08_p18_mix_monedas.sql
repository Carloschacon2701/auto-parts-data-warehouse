-- Pregunta 18: ¿Qué porcentaje de las ventas se realiza en bolívares, dólares
--              y pesos colombianos?
--
-- Se reporta el porcentaje bajo tres lecturas distintas, porque no dan lo mismo:
--   - por monto facturado (normalizado a USD)
--   - por número de facturas
--   - por unidades despachadas
-- Todos los montos van en USD: `core.fact_ventas` ya no guarda el importe en la
-- moneda de cobro, esa información la aporta la dimensión moneda.

DROP TABLE IF EXISTS marts.p18_mix_monedas;

CREATE TABLE marts.p18_mix_monedas AS
SELECT
    dm.codigo                                    AS moneda,
    CASE dm.codigo
        WHEN 'BS'  THEN 'Bolívares'
        WHEN 'USD' THEN 'Dólares'
        WHEN 'COP' THEN 'Pesos colombianos'
        ELSE dm.codigo
    END                                          AS moneda_nombre,
    COUNT(DISTINCT fv.nro_factura)               AS nro_facturas,
    SUM(fv.cantidad)                             AS unidades_vendidas,
    ROUND(SUM(fv.subtotal_usd), 2)               AS ingreso_usd,
    ROUND(SUM(fv.subtotal_usd) / NULLIF(COUNT(DISTINCT fv.nro_factura), 0), 2) AS ticket_promedio_usd,
    ROUND(
        100 * SUM(fv.subtotal_usd) / NULLIF(SUM(SUM(fv.subtotal_usd)) OVER (), 0)
    , 2)                                         AS pct_por_monto,
    ROUND(
        100 * COUNT(DISTINCT fv.nro_factura)
            / NULLIF(SUM(COUNT(DISTINCT fv.nro_factura)) OVER (), 0)::NUMERIC
    , 2)                                         AS pct_por_nro_facturas,
    ROUND(
        100 * SUM(fv.cantidad) / NULLIF(SUM(SUM(fv.cantidad)) OVER (), 0)::NUMERIC
    , 2)                                         AS pct_por_unidades
FROM core.fact_ventas fv
INNER JOIN core.dim_moneda dm
    ON dm.sk_moneda = fv.sk_moneda
GROUP BY dm.codigo
ORDER BY ingreso_usd DESC;


-- Evolución mensual del mix de monedas (para ver si la dolarización avanza o retrocede).
DROP TABLE IF EXISTS marts.p18_mix_monedas_mensual;

CREATE TABLE marts.p18_mix_monedas_mensual AS
SELECT
    TO_CHAR(dt.fecha, 'YYYY-MM')                 AS mes,
    DATE_TRUNC('month', dt.fecha)::DATE          AS mes_inicio,
    dm.codigo                                    AS moneda,
    COUNT(DISTINCT fv.nro_factura)               AS nro_facturas,
    ROUND(SUM(fv.subtotal_usd), 2)               AS ingreso_usd,
    ROUND(
        100 * SUM(fv.subtotal_usd)
            / NULLIF(SUM(SUM(fv.subtotal_usd)) OVER (PARTITION BY DATE_TRUNC('month', dt.fecha)), 0)
    , 2)                                         AS pct_del_mes
FROM core.fact_ventas fv
INNER JOIN core.dim_tiempo dt ON dt.sk_fecha  = fv.sk_fecha
INNER JOIN core.dim_moneda dm ON dm.sk_moneda = fv.sk_moneda
GROUP BY DATE_TRUNC('month', dt.fecha), TO_CHAR(dt.fecha, 'YYYY-MM'), dm.codigo
ORDER BY mes_inicio, ingreso_usd DESC;
