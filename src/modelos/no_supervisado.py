"""ETAPA 5a - APRENDIZAJE NO SUPERVISADO.

Dos usos, y ambos tienen sentido de negocio:

1. Isolation Forest -> deteccion de avisos anomalos. Es la ultima capa del
   control de calidad: encuentra combinaciones raras que ninguna regla fija
   habria detectado (ej. 300 m2 con 1 bano a precio de estudio).

2. K-Means -> segmentacion del mercado. Descubre grupos naturales de
   inmuebles SIN usar el precio como etiqueta. El segmento resultante se
   convierte despues en variable de entrada del modelo supervisado, y en
   filtro del dashboard de Power BI.
"""
from __future__ import annotations

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.utils.log import obtener_logger

log = obtener_logger("modelos.no_supervisado")
sns.set_theme(style="whitegrid")


def _matriz(df: pd.DataFrame, variables: list[str]) -> tuple[np.ndarray, list[str]]:
    usadas = [v for v in variables if v in df.columns]
    return df[usadas].to_numpy(dtype=float), usadas


def detectar_anomalias(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """Marca con 1 los avisos atipicos segun Isolation Forest."""
    p = cfg["no_supervisado"]
    X, usadas = _matriz(df, p["variables"])

    modelo = Pipeline(
        [
            ("imputador", SimpleImputer(strategy="median")),
            ("escalador", StandardScaler()),
            (
                "isolation",
                IsolationForest(
                    contamination=p["contaminacion_isolation_forest"],
                    random_state=p["semilla"],
                    n_estimators=200,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    etiquetas = modelo.fit_predict(X)          # -1 = anomalo, 1 = normal
    es_anomalo = pd.Series((etiquetas == -1).astype(int), index=df.index, name="es_anomalo")

    joblib.dump(modelo, cfg["rutas"]["artefactos"] / "isolation_forest.pkl")
    log.info(
        "Isolation Forest sobre %s: %s anomalias (%.2f%%)",
        usadas, f"{es_anomalo.sum():,}", es_anomalo.mean() * 100,
    )
    return es_anomalo


def elegir_k(X: np.ndarray, cfg: dict) -> int:
    """Metodo del codo + coeficiente de silueta para justificar el numero de grupos."""
    p = cfg["no_supervisado"]
    ks = range(p["k_min"], p["k_max"] + 1)

    # Con datasets grandes evaluamos la silueta sobre una muestra: es O(n^2)
    idx = np.random.default_rng(p["semilla"]).choice(
        len(X), size=min(10000, len(X)), replace=False
    )

    inercias, siluetas = [], []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=p["semilla"], n_init=10)
        etiquetas = km.fit_predict(X)
        inercias.append(km.inertia_)
        siluetas.append(silhouette_score(X[idx], etiquetas[idx]))
        log.info("  k=%d | inercia=%.0f | silueta=%.4f", k, km.inertia_, siluetas[-1])

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    axes[0].plot(list(ks), inercias, marker="o", color="#2b6cb0")
    axes[0].set(title="Metodo del codo", xlabel="k (numero de grupos)", ylabel="Inercia")
    axes[1].plot(list(ks), siluetas, marker="o", color="#2c7a7b")
    axes[1].set(title="Coeficiente de silueta", xlabel="k (numero de grupos)", ylabel="Silueta")
    fig.suptitle("Seleccion del numero de segmentos", fontsize=13, weight="bold")
    fig.savefig(cfg["rutas"]["figuras"] / "05_seleccion_k.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    pd.DataFrame({"k": list(ks), "inercia": inercias, "silueta": siluetas}).to_csv(
        cfg["rutas"]["tablas"] / "05_seleccion_k.csv", index=False, encoding="utf-8"
    )

    k = p.get("k_elegido") or int(list(ks)[int(np.argmax(siluetas))])
    log.info("Numero de segmentos elegido: k=%d", k)
    return k


def segmentar(df: pd.DataFrame, cfg: dict) -> tuple[pd.Series, pd.DataFrame]:
    """Aplica K-Means y devuelve la etiqueta de segmento y el perfil de cada grupo."""
    p = cfg["no_supervisado"]
    X_bruto, usadas = _matriz(df, p["variables"])

    preproceso = Pipeline(
        [("imputador", SimpleImputer(strategy="median")), ("escalador", StandardScaler())]
    )
    X = preproceso.fit_transform(X_bruto)

    k = elegir_k(X, cfg)
    kmeans = KMeans(n_clusters=k, random_state=p["semilla"], n_init=10)
    etiquetas = pd.Series(kmeans.fit_predict(X) + 1, index=df.index, name="id_segmento")

    joblib.dump(
        {"preproceso": preproceso, "kmeans": kmeans, "variables": usadas},
        cfg["rutas"]["artefactos"] / "kmeans_segmentos.pkl",
    )

    perfil = _perfilar(df.assign(id_segmento=etiquetas), cfg)
    _graficar_pca(X, etiquetas, cfg)
    return etiquetas, perfil


def _perfilar(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Traduce cada cluster a lenguaje de negocio. Sin esto, un cluster es solo un numero."""
    perfil = (
        df.groupby("id_segmento")
        .agg(
            n_inmuebles=("precio", "size"),
            precio_promedio=("precio", "mean"),
            precio_m2_prom=("precio_m2", "mean"),
            area_promedio=("superficie_total", "mean"),
            habitaciones_prom=("habitaciones", "mean"),
            banos_prom=("banos", "mean"),
        )
        .round(2)
        .reset_index()
    )

    # Etiqueta legible segun el precio por m2 relativo del grupo
    orden = perfil["precio_m2_prom"].rank(pct=True)
    nombres = pd.cut(
        orden,
        bins=[0, 0.25, 0.5, 0.75, 1.0],
        labels=["Economico", "Estandar", "Alto", "Premium"],
        include_lowest=True,
    ).astype(str)
    perfil["nombre_segmento"] = [
        f"S{i} - {n}" for i, n in zip(perfil["id_segmento"], nombres)
    ]
    perfil["descripcion"] = perfil.apply(
        lambda r: (
            f"{r['n_inmuebles']:,.0f} inmuebles | area media {r['area_promedio']:.0f} m2 | "
            f"{r['habitaciones_prom']:.1f} hab | {r['precio_m2_prom']/1e6:.2f} M COP/m2"
        ),
        axis=1,
    )

    perfil.to_csv(cfg["rutas"]["tablas"] / "06_perfil_segmentos.csv", index=False, encoding="utf-8")
    log.info("Perfil de segmentos:\n%s", perfil.to_string(index=False))
    return perfil


def _graficar_pca(X: np.ndarray, etiquetas: pd.Series, cfg: dict) -> None:
    """Proyecta los grupos a 2 dimensiones con PCA para poder verlos."""
    pca = PCA(n_components=2, random_state=cfg["no_supervisado"]["semilla"])
    muestra = np.random.default_rng(cfg["no_supervisado"]["semilla"]).choice(
        len(X), size=min(8000, len(X)), replace=False
    )
    coords = pca.fit_transform(X)[muestra]

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.scatterplot(
        x=coords[:, 0], y=coords[:, 1],
        hue=etiquetas.to_numpy()[muestra],
        palette="tab10", s=14, alpha=0.6, ax=ax, legend="full",
    )
    var = pca.explained_variance_ratio_
    ax.set(
        title="Segmentos del mercado proyectados con PCA",
        xlabel=f"Componente 1 ({var[0]:.1%} de la varianza)",
        ylabel=f"Componente 2 ({var[1]:.1%} de la varianza)",
    )
    ax.legend(title="Segmento")
    fig.savefig(cfg["rutas"]["figuras"] / "06_segmentos_pca.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    log.info("PCA: las 2 componentes explican el %.1f%% de la varianza", var.sum() * 100)


def ejecutar(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Punto de entrada: agrega es_anomalo e id_segmento al DataFrame."""
    df = df.copy()
    df["es_anomalo"] = detectar_anomalias(df, cfg)

    # Los grupos se calculan sobre los avisos NO anomalos para no deformar los centroides
    limpios = df[df["es_anomalo"] == 0]
    etiquetas, perfil = segmentar(limpios, cfg)

    df["id_segmento"] = etiquetas
    df["id_segmento"] = df["id_segmento"].fillna(-1).astype(int)  # -1 = anomalo, sin segmento
    return df, perfil
