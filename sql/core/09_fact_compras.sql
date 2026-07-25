DROP TABLE IF EXISTS core.fact_compras;

CREATE TABLE core.fact_compras (
    sk_compra     BIGSERIAL PRIMARY KEY,
    sk_fecha      BIGINT NOT NULL REFERENCES core.dim_tiempo(sk_fecha),
    sk_producto   BIGINT NOT NULL REFERENCES core.dim_producto(sk_producto),
    sk_proveedor  BIGINT NOT NULL REFERENCES core.dim_proveedor(sk_proveedor),
    nro_orden     VARCHAR(50) NOT NULL,
    cantidad      INTEGER NOT NULL,
    cost_unt_usd  NUMERIC(14, 2) NOT NULL,
    subtotal_usd  NUMERIC(14, 2) NOT NULL
);

INSERT INTO core.fact_compras (
    sk_fecha,
    sk_producto,
    sk_proveedor,
    nro_orden,
    cantidad,
    cost_unt_usd,
    subtotal_usd
)
SELECT
    dt.sk_fecha,
    dpp.sk_producto,
    dp.sk_proveedor,
    scd.numero AS nro_orden,
    scd.cantidad,
    scd.costo_unitario_usd AS cost_unt_usd,
    scd.subtotal_usd
FROM staging.stg_compras_detalle scd
INNER JOIN staging.stg_compras_header sch
    ON scd.numero = sch.numero
INNER JOIN core.dim_proveedor dp
    ON dp.documento = sch.proveedor_documento
INNER JOIN core.dim_producto dpp
    ON dpp.codigo = scd.product_codigo
INNER JOIN core.dim_tiempo dt
    ON dt.fecha = sch.fecha_hora::DATE
ORDER BY scd.numero ASC;
