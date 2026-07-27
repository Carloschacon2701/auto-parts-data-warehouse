-- Pregunta 1: ¿Cuáles son los 10 repuestos más vendidos por cantidad y por monto?
--
-- Se calcula el acumulado de unidades e ingreso (USD) por producto y se rankea
-- por ambas métricas. La tabla conserva los productos que entran en el top 10 de
-- al menos uno de los dos rankings, para poder comparar ambas lecturas.

DROP TABLE IF EXISTS marts.p01_top_productos;

CREATE TABLE marts.p01_top_productos AS
WITH ventas_producto AS (
    SELECT
        dp.codigo,
        dp.descripcion,
        dp.marca,
        dp.categoria,
        SUM(fv.cantidad)                    AS unidades_vendidas,
        ROUND(SUM(fv.subtotal_usd), 2)      AS monto_vendido_usd,
        COUNT(DISTINCT fv.nro_factura)      AS nro_facturas,
        ROUND(AVG(fv.subtotal_usd / NULLIF(fv.cantidad, 0)), 2) AS precio_prom_usd
    FROM core.fact_ventas fv
    INNER JOIN core.dim_producto dp
        ON dp.sk_producto = fv.sk_producto
    GROUP BY dp.codigo, dp.descripcion, dp.marca, dp.categoria
),
rankeadas AS (
    SELECT
        vp.*,
        RANK() OVER (ORDER BY vp.unidades_vendidas DESC) AS ranking_por_cantidad,
        RANK() OVER (ORDER BY vp.monto_vendido_usd DESC) AS ranking_por_monto
    FROM ventas_producto vp
)
SELECT
    ranking_por_cantidad,
    ranking_por_monto,
    codigo,
    descripcion,
    marca,
    categoria,
    unidades_vendidas,
    monto_vendido_usd,
    nro_facturas,
    precio_prom_usd,
    (ranking_por_cantidad <= 10) AS top10_por_cantidad,
    (ranking_por_monto    <= 10) AS top10_por_monto
FROM rankeadas
WHERE ranking_por_cantidad <= 10
   OR ranking_por_monto    <= 10
ORDER BY ranking_por_cantidad, ranking_por_monto;
