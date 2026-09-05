"""ETAPA 2 - EXTRACCION (la E de ETL).

Lee el archivo crudo por bloques (chunks) para poder trabajar con ~1 millon
de filas sin agotar la memoria, normaliza los nombres de columna segun el
mapeo del config y entrega un DataFrame canonico.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.log import obtener_logger

log = obtener_logger("etl.extract")


def perfilar_fuente(ruta: Path, cfg: dict) -> pd.DataFrame:
    """Lee solo las primeras filas para conocer el archivo antes de procesarlo."""
    muestra = pd.read_csv(
        ruta,
        sep=cfg["extraccion"]["separador"],
        encoding=cfg["extraccion"]["encoding"],
        nrows=5000,
        low_memory=False,
    )
    perfil = pd.DataFrame(
        {
            "columna": muestra.columns,
            "tipo": [str(t) for t in muestra.dtypes],
            "pct_nulos": (muestra.isna().mean() * 100).round(2).values,
            "valores_unicos": [muestra[c].nunique(dropna=True) for c in muestra.columns],
            "ejemplo": [
                muestra[c].dropna().iloc[0] if muestra[c].notna().any() else None
                for c in muestra.columns
            ],
        }
    )
    log.info("Perfil de la fuente (%d columnas detectadas):", len(perfil))
    log.info("\n%s", perfil.to_string(index=False))
    return perfil


def _validar_mapeo(columnas_archivo: list[str], mapeo: dict[str, str]) -> dict[str, str]:
    """Comprueba que el mapeo del config coincida con el archivo real."""
    faltantes = [c for c in mapeo if c not in columnas_archivo]
    if faltantes:
        log.warning(
            "Estas columnas del mapeo NO existen en el archivo y seran ignoradas: %s",
            faltantes,
        )
    sin_mapear = [c for c in columnas_archivo if c not in mapeo]
    if sin_mapear:
        log.info("Columnas del archivo descartadas por no estar en el mapeo: %s", sin_mapear)
    return {k: v for k, v in mapeo.items() if k in columnas_archivo}


def extraer(cfg: dict) -> pd.DataFrame:
    """Devuelve el dataset crudo con nombres de columna canonicos."""
    ruta = cfg["rutas"]["raw"] / cfg["extraccion"]["archivo"]
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo crudo en:\n  {ruta}\n"
            "Descarga el dataset y colocalo ahi, o ajusta 'extraccion.archivo' en config.yaml."
        )

    log.info("Leyendo fuente: %s (%.1f MB)", ruta.name, ruta.stat().st_size / 1024**2)
    perfilar_fuente(ruta, cfg)

    cabecera = pd.read_csv(ruta, sep=cfg["extraccion"]["separador"], nrows=0)
    mapeo = _validar_mapeo(list(cabecera.columns), cfg["mapeo_columnas"])

    chunksize = cfg["extraccion"]["chunksize"]
    limite = cfg["extraccion"].get("muestra_filas")

    bloques: list[pd.DataFrame] = []
    total = 0
    lector = pd.read_csv(
        ruta,
        sep=cfg["extraccion"]["separador"],
        encoding=cfg["extraccion"]["encoding"],
        usecols=list(mapeo.keys()),
        chunksize=chunksize,
        low_memory=False,
    )
    for i, bloque in enumerate(lector, start=1):
        bloques.append(bloque)
        total += len(bloque)
        log.info("  bloque %d leido | acumulado: %s filas", i, f"{total:,}")
        if limite and total >= limite:
            break

    df = pd.concat(bloques, ignore_index=True).rename(columns=mapeo)
    if limite:
        df = df.head(limite)

    log.info("Extraccion completada: %s filas x %d columnas", f"{len(df):,}", df.shape[1])
    return df
