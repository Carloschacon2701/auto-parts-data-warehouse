-- Pregunta 6: ¿Qué productos llevan más tiempo sin venderse (inventario muerto)
--             y cuánto capital inmovilizan?
--
-- - Stock actual: `stock_resultante` del último movimiento de inventario del producto.
-- - Días sin vender: días entre la última venta del producto y la fecha de corte
--   (última fecha con actividad de ventas en el DWH). Si nunca se vendió, se mide
--   desde su primer movimiento de inventario.
-- - Capital inmovilizado: stock actual * costo_usd.

DROP TABLE IF EXISTS marts.p06_inventario_muerto;

CREATE TABLE marts.p06_inventario_muerto AS
WITH corte AS (
    SELECT MAX(dt.fecha) AS fecha_corte
    FROM core.fact_ventas fv
    INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fv.sk_fecha
),
ultimo_movimiento AS (
    SELECT DISTINCT ON (fmi.sk_producto)
        fmi.sk_producto,
        fmi.stock_resultante,
        dt.fecha AS fecha_ultimo_movimiento
    FROM core.fact_mov_inventario fmi
    INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fmi.sk_fecha
    INNER JOIN core.dim_hora   dh ON dh.sk_hora  = fmi.sk_hora
    ORDER BY fmi.sk_producto, dt.fecha DESC, dh.hora DESC, fmi.sk_movimiento DESC
),
primer_movimiento AS (
    SELECT
        fmi.sk_producto,
        MIN(dt.fecha) AS fecha_primer_movimiento
    FROM core.fact_mov_inventario fmi
    INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fmi.sk_fecha
    GROUP BY fmi.sk_producto
),
ventas_producto AS (
    SELECT
        fv.sk_producto,
        MAX(dt.fecha)    AS fecha_ultima_venta,
        SUM(fv.cantidad) AS unidades_vendidas_hist
    FROM core.fact_ventas fv
    INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fv.sk_fecha
    GROUP BY fv.sk_producto
),
base AS (
    SELECT
        dp.codigo,
        dp.descripcion,
        dp.marca,
        dp.categoria,
        dp.ubicacion,
        dp.costo_usd,
        dp.precio_venta_usd,
        COALESCE(um.stock_resultante, 0) AS stock_actual,
        ROUND(COALESCE(um.stock_resultante, 0) * dp.costo_usd, 2) AS capital_inmovilizado_usd,
        um.fecha_ultimo_movimiento,
        vp.fecha_ultima_venta,
        COALESCE(vp.unidades_vendidas_hist, 0) AS unidades_vendidas_hist,
        c.fecha_corte,
        (c.fecha_corte - COALESCE(vp.fecha_ultima_venta, pm.fecha_primer_movimiento)) AS dias_sin_vender
    FROM core.dim_producto dp
    CROSS JOIN corte c
    LEFT JOIN ultimo_movimiento um ON um.sk_producto = dp.sk_producto
    LEFT JOIN primer_movimiento pm ON pm.sk_producto = dp.sk_producto
    LEFT JOIN ventas_producto   vp ON vp.sk_producto = dp.sk_producto
)
SELECT
    b.*,
    CASE
        WHEN b.fecha_ultima_venta IS NULL           THEN 'NUNCA VENDIDO'
        WHEN b.dias_sin_vender >= 180               THEN 'INVENTARIO MUERTO (180+ días)'
        WHEN b.dias_sin_vender >=  90               THEN 'LENTA ROTACIÓN (90-179 días)'
        WHEN b.dias_sin_vender >=  30               THEN 'ATENCIÓN (30-89 días)'
        ELSE                                             'ACTIVO'
    END AS clasificacion,
    (b.fecha_ultima_venta IS NULL OR b.dias_sin_vender >= 180) AS es_inventario_muerto
FROM base b
ORDER BY
    (b.fecha_ultima_venta IS NULL) DESC,
    b.dias_sin_vender DESC NULLS LAST,
    b.capital_inmovilizado_usd DESC;


-- Resumen ejecutivo: capital inmovilizado agregado por clasificación de rotación.
DROP TABLE IF EXISTS marts.p06_inventario_muerto_resumen;

CREATE TABLE marts.p06_inventario_muerto_resumen AS
SELECT
    clasificacion,
    COUNT(*)                                    AS nro_productos,
    SUM(stock_actual)                           AS unidades_en_stock,
    ROUND(SUM(capital_inmovilizado_usd), 2)     AS capital_inmovilizado_usd,
    ROUND(
        100 * SUM(capital_inmovilizado_usd)
            / NULLIF(SUM(SUM(capital_inmovilizado_usd)) OVER (), 0)
    , 2)                                        AS pct_del_capital_total,
    ROUND(AVG(dias_sin_vender), 1)              AS dias_sin_vender_prom
FROM marts.p06_inventario_muerto
GROUP BY clasificacion
ORDER BY capital_inmovilizado_usd DESC;
