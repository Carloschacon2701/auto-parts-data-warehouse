-- Pregunta 4: ¿Cuál es el margen de ganancia por producto, marca y categoría?
--
-- Margen realizado = ingreso efectivamente facturado (USD) - costo de la mercancía
-- vendida (unidades vendidas * costo_usd del producto).
-- Se resuelven los tres niveles en una sola tabla usando GROUPING SETS; la columna
-- `nivel` indica a qué agregación corresponde cada fila.

DROP TABLE IF EXISTS marts.p04_margen;

CREATE TABLE marts.p04_margen AS
SELECT
    CASE
        WHEN GROUPING(dp.codigo) = 0 THEN 'PRODUCTO'
        WHEN GROUPING(dp.marca)  = 0 THEN 'MARCA'
        ELSE 'CATEGORIA'
    END                                          AS nivel,
    dp.categoria,
    dp.marca,
    dp.codigo,
    MAX(dp.descripcion)                          AS descripcion,
    SUM(fv.cantidad)                             AS unidades_vendidas,
    ROUND(SUM(fv.subtotal_usd), 2)               AS ingreso_usd,
    ROUND(SUM(fv.cantidad * dp.costo_usd), 2)    AS costo_mercancia_usd,
    ROUND(SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd), 2) AS margen_usd,
    ROUND(
        100 * (SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd))
            / NULLIF(SUM(fv.subtotal_usd), 0)
    , 2)                                         AS margen_pct_sobre_ingreso,
    ROUND(
        100 * (SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd))
            / NULLIF(SUM(fv.cantidad * dp.costo_usd), 0)
    , 2)                                         AS markup_pct_sobre_costo
FROM core.fact_ventas fv
INNER JOIN core.dim_producto dp
    ON dp.sk_producto = fv.sk_producto
GROUP BY GROUPING SETS (
    (dp.categoria, dp.marca, dp.codigo),
    (dp.marca),
    (dp.categoria)
)
ORDER BY nivel, margen_usd DESC;
