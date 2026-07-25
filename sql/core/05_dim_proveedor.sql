DO $$
BEGIN
    CREATE TYPE pais_proveedor AS ENUM ('VE', 'CO');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END$$;

DROP TABLE IF EXISTS core.dim_proveedor;
CREATE TABLE IF NOT EXISTS core.dim_proveedor (
    sk_proveedor   BIGSERIAL PRIMARY KEY,
    documento      VARCHAR(50) NOT NULL,
    nombre         VARCHAR(255) NOT NULL,
    ciudad         VARCHAR(100),
    pais           pais_proveedor NOT NULL,
    fecha_creacion DATE DEFAULT CURRENT_DATE
);

WITH proveedores_ordenados AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY documento
            ORDER BY fecha_registro
        ) AS flag
    FROM staging.stg_proveedores
    WHERE documento IS NOT NULL
)
INSERT INTO core.dim_proveedor (
    documento,
    nombre,
    ciudad,
    pais
)
SELECT
    TRIM(documento),
    TRIM(nombre),
    TRIM(SPLIT_PART(direccion, ',', -2)),
    CASE
        WHEN documento LIKE 'NIT%' THEN 'CO'
        ELSE 'VE'
    END::pais_proveedor
FROM proveedores_ordenados
WHERE flag = 1;
