"""ETAPA 5b - APRENDIZAJE SUPERVISADO.

Problema: estimar el precio de venta de un inmueble (regresion).

Se comparan cuatro modelos de complejidad creciente para poder argumentar
la eleccion, no solo presentar un numero:

  1. Ridge                    -> linea base interpretable
  2. Random Forest            -> arboles en paralelo (bagging)
  3. Gradient Boosting        -> arboles secuenciales (boosting)
  4. Red neuronal (Keras)     -> continuidad del trabajo previo del curso

Todos entrenan sobre log(precio): el precio es fuertemente asimetrico y el
logaritmo estabiliza la varianza. Las metricas SIEMPRE se reportan en pesos.
"""
from __future__ import annotations

import time

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.utils.log import obtener_logger

log = obtener_logger("modelos.supervisado")
sns.set_theme(style="whitegrid")

NUMERICAS = [
    "superficie_total", "superficie_cubierta", "habitaciones", "banos",
    "latitud", "longitud", "area_por_habitacion", "ratio_bano_habitacion", "pct_cubierta",
]
# NOTA: 'dias_publicado' se excluye a proposito. Solo se conoce cuando el aviso
# ya salio del portal, y el modelo debe sugerir un precio EN EL MOMENTO DE
# PUBLICAR. Incluirlo seria usar informacion del futuro. Esa variable se usa
# para analizar la rotacion (vista v_rotacion), no para estimar el precio.
CATEGORICAS = ["tipo_propiedad", "segmento_tamano", "ciudad", "id_segmento"]
TOP_CIUDADES = 30


def preparar_datos(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.Series, list, list]:
    """Selecciona variables de entrada y la variable objetivo."""
    p = cfg["supervisado"]
    df = df.copy()

    # Los avisos marcados como anomalos no entran al entrenamiento: son ruido conocido
    if "es_anomalo" in df.columns:
        antes = len(df)
        df = df[df["es_anomalo"] == 0]
        log.info("Se excluyen %s avisos anomalos del entrenamiento.", f"{antes - len(df):,}")

    # Ciudad tiene cientos de categorias: dejamos las mas frecuentes y agrupamos el resto
    if "ciudad" in df.columns:
        principales = df["ciudad"].value_counts().head(TOP_CIUDADES).index
        df["ciudad"] = df["ciudad"].where(df["ciudad"].isin(principales), "Otras")

    numericas = [c for c in NUMERICAS if c in df.columns]
    categoricas = [c for c in CATEGORICAS if c in df.columns]
    if not p["usar_cluster_como_variable"] and "id_segmento" in categoricas:
        categoricas.remove("id_segmento")
    if "id_segmento" in categoricas:
        df["id_segmento"] = df["id_segmento"].astype(str)

    X = df[numericas + categoricas]
    y = df[p["objetivo"]]
    log.info("Variables de entrada -> numericas: %s | categoricas: %s", numericas, categoricas)
    return X, y, numericas, categoricas


def _preprocesador(numericas: list[str], categoricas: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline([("imp", SimpleImputer(strategy="median")), ("esc", StandardScaler())]),
                numericas,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="most_frequent")),
                        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categoricas,
            ),
        ]
    )


def metricas(y_real: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """MAE y RMSE en millones de COP; R2 y MAPE adimensionales."""
    error = y_real - y_pred
    return {
        "mae": float(mean_absolute_error(y_real, y_pred)),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "r2": float(r2_score(y_real, y_pred)),
        "mape": float(np.mean(np.abs(error / y_real)) * 100),
    }


def _red_neuronal(n_entradas: int, cfg: dict):
    """Red densa. Continua el modelo del proyecto anterior, ahora con regularizacion."""
    from tensorflow import keras

    modelo = keras.Sequential(
        [
            keras.layers.Input(shape=(n_entradas,)),
            keras.layers.Dense(128, activation="relu"),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(64, activation="relu"),
            keras.layers.Dropout(0.1),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1),
        ]
    )
    modelo.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse", metrics=["mae"])
    return modelo


