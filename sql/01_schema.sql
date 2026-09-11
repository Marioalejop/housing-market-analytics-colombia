-- =====================================================================
-- Modelo dimensional (esquema en estrella) del mercado de vivienda.
-- Una tabla de hechos rodeada de dimensiones. Es el modelo que Power BI
-- espera encontrar: las dimensiones alimentan los filtros y los ejes,
-- la tabla de hechos alimenta las medidas.
-- =====================================================================

DROP TABLE IF EXISTS hecho_inmueble;
DROP TABLE IF EXISTS dim_ubicacion;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_tipo;
DROP TABLE IF EXISTS dim_segmento;
DROP TABLE IF EXISTS etl_auditoria;
DROP TABLE IF EXISTS modelo_metricas;

-- ---------- DIMENSIONES ----------

CREATE TABLE dim_ubicacion (
    id_ubicacion INTEGER PRIMARY KEY,
    pais         TEXT,
    departamento TEXT,
    ciudad       TEXT,
    zona         TEXT,                -- l4 en Properati
    barrio       TEXT                 -- l6 en Properati (vacio en la mayoria de avisos)
);

CREATE TABLE dim_tiempo (
    id_tiempo  INTEGER PRIMARY KEY,
    fecha      TEXT,
    anio       INTEGER,
    mes        INTEGER,
    trimestre  INTEGER,
    anio_mes   TEXT,
    nombre_mes TEXT
);

CREATE TABLE dim_tipo (
    id_tipo         INTEGER PRIMARY KEY,
    tipo_propiedad  TEXT,
    tipo_operacion  TEXT
);

-- Se puebla en la etapa de aprendizaje NO SUPERVISADO (K-Means)
CREATE TABLE dim_segmento (
    id_segmento      INTEGER PRIMARY KEY,
    nombre_segmento  TEXT,
    n_inmuebles      INTEGER,
    precio_promedio  REAL,
    precio_m2_prom   REAL,
    area_promedio    REAL,
    habitaciones_prom REAL,
    descripcion      TEXT
);

-- ---------- TABLA DE HECHOS ----------

CREATE TABLE hecho_inmueble (
    id_inmueble          INTEGER PRIMARY KEY,
    id_aviso             TEXT,                -- identificador original del aviso
    id_ubicacion         INTEGER,
    id_tiempo            INTEGER,
    id_tipo              INTEGER,
    id_segmento          INTEGER,

    superficie_total     REAL,
    superficie_cubierta  REAL,
    habitaciones         REAL,
    banos                REAL,
    latitud              REAL,
    longitud             REAL,

    precio               REAL,
    precio_m2            REAL,
    area_por_habitacion  REAL,
    ratio_bano_habitacion REAL,
    pct_cubierta         REAL,
    segmento_tamano      TEXT,

    dias_publicado       REAL,                -- nulo si el aviso sigue activo
    esta_activo          INTEGER,             -- 1 = aviso vigente

    es_anomalo           INTEGER DEFAULT 0,   -- marcado por Isolation Forest
    precio_estimado      REAL,                -- prediccion del modelo supervisado
    error_estimacion     REAL,                -- precio_estimado - precio

    FOREIGN KEY (id_ubicacion) REFERENCES dim_ubicacion (id_ubicacion),
    FOREIGN KEY (id_tiempo)    REFERENCES dim_tiempo (id_tiempo),
    FOREIGN KEY (id_tipo)      REFERENCES dim_tipo (id_tipo),
    FOREIGN KEY (id_segmento)  REFERENCES dim_segmento (id_segmento)
);

CREATE INDEX idx_hecho_ubicacion ON hecho_inmueble (id_ubicacion);
CREATE INDEX idx_hecho_tiempo    ON hecho_inmueble (id_tiempo);
CREATE INDEX idx_hecho_tipo      ON hecho_inmueble (id_tipo);
CREATE INDEX idx_hecho_segmento  ON hecho_inmueble (id_segmento);

-- ---------- TRAZABILIDAD ----------

-- Evidencia de cada paso del ETL: cuantas filas entraron y salieron.
CREATE TABLE etl_auditoria (
    ejecucion        TEXT,
    orden            INTEGER,
    paso             TEXT,
    filas_antes      INTEGER,
    filas_despues    INTEGER,
    filas_eliminadas INTEGER,
    pct_eliminado    REAL,
    detalle          TEXT
);

-- Comparativa de modelos supervisados
CREATE TABLE modelo_metricas (
    ejecucion TEXT,
    modelo    TEXT,
    mae       REAL,
    rmse      REAL,
    r2        REAL,
    mape      REAL,
    segundos  REAL
);
