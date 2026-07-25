DO $$
BEGIN
    CREATE TYPE tipo_franja AS ENUM ('manana', 'mediodia', 'tarde');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END$$;


DROP TABLE IF EXISTS core.dim_hora;
CREATE TABLE core.dim_hora (
    sk_hora   BIGSERIAL PRIMARY KEY,
    hora      INTEGER NOT NULL,
    franja    tipo_franja NOT NULL
);


INSERT INTO core.dim_hora (
    hora,
    franja
)
SELECT
    hora,
    CASE 
        WHEN hora < 12 THEN 'manana'::tipo_franja
        WHEN hora >= 13 THEN 'tarde'::tipo_franja
        ELSE 'mediodia'::tipo_franja
    END AS franja
FROM (
    SELECT
        EXTRACT(HOUR FROM fecha_hora::timestamp) AS hora
    FROM staging.stg_movimientos_inventario
    UNION
    SELECT
        EXTRACT(HOUR FROM fecha_hora::timestamp) AS hora
    FROM staging.stg_ventas_header
) h
ORDER BY hora DESC