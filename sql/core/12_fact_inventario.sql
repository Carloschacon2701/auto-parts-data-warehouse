-- Hecho de movimientos de inventario. Grano: una fila por movimiento registrado.
--
-- El tipo de movimiento dejó de guardarse como texto y ahora es una clave foránea
-- a core.dim_tipo_movimiento. El campo `referencia` (el documento que originó el
-- movimiento) se eliminó: no es una medida y lo que representa ya está en los
-- hechos de venta y de compra.
--
-- La cantidad se abre en `cantidad_entrada` / `cantidad_salida` porque en el origen
-- viene siempre positiva y su significado dependía del texto del tipo. Separadas,
-- las medidas son aditivas por sí solas y `cantidad_neta` puede sumarse
-- directamente para obtener la variación de existencias de cualquier corte.

DROP TABLE IF EXISTS core.fact_mov_inventario;

CREATE TABLE core.fact_mov_inventario (
    sk_movimiento       BIGSERIAL PRIMARY KEY,
    sk_fecha            BIGINT NOT NULL REFERENCES core.dim_tiempo(sk_fecha),
    sk_hora             BIGINT NOT NULL REFERENCES core.dim_hora(sk_hora),
    sk_producto         BIGINT NOT NULL REFERENCES core.dim_producto(sk_producto),
    sk_tipo_movimiento  BIGINT NOT NULL REFERENCES core.dim_tipo_movimiento(sk_tipo_movimiento),
    cantidad_entrada    INTEGER NOT NULL,
    cantidad_salida     INTEGER NOT NULL,
    cantidad_neta       INTEGER NOT NULL,
    stock_resultante    INTEGER NOT NULL
);

INSERT INTO core.fact_mov_inventario (
    sk_fecha,
    sk_hora,
    sk_producto,
    sk_tipo_movimiento,
    cantidad_entrada,
    cantidad_salida,
    cantidad_neta,
    stock_resultante
)
SELECT
    dt.sk_fecha,
    dh.sk_hora,
    dpp.sk_producto,
    dtm.sk_tipo_movimiento,
    CASE WHEN dtm.signo_stock =  1 THEN ABS(smi.cantidad) ELSE 0 END AS cantidad_entrada,
    CASE WHEN dtm.signo_stock = -1 THEN ABS(smi.cantidad) ELSE 0 END AS cantidad_salida,
    dtm.signo_stock * ABS(smi.cantidad)                              AS cantidad_neta,
    smi.stock_nuevo AS stock_resultante
FROM staging.stg_movimientos_inventario smi
INNER JOIN core.dim_producto dpp
    ON dpp.codigo = smi.product_codigo
INNER JOIN core.dim_tiempo dt
    ON dt.fecha = smi.fecha_hora::DATE
INNER JOIN core.dim_hora dh
    ON EXTRACT(HOUR FROM smi.fecha_hora::timestamp) = dh.hora
INNER JOIN core.dim_tipo_movimiento dtm
    ON dtm.codigo = smi.tipo
   AND dtm.motivo = COALESCE(NULLIF(TRIM(smi.motivo), ''), 'SIN MOTIVO')
ORDER BY smi.fecha_hora ASC;
