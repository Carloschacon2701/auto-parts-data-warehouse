-- Pregunta 19: ¿Cómo afecta la variación del tipo de cambio a los ingresos
--              y márgenes de ganancia?
--
-- Se construye una serie mensual con la tasa promedio (Bs/USD y COP/USD), su
-- variación porcentual mes a mes, y en paralelo el ingreso, costo y margen en USD.
-- Además se separa el ingreso según la moneda de cobro, que es donde el tipo de
-- cambio realmente muerde: una venta en Bs se convierte a USD a la tasa del día,
-- así que una devaluación entre la fijación del precio y el cobro erosiona el margen.

DROP TABLE IF EXISTS marts.p19_tipo_cambio_mensual;

CREATE TABLE marts.p19_tipo_cambio_mensual AS
WITH ventas AS (
    SELECT
        DATE_TRUNC('month', dt.fecha)::DATE AS mes_inicio,
        dt.fecha,
        dt.tasa_bs_usd,
        dt.cop_por_usd,
        dm.codigo AS moneda,
        fv.nro_factura,
        fv.cantidad,
        fv.subtotal_usd,
        fv.cantidad * dp.costo_usd AS costo_usd
    FROM core.fact_ventas fv
    INNER JOIN core.dim_tiempo   dt ON dt.sk_fecha    = fv.sk_fecha
    INNER JOIN core.dim_producto dp ON dp.sk_producto = fv.sk_producto
    INNER JOIN core.dim_moneda   dm ON dm.sk_moneda   = fv.sk_moneda
),
tasas_mes AS (
    -- La tasa se promedia sobre el calendario completo, no ponderada por ventas.
    SELECT
        DATE_TRUNC('month', fecha)::DATE     AS mes_inicio,
        ROUND(AVG(tasa_bs_usd)::NUMERIC, 4)  AS tasa_bs_usd_prom,
        ROUND(MIN(tasa_bs_usd)::NUMERIC, 4)  AS tasa_bs_usd_min,
        ROUND(MAX(tasa_bs_usd)::NUMERIC, 4)  AS tasa_bs_usd_max,
        ROUND(AVG(cop_por_usd)::NUMERIC, 4)  AS cop_por_usd_prom
    FROM core.dim_tiempo
    GROUP BY DATE_TRUNC('month', fecha)
),
ventas_mes AS (
    SELECT
        mes_inicio,
        COUNT(DISTINCT nro_factura)                  AS nro_facturas,
        SUM(cantidad)                                AS unidades_vendidas,
        ROUND(SUM(subtotal_usd), 2)                  AS ingreso_usd,
        ROUND(SUM(costo_usd), 2)                     AS costo_usd,
        ROUND(SUM(subtotal_usd) - SUM(costo_usd), 2) AS margen_usd,
        ROUND(
            100 * (SUM(subtotal_usd) - SUM(costo_usd)) / NULLIF(SUM(subtotal_usd), 0)
        , 2)                                         AS margen_pct,
        ROUND(SUM(subtotal_usd) FILTER (WHERE moneda = 'BS'), 2)  AS ingreso_usd_cobrado_en_bs,
        ROUND(SUM(subtotal_usd) FILTER (WHERE moneda = 'USD'), 2) AS ingreso_usd_cobrado_en_usd,
        ROUND(SUM(subtotal_usd) FILTER (WHERE moneda = 'COP'), 2) AS ingreso_usd_cobrado_en_cop,
        ROUND(
            100 * COALESCE(SUM(subtotal_usd) FILTER (WHERE moneda <> 'USD'), 0)
                / NULLIF(SUM(subtotal_usd), 0)
        , 2)                                         AS pct_ingreso_expuesto_a_fx
    FROM ventas
    GROUP BY mes_inicio
),
unido AS (
    SELECT
        TO_CHAR(vm.mes_inicio, 'YYYY-MM') AS mes,
        vm.mes_inicio,
        tm.tasa_bs_usd_prom,
        tm.tasa_bs_usd_min,
        tm.tasa_bs_usd_max,
        tm.cop_por_usd_prom,
        vm.nro_facturas,
        vm.unidades_vendidas,
        vm.ingreso_usd,
        vm.costo_usd,
        vm.margen_usd,
        vm.margen_pct,
        vm.ingreso_usd_cobrado_en_bs,
        vm.ingreso_usd_cobrado_en_usd,
        vm.ingreso_usd_cobrado_en_cop,
        vm.pct_ingreso_expuesto_a_fx
    FROM ventas_mes vm
    INNER JOIN tasas_mes tm ON tm.mes_inicio = vm.mes_inicio
)
SELECT
    u.*,
    ROUND(
        100 * (u.tasa_bs_usd_prom - LAG(u.tasa_bs_usd_prom) OVER w)
            / NULLIF(LAG(u.tasa_bs_usd_prom) OVER w, 0)
    , 2) AS var_pct_tasa_bs_usd,
    ROUND(
        100 * (u.cop_por_usd_prom - LAG(u.cop_por_usd_prom) OVER w)
            / NULLIF(LAG(u.cop_por_usd_prom) OVER w, 0)
    , 2) AS var_pct_tasa_cop_usd,
    ROUND(
        100 * (u.ingreso_usd - LAG(u.ingreso_usd) OVER w)
            / NULLIF(LAG(u.ingreso_usd) OVER w, 0)
    , 2) AS var_pct_ingreso_usd,
    ROUND(
        100 * (u.margen_usd - LAG(u.margen_usd) OVER w)
            / NULLIF(LAG(u.margen_usd) OVER w, 0)
    , 2) AS var_pct_margen_usd,
    ROUND(u.margen_pct - LAG(u.margen_pct) OVER w, 2) AS delta_puntos_margen_pct,
    -- Volatilidad intramensual de la tasa: cuánto se movió dentro del propio mes.
    ROUND(
        100 * (u.tasa_bs_usd_max - u.tasa_bs_usd_min) / NULLIF(u.tasa_bs_usd_min, 0)
    , 2) AS amplitud_pct_tasa_bs_en_el_mes
