-- =====================================================================
-- Vistas de consumo para Power BI.
-- La idea: Power BI NO deberia calcular la logica de negocio. La base de
-- datos entrega la informacion ya modelada y el dashboard solo la muestra.
-- =====================================================================

DROP VIEW IF EXISTS v_inmuebles;
DROP VIEW IF EXISTS v_kpi_ciudad;
DROP VIEW IF EXISTS v_evolucion_mensual;
DROP VIEW IF EXISTS v_segmentos;
DROP VIEW IF EXISTS v_oportunidades;

-- Vista plana principal: la tabla de hechos con todas sus dimensiones resueltas.
CREATE VIEW v_inmuebles AS
SELECT
    h.id_inmueble,
    u.departamento,
    u.ciudad,
    u.barrio,
    t.anio,
    t.mes,
    t.anio_mes,
    t.nombre_mes,
    p.tipo_propiedad,
    s.nombre_segmento,
    h.superficie_total,
    h.habitaciones,
    h.banos,
    h.latitud,
    h.longitud,
    h.segmento_tamano,
    h.precio,
    h.precio_m2,
    h.es_anomalo,
    h.precio_estimado,
    h.error_estimacion
FROM hecho_inmueble h
LEFT JOIN dim_ubicacion u ON u.id_ubicacion = h.id_ubicacion
LEFT JOIN dim_tiempo    t ON t.id_tiempo    = h.id_tiempo
LEFT JOIN dim_tipo      p ON p.id_tipo      = h.id_tipo
LEFT JOIN dim_segmento  s ON s.id_segmento  = h.id_segmento;

-- KPI por ciudad: la tarjeta principal del dashboard.
CREATE VIEW v_kpi_ciudad AS
SELECT
    u.departamento,
    u.ciudad,
    COUNT(*)                        AS n_avisos,
    ROUND(AVG(h.precio))            AS precio_promedio,
    ROUND(AVG(h.precio_m2))         AS precio_m2_promedio,
    ROUND(AVG(h.superficie_total),1) AS area_promedio,
    ROUND(AVG(h.habitaciones),2)    AS habitaciones_promedio
FROM hecho_inmueble h
JOIN dim_ubicacion u ON u.id_ubicacion = h.id_ubicacion
WHERE h.es_anomalo = 0
GROUP BY u.departamento, u.ciudad
HAVING COUNT(*) >= 50;

-- Serie de tiempo para el grafico de tendencia.
CREATE VIEW v_evolucion_mensual AS
SELECT
    t.anio_mes,
    t.anio,
    t.mes,
    u.ciudad,
    COUNT(*)                AS n_avisos,
    ROUND(AVG(h.precio_m2)) AS precio_m2_promedio
FROM hecho_inmueble h
JOIN dim_tiempo    t ON t.id_tiempo    = h.id_tiempo
JOIN dim_ubicacion u ON u.id_ubicacion = h.id_ubicacion
WHERE h.es_anomalo = 0
GROUP BY t.anio_mes, t.anio, t.mes, u.ciudad;

-- Resultado del aprendizaje no supervisado, listo para filtrar el dashboard.
CREATE VIEW v_segmentos AS
SELECT
    s.id_segmento,
    s.nombre_segmento,
    s.descripcion,
    COUNT(h.id_inmueble)    AS n_inmuebles,
    ROUND(AVG(h.precio))    AS precio_promedio,
    ROUND(AVG(h.precio_m2)) AS precio_m2_promedio
FROM dim_segmento s
LEFT JOIN hecho_inmueble h ON h.id_segmento = s.id_segmento
GROUP BY s.id_segmento, s.nombre_segmento, s.descripcion;

-- Caso de uso de negocio: inmuebles cuyo precio publicado esta muy por
-- debajo de lo que el modelo estima. Son candidatos a oportunidad de compra.
CREATE VIEW v_oportunidades AS
SELECT
    h.id_inmueble,
    u.ciudad,
    u.barrio,
    h.superficie_total,
    h.habitaciones,
    h.banos,
    h.precio,
    h.precio_estimado,
    ROUND((h.precio_estimado - h.precio) * 100.0 / h.precio, 2) AS descuento_pct
FROM hecho_inmueble h
JOIN dim_ubicacion u ON u.id_ubicacion = h.id_ubicacion
WHERE h.precio_estimado IS NOT NULL
  AND h.es_anomalo = 0
  AND (h.precio_estimado - h.precio) * 100.0 / h.precio > 15
ORDER BY descuento_pct DESC;
