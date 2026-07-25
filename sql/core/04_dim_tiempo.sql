DROP TABLE IF EXISTS core.dim_tiempo;

CREATE TABLE core.dim_tiempo(
    sk_fecha BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    trimestre INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL,
    es_feriado BOOLEAN NOT NULL,
    nombre_feriado VARCHAR(255),
    tasa_bs_usd DOUBLE PRECISION NOT NULL,
    cop_por_usd DOUBLE PRECISION NOT NULL,
    tasa_bs_cop DOUBLE PRECISION NOT NULL
);

INSERT INTO core.dim_tiempo(
    fecha,
    trimestre,
    dia_semana,
    es_fin_de_semana,
    es_feriado,
    nombre_feriado,
    tasa_bs_usd,
    cop_por_usd,
    tasa_bs_cop
)
SELECT
    t.fecha::DATE,
    EXTRACT(QUARTER FROM t.fecha::DATE)::INTEGER,
    EXTRACT(ISODOW FROM t.fecha::DATE)::INTEGER,
    EXTRACT(ISODOW FROM t.fecha::DATE) IN (6, 7),
    f.feriado IS NOT NULL,
    f.feriado,
    t.tasa_bs_usd,
    t.cop_por_usd,
    t.tasa_bs_cop
FROM staging.stg_tasas_cambio t
LEFT JOIN staging.stg_feriados f
    ON f.fecha::DATE = t.fecha::DATE;
