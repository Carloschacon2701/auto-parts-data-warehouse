-- Hecho de ventas. Grano: una fila por línea de detalle de factura.
--
-- Todas las medidas monetarias están expresadas en USD. La moneda en que se cobró
-- la venta es contexto, no medida, y por eso vive únicamente en la clave foránea
-- `sk_moneda`: guardar además el importe en la moneda de cobro duplicaba la misma
-- información y hacía que las columnas de monto no fueran sumables entre sí.
-- La conversión usa la tasa vigente el día de la venta (core.dim_tiempo).

DROP TABLE IF EXISTS core.fact_ventas;

CREATE TABLE core.fact_ventas (
    sk_venta          BIGSERIAL PRIMARY KEY,
    sk_fecha          BIGINT NOT NULL REFERENCES core.dim_tiempo(sk_fecha),
    sk_hora           BIGINT NOT NULL REFERENCES core.dim_hora(sk_hora),
    sk_producto       BIGINT NOT NULL REFERENCES core.dim_producto(sk_producto),
    sk_cliente        BIGINT REFERENCES core.dim_clientes(sk_cliente),
    sk_empleado       BIGINT REFERENCES core.dim_usuarios(sk_usuario),
    sk_moneda         BIGINT NOT NULL REFERENCES core.dim_moneda(sk_moneda),
    nro_factura       VARCHAR(50) NOT NULL,
    cantidad          INTEGER NOT NULL,
    precio_unit_usd   NUMERIC(14, 2) NOT NULL,
    subtotal_usd      NUMERIC(14, 2) NOT NULL
);

INSERT INTO core.fact_ventas (
    sk_fecha,
    sk_hora,
    sk_producto,
    sk_cliente,
    sk_empleado,
    sk_moneda,
    nro_factura,
    cantidad,
    precio_unit_usd,
    subtotal_usd
)
WITH ventas AS (
    SELECT
        dt.sk_fecha,
        dh.sk_hora,
        dpp.sk_producto,
        dc.sk_cliente,
        du.sk_usuario AS sk_empleado,
        dm.sk_moneda,
        svd.numero AS nro_factura,
        svd.cantidad,
        svd.precio_unitario,
        svd.subtotal,
        -- Unidades de la moneda de cobro que equivalen a 1 USD ese día.
        CASE svh.moneda
            WHEN 'COP' THEN dt.cop_por_usd
            WHEN 'BS'  THEN dt.tasa_bs_usd
            ELSE 1
        END AS unidades_por_usd
    FROM staging.stg_ventas_detalle svd
    INNER JOIN staging.stg_ventas_header svh
        ON svd.numero = svh.numero
    LEFT JOIN core.dim_clientes dc
        ON dc.documento = RIGHT(svh.cliente_documento, -2)
    LEFT JOIN core.dim_usuarios du
        ON du.username = svh.usuario
    INNER JOIN core.dim_producto dpp
        ON dpp.codigo = svd.product_codigo
    INNER JOIN core.dim_tiempo dt
        ON dt.fecha = svh.fecha_hora::DATE
    INNER JOIN core.dim_hora dh
        ON EXTRACT(HOUR FROM svh.fecha_hora::timestamp) = dh.hora
    INNER JOIN core.dim_moneda dm
        ON dm.codigo = svh.moneda
)
SELECT
    sk_fecha,
    sk_hora,
    sk_producto,
    sk_cliente,
    sk_empleado,
    sk_moneda,
    nro_factura,
    cantidad,
    ROUND((precio_unitario / NULLIF(unidades_por_usd, 0))::numeric, 2) AS precio_unit_usd,
    ROUND((subtotal        / NULLIF(unidades_por_usd, 0))::numeric, 2) AS subtotal_usd
FROM ventas
ORDER BY nro_factura ASC;
