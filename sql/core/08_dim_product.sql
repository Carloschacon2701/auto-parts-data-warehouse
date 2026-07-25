DROP TABLE IF EXISTS core.dim_producto;
CREATE TABLE IF NOT EXISTS core.dim_producto (
    sk_producto      BIGSERIAL PRIMARY KEY,
    codigo           VARCHAR(100) NOT NULL,
    nro_original     VARCHAR(100),
    descripcion      VARCHAR(500) NOT NULL,
    marca            VARCHAR(100),
    categoria        VARCHAR(100),
    costo_usd        NUMERIC(12, 2) NOT NULL,
    precio_venta_usd NUMERIC(12, 2) NOT NULL,
    ubicacion        VARCHAR(100),
    stock_minimo     INTEGER DEFAULT 0,
    fecha_creacion   DATE DEFAULT CURRENT_DATE
);

WITH productos_ordenados AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(NULLIF(TRIM(codigo), ''), TRIM(descripcion))
            ORDER BY descripcion
        ) AS flag
    FROM staging.stg_productos
    WHERE descripcion IS NOT NULL
)
INSERT INTO core.dim_producto (
    codigo,
    nro_original,
    descripcion,
    marca,
    categoria,
    costo_usd,
    precio_venta_usd
)
SELECT
    COALESCE(NULLIF(TRIM(codigo), ''), 'SIN-CODIGO'),
    NULLIF(TRIM(nro_original), ''),
    TRIM(descripcion),
    NULLIF(TRIM(marca), ''),
    UPPER(SPLIT_PART(TRIM(descripcion), ' ', 1)),
    costo_usd,
    precio_venta_usd
FROM productos_ordenados
WHERE flag = 1;
