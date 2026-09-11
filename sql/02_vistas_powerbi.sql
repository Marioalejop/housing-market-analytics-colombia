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
DROP VIEW IF EXISTS v_rotacion;

-- Vista plana principal: la tabla de hechos con todas sus dimensiones resueltas.
CREATE VIEW v_inmuebles AS
SELECT
    h.id_inmueble,
    u.departamento,
    u.ciudad,
    u.zona,
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
    h.dias_publicado,
    h.esta_activo,
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
    ROUND(AVG(h.habitaciones),2)    AS habitaciones_promedio,
    ROUND(AVG(h.dias_publicado),1)  AS dias_publicado_promedio,
    SUM(h.esta_activo)              AS avisos_activos
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
    u.zona,
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

-- Rotacion del inventario. Responde la causa del Ishikawa "no hay revision
-- periodica de avisos con mucho tiempo publicados": cruza cuanto tarda en
-- salir un aviso con que tan por encima del mercado esta su precio.
CREATE VIEW v_rotacion AS
SELECT
    u.ciudad,
    s.nombre_segmento,
    h.segmento_tamano,
    COUNT(*)                                              AS n_avisos_cerrados,
    ROUND(AVG(h.dias_publicado), 1)                       AS dias_publicado_promedio,
    ROUND(AVG(h.precio_m2))                               AS precio_m2_promedio,
    SUM(CASE WHEN h.dias_publicado > 180 THEN 1 ELSE 0 END) AS avisos_lentos,
    ROUND(
        SUM(CASE WHEN h.dias_publicado > 180 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                                     AS pct_avisos_lentos
FROM hecho_inmueble h
JOIN dim_ubicacion u ON u.id_ubicacion = h.id_ubicacion
LEFT JOIN dim_segmento s ON s.id_segmento = h.id_segmento
WHERE h.dias_publicado IS NOT NULL
  AND h.es_anomalo = 0
GROUP BY u.ciudad, s.nombre_segmento, h.segmento_tamano
HAVING COUNT(*) >= 30;
