-- Pregunta 13: ¿Cómo evolucionan las ventas por día, semana, mes y año?
--
-- Una sola tabla con las cuatro granularidades apiladas (columna `granularidad`),
-- más la variación respecto al período anterior dentro de cada granularidad.

DROP TABLE IF EXISTS marts.p13_evolucion_ventas;

CREATE TABLE marts.p13_evolucion_ventas AS
WITH ventas AS (
    SELECT
        dt.fecha,
        fv.nro_factura,
        fv.cantidad,
        fv.subtotal_usd,
        fv.cantidad * dp.costo_usd AS costo_usd
    FROM core.fact_ventas fv
    INNER JOIN core.dim_tiempo   dt ON dt.sk_fecha    = fv.sk_fecha
    INNER JOIN core.dim_producto dp ON dp.sk_producto = fv.sk_producto
),
apilado AS (
    SELECT 'DIA' AS granularidad, fecha AS periodo_inicio,
           TO_CHAR(fecha, 'YYYY-MM-DD') AS periodo, v.*
    FROM ventas v
    UNION ALL
    SELECT 'SEMANA', DATE_TRUNC('week', fecha)::DATE,
           TO_CHAR(fecha, 'IYYY-"S"IW'), v.*
    FROM ventas v
    UNION ALL
    SELECT 'MES', DATE_TRUNC('month', fecha)::DATE,
           TO_CHAR(fecha, 'YYYY-MM'), v.*
    FROM ventas v
    UNION ALL
    SELECT 'ANIO', DATE_TRUNC('year', fecha)::DATE,
           TO_CHAR(fecha, 'YYYY'), v.*
    FROM ventas v
),
agregado AS (
    SELECT
        granularidad,
        periodo,
        MIN(periodo_inicio)                          AS periodo_inicio,
        COUNT(DISTINCT nro_factura)                  AS nro_facturas,
        COUNT(DISTINCT fecha)                        AS dias_con_ventas,
        SUM(cantidad)                                AS unidades_vendidas,
        ROUND(SUM(subtotal_usd), 2)                  AS ingreso_usd,
        ROUND(SUM(subtotal_usd) - SUM(costo_usd), 2) AS margen_usd,
        ROUND(SUM(subtotal_usd) / NULLIF(COUNT(DISTINCT nro_factura), 0), 2) AS ticket_promedio_usd
    FROM apilado
    GROUP BY granularidad, periodo
)
SELECT
    a.*,
    LAG(a.ingreso_usd) OVER w AS ingreso_usd_periodo_anterior,
    ROUND(
        100 * (a.ingreso_usd - LAG(a.ingreso_usd) OVER w)
            / NULLIF(LAG(a.ingreso_usd) OVER w, 0)
    , 2) AS variacion_pct_vs_periodo_anterior,
    ROUND(
        SUM(a.ingreso_usd) OVER (
            PARTITION BY a.granularidad ORDER BY a.periodo_inicio
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )
    , 2) AS ingreso_acumulado_usd
FROM agregado a
WINDOW w AS (PARTITION BY a.granularidad ORDER BY a.periodo_inicio)
ORDER BY a.granularidad, a.periodo_inicio;
