"""
Exporta las vistas de consumo de vivienda.db a archivos CSV
para importarlas directamente en Power BI (sin necesitar ODBC).

Uso:
    python exportar_vistas_powerbi.py

Genera los archivos en la carpeta: data/export/
"""

import sqlite3
import pandas as pd
from pathlib import Path

# Ruta a la base de datos (ajusta si tu vivienda.db está en otro lugar)
RUTA_DB = Path("db") / "vivienda.db"
CARPETA_SALIDA = Path("data") / "export"

VISTAS = [
    "v_evolucion_mensual",
    "v_inmuebles",
    "v_kpi_ciudad",
    "v_oportunidades",
    "v_segmentos",
]


def main():
    if not RUTA_DB.exists():
        raise FileNotFoundError(
            f"No se encontro la base de datos en: {RUTA_DB.resolve()}\n"
            "Verifica que estas ejecutando este script desde la carpeta del proyecto."
        )

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(RUTA_DB)
    try:
        for vista in VISTAS:
            try:
                df = pd.read_sql_query(f"SELECT * FROM {vista}", conexion)
            except Exception as e:
                print(f"  [AVISO] No se pudo leer '{vista}': {e}")
                continue

            ruta_csv = CARPETA_SALIDA / f"{vista}.csv"
            df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
            print(f"  OK -> {ruta_csv}  ({len(df):,} filas x {df.shape[1]} columnas)")
    finally:
        conexion.close()

    print(f"\nListo. Archivos CSV disponibles en: {CARPETA_SALIDA.resolve()}")


if __name__ == "__main__":
    main()
