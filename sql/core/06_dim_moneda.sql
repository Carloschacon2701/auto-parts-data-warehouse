DROP TABLE IF EXISTS core.dim_moneda;
CREATE TABLE IF NOT EXISTS core.dim_moneda (
    sk_moneda   BIGSERIAL PRIMARY KEY,
    codigo      VARCHAR(10) NOT NULL,
);

INSERT INTO core.dim_moneda (
    codigo
)
SELECT DISTINCT moneda FROM staging.stg_ventas_header
