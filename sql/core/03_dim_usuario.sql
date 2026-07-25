DO $$
BEGIN
    CREATE TYPE rol_usuario AS ENUM ('administrador', 'vendedor', 'consulta');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END$$;

DROP TABLE IF EXISTS core.dim_usuarios;
CREATE TABLE IF NOT EXISTS core.dim_usuarios (
    sk_usuario      BIGSERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    rol             rol_usuario NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion  DATE NOT NULL
);

WITH usuarios_ordenados AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY username
            ORDER BY fecha_creacion
        ) AS flag
    FROM staging.stg_usuarios
    WHERE username IS NOT NULL
)
INSERT INTO core.dim_usuarios (
    username,
    nombre_completo,
    rol,
    activo,
    fecha_creacion
)
SELECT
    LOWER(TRIM(username)),
    nombre_completo,
    LOWER(TRIM(rol))::rol_usuario,
    UPPER(TRIM(activo)) = 'SI',
    fecha_creacion::DATE
FROM usuarios_ordenados
WHERE flag = 1;
