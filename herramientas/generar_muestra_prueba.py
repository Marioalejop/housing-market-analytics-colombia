"""Genera un archivo de PRUEBA con el mismo esquema del dataset real.

ATENCION: estos datos son sinteticos y sirven UNICAMENTE para verificar que
el pipeline corre de principio a fin. Los resultados del proyecto deben
obtenerse con el dataset real descargado en data/raw.

Uso:
    python herramientas/generar_muestra_prueba.py --filas 20000
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent

CIUDADES = {
    "Bogotá D.C": ("Bogotá D.C", 4.65, -74.09, 6.5e6),
    "Medellín": ("Antioquia", 6.24, -75.57, 5.4e6),
    "Cali": ("Valle Del Cauca", 3.44, -76.52, 3.6e6),
    "Barranquilla": ("Atlántico", 10.96, -74.80, 3.9e6),
    "Bucaramanga": ("Santander", 7.12, -73.12, 3.4e6),
    "Cartagena": ("Bolívar", 10.39, -75.51, 5.8e6),
}
BARRIOS = ["Centro", "Norte", "Sur", "Chapinero", "El Poblado", "Laureles", "Ciudad Jardín"]


def generar(n: int, semilla: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    ciudad = rng.choice(list(CIUDADES), size=n, p=[0.35, 0.22, 0.14, 0.12, 0.09, 0.08])
    depto = np.array([CIUDADES[c][0] for c in ciudad])
    base_m2 = np.array([CIUDADES[c][3] for c in ciudad])
    lat = np.array([CIUDADES[c][1] for c in ciudad]) + rng.normal(0, 0.05, n)
    lon = np.array([CIUDADES[c][2] for c in ciudad]) + rng.normal(0, 0.05, n)

    superficie = rng.lognormal(4.5, 0.45, n).clip(25, 900).round(0)
    habitaciones = np.clip((superficie / 40 + rng.normal(0, 0.8, n)).round(), 1, 8)
    banos = np.clip((habitaciones * 0.6 + rng.normal(0, 0.6, n)).round(), 1, 6)
    tipo = rng.choice(["Apartamento", "Casa"], n, p=[0.72, 0.28])

    precio_m2 = base_m2 * rng.lognormal(0, 0.28, n) * np.where(tipo == "Casa", 0.88, 1.0)
    precio = (precio_m2 * superficie).round(-5)

    fechas = pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 1000, n), unit="D")

    df = pd.DataFrame(
        {
            "start_date": fechas.strftime("%Y-%m-%d"),
            "lat": lat.round(5),
            "lon": lon.round(5),
            "l1": "Colombia",
            "l2": depto,
            "l3": ciudad,
            "l4": rng.choice(BARRIOS, n),
            "rooms": habitaciones,
            "bedrooms": np.clip(habitaciones - 1, 1, None),
            "bathrooms": banos,
            "surface_total": superficie,
            "surface_covered": (superficie * rng.uniform(0.7, 1.0, n)).round(0),
            "price": precio,
            "currency": "COP",
            "property_type": tipo,
            "operation_type": rng.choice(["Venta", "Arriendo"], n, p=[0.8, 0.2]),
        }
    )

    # --- Suciedad deliberada: es lo que el ETL debe saber resolver ---
    idx = lambda frac: rng.choice(n, int(n * frac), replace=False)
    df.loc[idx(0.12), "surface_covered"] = np.nan     # nulos imputables
    df.loc[idx(0.08), "bathrooms"] = np.nan           # nulos con imputacion contextual
    df.loc[idx(0.05), "l4"] = np.nan                  # nulos que se etiquetan
    df.loc[idx(0.04), "price"] = np.nan               # nulos NO imputables -> se eliminan
    df.loc[idx(0.02), "price"] = 0                    # valores imposibles
    df.loc[idx(0.01), "surface_total"] = 3            # areas absurdas
    df.loc[idx(0.02), "bathrooms"] = 40               # atipicos groseros

    en_usd = idx(0.06)                                 # avisos en otra moneda
    df.loc[en_usd, "price"] = (df.loc[en_usd, "price"] / 4000).round(0)
    df.loc[en_usd, "currency"] = "USD"

    duplicados = df.sample(int(n * 0.07), random_state=semilla)  # avisos republicados
    df = pd.concat([df, duplicados], ignore_index=True).sample(frac=1, random_state=semilla)
    return df.reset_index(drop=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filas", type=int, default=20000)
    parser.add_argument("--salida", default="data/raw/muestra_prueba.csv")
    args = parser.parse_args()

    destino = RAIZ / args.salida
    destino.parent.mkdir(parents=True, exist_ok=True)
    df = generar(args.filas)
    df.to_csv(destino, index=False, encoding="utf-8")
    print(f"Archivo de PRUEBA generado: {destino}  ({len(df):,} filas)")
    print("Recuerda: para el proyecto final usa el dataset real.")
