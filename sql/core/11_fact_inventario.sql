DROP TABLE IF EXISTS core.fact_mov_inventario;

CREATE TABLE core.fact_mov_inventario (
    sk_movimiento     BIGSERIAL PRIMARY KEY,
    sk_fecha          BIGINT NOT NULL REFERENCES core.dim_tiempo(sk_fecha),
    sk_hora           BIGINT NOT NULL REFERENCES core.dim_hora(sk_hora),
    sk_producto       BIGINT NOT NULL REFERENCES core.dim_producto(sk_producto),
    tipo_movimiento   VARCHAR(50) NOT NULL,
    cantidad          INTEGER NOT NULL,
    stock_resultante  INTEGER NOT NULL,
    referencia        VARCHAR(100)
);

INSERT INTO core.fact_mov_inventario (
    sk_fecha,
    sk_hora,
    sk_producto,
    tipo_movimiento,
    cantidad,
    stock_resultante,
    referencia
)
SELECT
    dt.sk_fecha,
    dh.sk_hora,
    dpp.sk_producto,
    smi.tipo AS tipo_movimiento,
    smi.cantidad,
    smi.stock_nuevo AS stock_resultante,
    smi.referencia
FROM staging.stg_movimientos_inventario smi
INNER JOIN core.dim_producto dpp
    ON dpp.codigo = smi.product_codigo
INNER JOIN core.dim_tiempo dt
    ON dt.fecha = smi.fecha_hora::DATE
INNER JOIN core.dim_hora dh
    ON EXTRACT(HOUR FROM smi.fecha_hora::timestamp) = dh.hora
ORDER BY smi.fecha_hora ASC;