def entrenar(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Entrena y compara todos los modelos. Devuelve (metricas, predicciones del mejor)."""
    p = cfg["supervisado"]
    X, y, numericas, categoricas = preparar_datos(df, cfg)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=p["test_size"], random_state=p["semilla"]
    )
    log.info("Entrenamiento: %s | Prueba: %s", f"{len(X_train):,}", f"{len(X_test):,}")

    # Se aprende sobre el logaritmo del precio y se devuelve a pesos al evaluar
    y_train_log, y_test_real = np.log1p(y_train), y_test.to_numpy()

    prep = _preprocesador(numericas, categoricas)
    X_train_t = prep.fit_transform(X_train)
    X_test_t = prep.transform(X_test)
    log.info("Matriz de entrada tras codificar: %s columnas", X_train_t.shape[1])

    resultados, predicciones, modelos = [], {}, {}

    clasicos = {
        "Ridge (linea base)": Ridge(alpha=1.0),
        "Random Forest": RandomForestRegressor(
            n_estimators=300, max_depth=25, min_samples_leaf=2,
            random_state=p["semilla"], n_jobs=-1,
        ),
        "Gradient Boosting": HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.08, max_depth=None, random_state=p["semilla"]
        ),
    }

    for nombre, modelo in clasicos.items():
        inicio = time.perf_counter()
        modelo.fit(X_train_t, y_train_log)
        y_pred = np.expm1(modelo.predict(X_test_t))
        duracion = time.perf_counter() - inicio

        m = metricas(y_test_real, y_pred)
        m.update(modelo=nombre, segundos=round(duracion, 2))
        resultados.append(m)
        predicciones[nombre] = y_pred
        modelos[nombre] = modelo
        log.info(
            "%-22s | MAE %8.1f M | RMSE %8.1f M | R2 %.4f | MAPE %5.2f%% | %5.1fs",
            nombre, m["mae"] / 1e6, m["rmse"] / 1e6, m["r2"], m["mape"], duracion,
        )

    # ---- Red neuronal ----
    from tensorflow import keras

    inicio = time.perf_counter()
    red = _red_neuronal(X_train_t.shape[1], cfg)
    historial = red.fit(
        X_train_t, y_train_log,
        epochs=p["red_neuronal"]["epocas"],
        batch_size=p["red_neuronal"]["batch_size"],
        validation_split=0.2,
        callbacks=[
            keras.callbacks.EarlyStopping(
                patience=p["red_neuronal"]["paciencia_early_stopping"],
                restore_best_weights=True,
            )
        ],
        verbose=0,
    )
    y_pred = np.expm1(red.predict(X_test_t, verbose=0).flatten())
    duracion = time.perf_counter() - inicio

    m = metricas(y_test_real, y_pred)
    m.update(modelo="Red neuronal", segundos=round(duracion, 2))
    resultados.append(m)
    predicciones["Red neuronal"] = y_pred
    log.info(
        "%-22s | MAE %8.1f M | RMSE %8.1f M | R2 %.4f | MAPE %5.2f%% | %5.1fs",
        "Red neuronal", m["mae"] / 1e6, m["rmse"] / 1e6, m["r2"], m["mape"], duracion,
    )
    _curva_aprendizaje(historial, cfg)

    tabla = pd.DataFrame(resultados)[["modelo", "mae", "rmse", "r2", "mape", "segundos"]]
    tabla = tabla.sort_values("mae").reset_index(drop=True)
    tabla.to_csv(cfg["rutas"]["tablas"] / "07_comparacion_modelos.csv", index=False, encoding="utf-8")
    log.info("Comparacion de modelos:\n%s", tabla.to_string(index=False))

    mejor = tabla.loc[0, "modelo"]
    log.info("Mejor modelo por MAE: %s", mejor)

    # Guardado de artefactos: el preprocesador viaja con el modelo, siempre
    joblib.dump(prep, cfg["rutas"]["artefactos"] / "preprocesador.pkl")
    if mejor in modelos:
        joblib.dump(modelos[mejor], cfg["rutas"]["artefactos"] / "modelo_final.pkl")
        _importancia(modelos[mejor], prep, X_test_t, np.log1p(y_test_real), cfg)
    else:
        red.save(cfg["rutas"]["artefactos"] / "modelo_final.keras")

    _graficos_evaluacion(y_test_real, predicciones[mejor], mejor, cfg)

    salida = pd.DataFrame(
        {
            "id_inmueble": df.loc[X_test.index, "id_inmueble"].to_numpy(),
            "precio": y_test_real,
            "precio_estimado": predicciones[mejor],
        }
    )
    salida["error_estimacion"] = salida["precio_estimado"] - salida["precio"]
    return tabla, salida


def _curva_aprendizaje(historial, cfg: dict) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(historial.history["loss"], label="Entrenamiento")
    ax.plot(historial.history["val_loss"], label="Validacion")
    ax.set(title="Curva de aprendizaje de la red neuronal", xlabel="Epoca", ylabel="MSE (log precio)")
    ax.legend()
    fig.savefig(cfg["rutas"]["figuras"] / "07_curva_red_neuronal.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def _importancia(modelo, prep, X_test_t, y_test_log, cfg: dict) -> None:
    """Importancia por permutacion: que variables mueven realmente el precio."""
    nombres = prep.get_feature_names_out()
    muestra = min(3000, len(X_test_t))
    resultado = permutation_importance(
        modelo, X_test_t[:muestra], y_test_log[:muestra],
        n_repeats=5, random_state=cfg["supervisado"]["semilla"], n_jobs=-1,
    )
    imp = (
        pd.DataFrame({"variable": nombres, "importancia": resultado.importances_mean})
        .sort_values("importancia", ascending=False)
        .head(20)
    )
    imp.to_csv(cfg["rutas"]["tablas"] / "08_importancia_variables.csv", index=False, encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.barplot(data=imp, x="importancia", y="variable", color="#2b6cb0", ax=ax)
    ax.set(title="Importancia de variables (permutacion)", xlabel="Caida del desempeno", ylabel="")
    fig.savefig(cfg["rutas"]["figuras"] / "08_importancia_variables.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    log.info("Variables mas influyentes:\n%s", imp.head(10).to_string(index=False))


def _graficos_evaluacion(y_real, y_pred, nombre: str, cfg: dict) -> None:
    """ETAPA 6 - lectura visual del desempeno."""
    residuo = y_pred - y_real
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    axes[0].scatter(y_real / 1e6, y_pred / 1e6, alpha=0.25, s=10, color="#2b6cb0")
    lim = [0, np.percentile(y_real, 99) / 1e6]
    axes[0].plot(lim, lim, "r--", linewidth=1.5)
    axes[0].set(xlim=lim, ylim=lim, xlabel="Precio real (M COP)",
                ylabel="Precio estimado (M COP)", title="Estimado vs. real")

    axes[1].scatter(y_pred / 1e6, residuo / 1e6, alpha=0.25, s=10, color="#805ad5")
    axes[1].axhline(0, color="red", linestyle="--")
    axes[1].set(xlabel="Precio estimado (M COP)", ylabel="Residuo (M COP)",
                title="Residuos", xlim=lim)

    error_pct = residuo / y_real * 100
    sns.histplot(error_pct.clip(-100, 100), bins=60, ax=axes[2], color="#2c7a7b")
    axes[2].axvline(0, color="red", linestyle="--")
    axes[2].set(xlabel="Error porcentual (%)", title="Distribucion del error relativo")

    fig.suptitle(f"Evaluacion del modelo: {nombre}", fontsize=14, weight="bold")
    fig.savefig(cfg["rutas"]["figuras"] / "09_evaluacion_modelo.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
