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
    precio_unit_mon   NUMERIC(14, 2) NOT NULL,
    subtotal_mon      NUMERIC(14, 2) NOT NULL,
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
    precio_unit_mon,
    subtotal_mon,
    subtotal_usd
)
SELECT
    dt.sk_fecha,
    dh.sk_hora,
    dpp.sk_producto,
    dc.sk_cliente,
    du.sk_usuario AS sk_empleado,
    dm.sk_moneda,
    svd.numero AS nro_factura,
    svd.cantidad,
    svd.precio_unitario AS precio_unit_mon,
    svd.subtotal AS subtotal_mon,
    CASE
      WHEN svh.moneda = 'COP' THEN ROUND((svd.subtotal / dt.cop_por_usd)::numeric, 2)
      WHEN svh.moneda = 'BS'  THEN ROUND((svd.subtotal / dt.tasa_bs_usd)::numeric, 2)
        ELSE svd.subtotal
    END AS subtotal_usd
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
ORDER BY svd.numero ASC;
