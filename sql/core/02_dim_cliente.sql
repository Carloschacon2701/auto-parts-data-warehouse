DO $$
BEGIN
    CREATE TYPE tipo_cliente AS ENUM ('V', 'E', 'J');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END$$;

DROP TABLE IF EXISTS core.dim_clientes;
CREATE TABLE IF NOT EXISTS core.dim_clientes (
    sk_cliente     BIGSERIAL PRIMARY KEY,
    documento      VARCHAR(50) NOT NULL,
    tipo           tipo_cliente DEFAULT 'V',
    nombre         VARCHAR(100) NOT NULL,
    fecha_registro DATE NOT NULL,
    email          VARCHAR(255) NOT NULL,
    fecha_creacion DATE DEFAULT CURRENT_DATE
);

WITH clientes_ordenados AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY documento
            ORDER BY fecha_registro
        ) AS flag
    FROM staging.stg_clientes
    WHERE documento IS NOT NULL
)
INSERT INTO core.dim_clientes (
    documento,
    tipo,
    nombre,
    fecha_registro,
    email
)
SELECT
    RIGHT(documento, -2),
    UPPER(LEFT(documento, 1))::tipo_cliente,
    nombre,
    fecha_registro::DATE,
    LOWER(TRIM(email))
FROM clientes_ordenados
WHERE flag = 1;
