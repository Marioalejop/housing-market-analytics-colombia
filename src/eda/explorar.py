"""ETAPA 3 - EXPLORACION DE LOS DATOS.

Genera las figuras y tablas que sustentan las decisiones tomadas en el ETL
y en el modelado. Todo se guarda en reportes/ para poder citarlo en el
documento final.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: guarda a archivo
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.utils.log import obtener_logger

log = obtener_logger("eda")
sns.set_theme(style="whitegrid", palette="deep")

NUM_INTERES = [
    "precio", "precio_m2", "superficie_total", "habitaciones",
    "banos", "area_por_habitacion", "ratio_bano_habitacion",
]


def _guardar(fig: plt.Figure, ruta, nombre: str) -> None:
    destino = ruta / nombre
    fig.savefig(destino, dpi=130, bbox_inches="tight")
    plt.close(fig)
    log.info("  figura -> %s", nombre)


def resumen_estadistico(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Tabla descriptiva de las variables numericas."""
    cols = [c for c in NUM_INTERES if c in df.columns]
    resumen = df[cols].describe().T
    resumen["nulos_pct"] = (df[cols].isna().mean() * 100).round(2)
    resumen["asimetria"] = df[cols].skew().round(3)
    resumen.to_csv(cfg["rutas"]["tablas"] / "01_resumen_estadistico.csv", encoding="utf-8")
    log.info("Resumen estadistico:\n%s", resumen.round(2).to_string())
    return resumen


def distribuciones(df: pd.DataFrame, cfg: dict) -> None:
    """Histogramas de precio y area. El precio suele ser muy asimetrico a la derecha."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))

    sns.histplot(df["precio"] / 1e6, bins=60, ax=axes[0, 0], color="#2b6cb0")
    axes[0, 0].set(title="Distribucion del precio", xlabel="Precio (millones COP)")

    sns.histplot(np.log10(df["precio"]), bins=60, ax=axes[0, 1], color="#2c7a7b")
    axes[0, 1].set(title="Precio en escala logaritmica", xlabel="log10(precio)")

    sns.histplot(df["superficie_total"], bins=60, ax=axes[1, 0], color="#975a16")
    axes[1, 0].set(title="Distribucion del area", xlabel="Superficie total (m2)")

    sns.histplot(df["precio_m2"] / 1e6, bins=60, ax=axes[1, 1], color="#805ad5")
    axes[1, 1].set(title="Precio por m2", xlabel="Millones COP / m2")

    fig.suptitle("Distribucion de las variables clave", fontsize=14, weight="bold")
    _guardar(fig, cfg["rutas"]["figuras"], "01_distribuciones.png")


def correlaciones(df: pd.DataFrame, cfg: dict) -> None:
    """Matriz de correlacion: que variables se relacionan con el precio."""
    cols = [c for c in NUM_INTERES if c in df.columns]
    corr = df[cols].corr(numeric_only=True)
    corr.to_csv(cfg["rutas"]["tablas"] / "02_correlaciones.csv", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax, square=True)
    ax.set_title("Correlacion entre variables numericas", fontsize=13, weight="bold")
    _guardar(fig, cfg["rutas"]["figuras"], "02_correlaciones.png")


def precio_por_ciudad(df: pd.DataFrame, cfg: dict, top: int = 15) -> pd.DataFrame:
    """Ranking de ciudades por precio por m2: la lectura de negocio mas directa."""
    tabla = (
        df.groupby("ciudad")
        .agg(
            n_avisos=("precio", "size"),
            precio_mediano=("precio", "median"),
            precio_m2_mediano=("precio_m2", "median"),
            area_mediana=("superficie_total", "median"),
        )
        .query("n_avisos >= 50")
        .sort_values("precio_m2_mediano", ascending=False)
    )
    tabla.to_csv(cfg["rutas"]["tablas"] / "03_precio_por_ciudad.csv", encoding="utf-8")

    principales = tabla.head(top)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        x=principales["precio_m2_mediano"] / 1e6,
        y=principales.index,
        ax=ax,
        color="#2b6cb0",
    )
    ax.set(
        title=f"Top {top} ciudades por precio del m2 (mediana)",
        xlabel="Millones COP por m2",
        ylabel="",
    )
    _guardar(fig, cfg["rutas"]["figuras"], "03_precio_por_ciudad.png")
    return tabla


def evolucion_temporal(df: pd.DataFrame, cfg: dict) -> None:
    """Serie mensual del precio por m2: alimenta el analisis de tendencia en Power BI."""
    if "anio_mes" not in df.columns:
        return
    serie = (
        df.groupby("anio_mes")
        .agg(precio_m2_mediano=("precio_m2", "median"), n_avisos=("precio", "size"))
        .sort_index()
    )
    serie.to_csv(cfg["rutas"]["tablas"] / "04_evolucion_mensual.csv", encoding="utf-8")

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(serie.index, serie["precio_m2_mediano"] / 1e6, marker="o", color="#2b6cb0")
    ax1.set(ylabel="Millones COP / m2", xlabel="Mes")
    ax1.tick_params(axis="x", rotation=60)

    ax2 = ax1.twinx()
    ax2.bar(serie.index, serie["n_avisos"], alpha=0.20, color="#718096")
    ax2.set_ylabel("Numero de avisos")
    ax2.grid(False)

    ax1.set_title("Evolucion mensual del precio por m2", fontsize=13, weight="bold")
    _guardar(fig, cfg["rutas"]["figuras"], "04_evolucion_mensual.png")


def explorar(df: pd.DataFrame, cfg: dict) -> None:
    log.info("Iniciando exploracion sobre %s registros...", f"{len(df):,}")
    resumen_estadistico(df, cfg)
    distribuciones(df, cfg)
    correlaciones(df, cfg)
    precio_por_ciudad(df, cfg)
    evolucion_temporal(df, cfg)
    log.info("Exploracion terminada. Revisa reportes/figuras y reportes/tablas.")
