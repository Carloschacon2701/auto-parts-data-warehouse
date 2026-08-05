-- Dimensión de tipos de movimiento de inventario.
--
-- El tipo de movimiento venía como texto dentro de la tabla de hechos. Un hecho
-- solo debe contener claves foráneas y medidas numéricas, así que el atributo se
-- normaliza aquí.
--
-- El grano es (tipo, motivo): son 7 combinaciones y la relación es jerárquica
-- (cada motivo pertenece a un solo tipo), así que ambos caben en una misma
-- dimensión sin generar filas espurias.
--
-- `signo_stock` codifica el efecto sobre las existencias (+1 suma, -1 resta) y es
-- lo que permite que las cantidades del hecho sean aditivas sin tener que leer un
-- campo de texto.

DROP TABLE IF EXISTS core.dim_tipo_movimiento;

CREATE TABLE core.dim_tipo_movimiento (
    sk_tipo_movimiento BIGSERIAL PRIMARY KEY,
    codigo             VARCHAR(50) NOT NULL,
    nombre             VARCHAR(100) NOT NULL,
    motivo             VARCHAR(200) NOT NULL,
    efecto_stock       VARCHAR(10) NOT NULL,
    signo_stock        SMALLINT NOT NULL,
    UNIQUE (codigo, motivo)
);

INSERT INTO core.dim_tipo_movimiento (
    codigo,
    nombre,
    motivo,
    efecto_stock,
    signo_stock
)
SELECT DISTINCT
    smi.tipo                                     AS codigo,
    CASE smi.tipo
        WHEN 'entrada'        THEN 'Entrada'
        WHEN 'salida'         THEN 'Salida'
        WHEN 'venta'          THEN 'Venta'
        WHEN 'import_inicial' THEN 'Carga inicial'
        ELSE INITCAP(REPLACE(smi.tipo, '_', ' '))
    END                                          AS nombre,
    COALESCE(NULLIF(TRIM(smi.motivo), ''), 'SIN MOTIVO') AS motivo,
    CASE
        WHEN smi.tipo IN ('entrada', 'import_inicial') THEN 'ENTRADA'
        ELSE 'SALIDA'
    END                                          AS efecto_stock,
    CASE
        WHEN smi.tipo IN ('entrada', 'import_inicial') THEN 1
        ELSE -1
    END                                          AS signo_stock
FROM staging.stg_movimientos_inventario smi
WHERE smi.tipo IS NOT NULL
ORDER BY codigo, motivo;
