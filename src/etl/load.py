"""ETAPA 4 (cierre) - CARGA (la L de ETL).

Convierte la tabla plana ya limpia en un MODELO DIMENSIONAL (esquema en
estrella) dentro de SQLite. A partir de aqui tanto Python como Power BI
consumen la base de datos, no el CSV.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.utils.auditoria import Auditoria
from src.utils.log import obtener_logger

log = obtener_logger("etl.load")

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def conectar(ruta_bd: Path) -> sqlite3.Connection:
    ruta_bd.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta_bd)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def crear_esquema(con: sqlite3.Connection, ruta_sql: Path) -> None:
    """Ejecuta el DDL. Recrea las tablas desde cero en cada carga completa."""
    con.executescript(ruta_sql.read_text(encoding="utf-8"))
    con.commit()
    log.info("Esquema dimensional creado desde %s", ruta_sql.name)


def _construir_dimension(df: pd.DataFrame, columnas: list[str], nombre_id: str) -> pd.DataFrame:
    """Genera una dimension con clave subrogada a partir de las combinaciones unicas."""
    dim = df[columnas].drop_duplicates().reset_index(drop=True)
    dim.insert(0, nombre_id, range(1, len(dim) + 1))
    return dim


def construir_estrella(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Descompone la tabla plana en dimensiones + hechos."""
    cols_ubi = [c for c in ["pais", "departamento", "ciudad", "barrio"] if c in df.columns]
    cols_tipo = [c for c in ["tipo_propiedad", "tipo_operacion"] if c in df.columns]
    cols_tiempo = [c for c in ["anio", "mes", "trimestre", "anio_mes"] if c in df.columns]

    dim_ubicacion = _construir_dimension(df, cols_ubi, "id_ubicacion")
    dim_tipo = _construir_dimension(df, cols_tipo, "id_tipo")

    dim_tiempo = _construir_dimension(df, cols_tiempo, "id_tiempo")
    if "mes" in dim_tiempo:
        dim_tiempo["nombre_mes"] = dim_tiempo["mes"].map(MESES)
        dim_tiempo["fecha"] = dim_tiempo["anio_mes"].astype(str) + "-01"
        dim_tiempo = dim_tiempo.sort_values(["anio", "mes"]).reset_index(drop=True)

    # Enlazamos cada hecho con su clave subrogada
    hechos = (
        df.merge(dim_ubicacion, on=cols_ubi, how="left")
        .merge(dim_tipo, on=cols_tipo, how="left")
        .merge(dim_tiempo[["id_tiempo", *cols_tiempo]], on=cols_tiempo, how="left")
    )

    cols_hecho = [
        "id_inmueble", "id_aviso", "id_ubicacion", "id_tiempo", "id_tipo",
        "superficie_total", "superficie_cubierta", "habitaciones", "banos",
        "latitud", "longitud", "precio", "precio_m2",
        "area_por_habitacion", "ratio_bano_habitacion", "pct_cubierta", "segmento_tamano",
        "dias_publicado", "esta_activo",
    ]
    hechos = hechos[[c for c in cols_hecho if c in hechos.columns]]

    log.info(
        "Estrella construida | hechos: %s | ubicaciones: %s | tiempos: %s | tipos: %s",
        f"{len(hechos):,}", f"{len(dim_ubicacion):,}", f"{len(dim_tiempo):,}", f"{len(dim_tipo):,}",
    )
    return {
        "dim_ubicacion": dim_ubicacion,
        "dim_tiempo": dim_tiempo,
        "dim_tipo": dim_tipo,
        "hecho_inmueble": hechos,
    }


def cargar(df: pd.DataFrame, aud: Auditoria, cfg: dict, ruta_sql: Path) -> None:
    """Crea el esquema, escribe las tablas y guarda la auditoria del ETL."""
    tablas = construir_estrella(df)
    con = conectar(cfg["rutas"]["base_datos"])
    try:
        crear_esquema(con, ruta_sql)
        for nombre, tabla in tablas.items():
            tabla.to_sql(nombre, con, if_exists="append", index=False)
            log.info("  %-16s -> %s filas", nombre, f"{len(tabla):,}")

        aud.a_dataframe().to_sql("etl_auditoria", con, if_exists="append", index=False)
        con.commit()
    finally:
        con.close()

    # Copia en Parquet: formato columnar, comprimido y rapido de releer
    destino = cfg["rutas"]["processed"] / "inmuebles_limpio.parquet"
    df.to_parquet(destino, index=False)
    log.info("Dataset limpio guardado en %s", destino.name)
    log.info("Base de datos lista: %s", cfg["rutas"]["base_datos"])
