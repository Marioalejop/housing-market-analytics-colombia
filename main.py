"""Orquestador del proyecto de Business Analytics.

Ejecuta el pipeline completo o una etapa concreta:

    python main.py etl         Etapas 2 y 4: extraer, transformar y cargar a SQLite
    python main.py eda         Etapa 3: exploracion (figuras y tablas)
    python main.py segmentar   Etapa 5a: aprendizaje NO supervisado
    python main.py entrenar    Etapa 5b: aprendizaje supervisado
    python main.py vistas      Crea/recrea las vistas de consumo para Power BI
    python main.py todo        Todo lo anterior, en orden

Opciones:
    --muestra N     Trabaja solo con las primeras N filas (desarrollo rapido)
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

# En Windows la consola usa cp1252 por defecto y rompe los acentos de las
# ciudades colombianas. Forzamos UTF-8 en la salida estandar.
for flujo in (sys.stdout, sys.stderr):
    if hasattr(flujo, "reconfigure"):
        flujo.reconfigure(encoding="utf-8", errors="replace")

from src.config import RAIZ, asegurar_directorios, cargar_config
from src.utils.log import obtener_logger


def _titulo(texto: str, log) -> None:
    log.info("=" * 78)
    log.info(texto.upper())
    log.info("=" * 78)


def _leer_limpio(cfg: dict) -> pd.DataFrame:
    """Recupera el dataset ya procesado por el ETL."""
    ruta = cfg["rutas"]["processed"] / "inmuebles_limpio.parquet"
    if not ruta.exists():
        raise FileNotFoundError(
            "No existe el dataset limpio. Ejecuta primero:  python main.py etl"
        )
    return pd.read_parquet(ruta)


def _actualizar_hechos(cfg: dict, datos: pd.DataFrame, columnas: list[str]) -> None:
    """Actualiza columnas de hecho_inmueble usando una tabla temporal (rapido y atomico)."""
    con = sqlite3.connect(cfg["rutas"]["base_datos"])
    try:
        datos[["id_inmueble", *columnas]].to_sql("_stage", con, if_exists="replace", index=False)
        asignaciones = ", ".join(f"{c} = s.{c}" for c in columnas)
        con.execute(
            f"""
            UPDATE hecho_inmueble AS h
               SET {asignaciones}
              FROM _stage AS s
             WHERE s.id_inmueble = h.id_inmueble
            """
        )
        con.execute("DROP TABLE _stage")
        con.commit()
    finally:
        con.close()


# --------------------------------------------------------------------- etapas


def etapa_etl(cfg: dict, log) -> None:
    from src.etl.extract import extraer
    from src.etl.load import cargar
    from src.etl.transform import transformar

    _titulo("Etapas 2 y 4 | Extraccion, transformacion y carga", log)
    crudo = extraer(cfg)
    limpio, auditoria = transformar(crudo, cfg)
    cargar(limpio, auditoria, cfg, RAIZ / "sql" / "01_schema.sql")

    auditoria.a_dataframe().to_csv(
        cfg["rutas"]["tablas"] / "00_auditoria_etl.csv", index=False, encoding="utf-8"
    )


def etapa_eda(cfg: dict, log) -> None:
    from src.eda.explorar import explorar

    _titulo("Etapa 3 | Exploracion de los datos", log)
    explorar(_leer_limpio(cfg), cfg)


def etapa_segmentar(cfg: dict, log) -> None:
    from src.modelos import no_supervisado

    _titulo("Etapa 5a | Aprendizaje no supervisado", log)
    df = _leer_limpio(cfg)
    df, perfil = no_supervisado.ejecutar(df, cfg)

    # Persistimos el resultado: dimension de segmentos + marcas en los hechos
    con = sqlite3.connect(cfg["rutas"]["base_datos"])
    try:
        perfil.rename(columns={"nombre_segmento": "nombre_segmento"})[
            ["id_segmento", "nombre_segmento", "n_inmuebles", "precio_promedio",
             "precio_m2_prom", "area_promedio", "habitaciones_prom", "descripcion"]
        ].to_sql("dim_segmento", con, if_exists="replace", index=False)
        con.commit()
    finally:
        con.close()

    _actualizar_hechos(cfg, df, ["id_segmento", "es_anomalo"])
    df.to_parquet(cfg["rutas"]["processed"] / "inmuebles_limpio.parquet", index=False)
    log.info("Segmentos y marcas de anomalia guardados en la base de datos.")


def etapa_entrenar(cfg: dict, log) -> None:
    from src.modelos.supervisado import entrenar

    _titulo("Etapa 5b | Aprendizaje supervisado", log)
    df = _leer_limpio(cfg)
    if "id_segmento" not in df.columns:
        log.warning("Aun no hay segmentos. Ejecuta 'python main.py segmentar' para mejorar el modelo.")

    tabla, predicciones = entrenar(df, cfg)

    con = sqlite3.connect(cfg["rutas"]["base_datos"])
    try:
        tabla.assign(ejecucion=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")).to_sql(
            "modelo_metricas", con, if_exists="append", index=False
        )
        con.commit()
    finally:
        con.close()

    _actualizar_hechos(cfg, predicciones, ["precio_estimado", "error_estimacion"])
    predicciones.to_csv(
        cfg["rutas"]["tablas"] / "09_predicciones_test.csv", index=False, encoding="utf-8"
    )
    log.info("Metricas y predicciones guardadas en la base de datos.")


def etapa_vistas(cfg: dict, log) -> None:
    _titulo("Vistas de consumo para Power BI", log)
    sql = (RAIZ / "sql" / "02_vistas_powerbi.sql").read_text(encoding="utf-8")
    con = sqlite3.connect(cfg["rutas"]["base_datos"])
    try:
        con.executescript(sql)
        con.commit()
        vistas = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name", con
        )
        log.info("Vistas disponibles: %s", ", ".join(vistas["name"]))
    finally:
        con.close()


# ----------------------------------------------------------------------- cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de Business Analytics - vivienda")
    parser.add_argument(
        "etapa",
        choices=["etl", "eda", "segmentar", "entrenar", "vistas", "todo"],
        help="Etapa del proyecto a ejecutar",
    )
    parser.add_argument("--muestra", type=int, default=None, help="Limitar el numero de filas")
    args = parser.parse_args()

    cfg = cargar_config()
    asegurar_directorios(cfg)
    if args.muestra:
        cfg["extraccion"]["muestra_filas"] = args.muestra

    log = obtener_logger("main", cfg["rutas"]["logs"])
    log.info("Proyecto: %s v%s", cfg["proyecto"]["nombre"], cfg["proyecto"]["version"])

    etapas = {
        "etl": etapa_etl,
        "eda": etapa_eda,
        "segmentar": etapa_segmentar,
        "entrenar": etapa_entrenar,
        "vistas": etapa_vistas,
    }
    secuencia = ["etl", "eda", "segmentar", "entrenar", "vistas"] if args.etapa == "todo" else [args.etapa]

    for nombre in secuencia:
        etapas[nombre](cfg, log)

    log.info("Proceso finalizado correctamente.")


if __name__ == "__main__":
    main()
