-- Pregunta 15: ¿Qué días de la semana o feriados presentan mayor volumen de ventas?
--
-- Se reportan totales Y promedio por día calendario, porque los totales crudos
-- favorecen al día de la semana que más veces aparece en el período analizado.

-- 15.a) Volumen por día de la semana.
DROP TABLE IF EXISTS marts.p15_ventas_por_dia_semana;

CREATE TABLE marts.p15_ventas_por_dia_semana AS
WITH ventas AS (
    SELECT
        dt.fecha,
        dt.dia_semana,
        dt.es_fin_de_semana,
        fv.nro_factura,
        fv.cantidad,
        fv.subtotal_usd
    FROM core.fact_ventas fv
    INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fv.sk_fecha
)
SELECT
    dia_semana,
    CASE dia_semana
        WHEN 1 THEN 'Lunes'
        WHEN 2 THEN 'Martes'
        WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves'
        WHEN 5 THEN 'Viernes'
        WHEN 6 THEN 'Sábado'
        WHEN 7 THEN 'Domingo'
    END                                          AS nombre_dia,
    BOOL_OR(es_fin_de_semana)                    AS es_fin_de_semana,
    COUNT(DISTINCT fecha)                        AS dias_con_ventas,
    COUNT(DISTINCT nro_factura)                  AS nro_facturas,
    SUM(cantidad)                                AS unidades_vendidas,
    ROUND(SUM(subtotal_usd), 2)                  AS ingreso_usd,
    ROUND(SUM(subtotal_usd) / NULLIF(COUNT(DISTINCT fecha), 0), 2)      AS ingreso_prom_por_dia_usd,
    ROUND(SUM(subtotal_usd) / NULLIF(COUNT(DISTINCT nro_factura), 0), 2) AS ticket_promedio_usd,
    ROUND(100 * SUM(subtotal_usd) / NULLIF(SUM(SUM(subtotal_usd)) OVER (), 0), 2) AS pct_del_ingreso_total,
    RANK() OVER (ORDER BY SUM(subtotal_usd) DESC) AS ranking_ingreso_total,
    RANK() OVER (
        ORDER BY SUM(subtotal_usd) / NULLIF(COUNT(DISTINCT fecha), 0) DESC
    )                                            AS ranking_ingreso_promedio
FROM ventas
GROUP BY dia_semana
ORDER BY dia_semana;


-- 15.b) Feriado vs día laborable / fin de semana.
DROP TABLE IF EXISTS marts.p15_ventas_feriado_vs_normal;

CREATE TABLE marts.p15_ventas_feriado_vs_normal AS
WITH ventas AS (
    SELECT
        dt.fecha,
        dt.es_feriado,
        dt.es_fin_de_semana,
        fv.nro_factura,
        fv.cantidad,
        fv.subtotal_usd
    FROM core.fact_ventas fv
    INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fv.sk_fecha
)
SELECT
    CASE
        WHEN es_feriado                        THEN 'FERIADO'
        WHEN es_fin_de_semana                  THEN 'FIN DE SEMANA'
        ELSE                                        'DIA LABORABLE'
    END                                          AS tipo_dia,
    COUNT(DISTINCT fecha)                        AS dias_con_ventas,
    COUNT(DISTINCT nro_factura)                  AS nro_facturas,
    SUM(cantidad)                                AS unidades_vendidas,
    ROUND(SUM(subtotal_usd), 2)                  AS ingreso_usd,
    ROUND(SUM(subtotal_usd) / NULLIF(COUNT(DISTINCT fecha), 0), 2)       AS ingreso_prom_por_dia_usd,
    ROUND(SUM(subtotal_usd) / NULLIF(COUNT(DISTINCT nro_factura), 0), 2) AS ticket_promedio_usd,
    ROUND(100 * SUM(subtotal_usd) / NULLIF(SUM(SUM(subtotal_usd)) OVER (), 0), 2) AS pct_del_ingreso_total
FROM ventas
GROUP BY 1
ORDER BY ingreso_prom_por_dia_usd DESC;


-- 15.c) Detalle por feriado (qué feriado concreto vende más).
DROP TABLE IF EXISTS marts.p15_ventas_por_feriado;

CREATE TABLE marts.p15_ventas_por_feriado AS
SELECT
    dt.nombre_feriado,
    COUNT(DISTINCT dt.fecha)                     AS dias_con_ventas,
    MIN(dt.fecha)                                AS primera_fecha,
    MAX(dt.fecha)                                AS ultima_fecha,
    COUNT(DISTINCT fv.nro_factura)               AS nro_facturas,
    SUM(fv.cantidad)                             AS unidades_vendidas,
    ROUND(SUM(fv.subtotal_usd), 2)               AS ingreso_usd,
    ROUND(SUM(fv.subtotal_usd) / NULLIF(COUNT(DISTINCT dt.fecha), 0), 2) AS ingreso_prom_por_dia_usd
FROM core.fact_ventas fv
INNER JOIN core.dim_tiempo dt ON dt.sk_fecha = fv.sk_fecha
WHERE dt.es_feriado
GROUP BY dt.nombre_feriado
ORDER BY ingreso_usd DESC;