FROM unido u
WINDOW w AS (ORDER BY u.mes_inicio)
ORDER BY u.mes_inicio;


-- Correlación entre la variación de la tasa y los resultados del mes.
-- |r| cercano a 1 indica relación fuerte; el signo indica la dirección.
DROP TABLE IF EXISTS marts.p19_correlacion_fx;

CREATE TABLE marts.p19_correlacion_fx AS
SELECT
    COUNT(*) FILTER (WHERE var_pct_tasa_bs_usd IS NOT NULL) AS meses_comparables,
    ROUND(CORR(var_pct_tasa_bs_usd::FLOAT8, var_pct_ingreso_usd::FLOAT8)::NUMERIC, 4)
        AS corr_devaluacion_vs_var_ingreso,
    ROUND(CORR(var_pct_tasa_bs_usd::FLOAT8, var_pct_margen_usd::FLOAT8)::NUMERIC, 4)
        AS corr_devaluacion_vs_var_margen,
    ROUND(CORR(var_pct_tasa_bs_usd::FLOAT8, delta_puntos_margen_pct::FLOAT8)::NUMERIC, 4)
        AS corr_devaluacion_vs_delta_margen_pct,
    ROUND(CORR(var_pct_tasa_bs_usd::FLOAT8, pct_ingreso_expuesto_a_fx::FLOAT8)::NUMERIC, 4)
        AS corr_devaluacion_vs_exposicion_fx
FROM marts.p19_tipo_cambio_mensual;


-- Comparación directa: margen obtenido según la moneda en que se cobró la venta.
-- Es la lectura más concreta del impacto del tipo de cambio sobre la rentabilidad.
DROP TABLE IF EXISTS marts.p19_margen_por_moneda;

CREATE TABLE marts.p19_margen_por_moneda AS
SELECT
    dm.codigo                                    AS moneda,
    COUNT(DISTINCT fv.nro_factura)               AS nro_facturas,
    SUM(fv.cantidad)                             AS unidades_vendidas,
    ROUND(SUM(fv.subtotal_usd), 2)               AS ingreso_usd,
    ROUND(SUM(fv.cantidad * dp.costo_usd), 2)    AS costo_usd,
    ROUND(SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd), 2) AS margen_usd,
    ROUND(
        100 * (SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd))
            / NULLIF(SUM(fv.subtotal_usd), 0)
    , 2)                                         AS margen_pct,
    -- Precio realmente cobrado vs precio de lista en USD del producto.
    ROUND(
        100 * (SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.precio_venta_usd))
            / NULLIF(SUM(fv.cantidad * dp.precio_venta_usd), 0)
    , 2)                                         AS desvio_pct_vs_precio_lista_usd
FROM core.fact_ventas fv
INNER JOIN core.dim_producto dp ON dp.sk_producto = fv.sk_producto
INNER JOIN core.dim_moneda   dm ON dm.sk_moneda   = fv.sk_moneda
GROUP BY dm.codigo
ORDER BY margen_pct DESC;
