"""Carga de la configuracion y resolucion de rutas del proyecto."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Raiz del proyecto = carpeta que contiene a src/
RAIZ = Path(__file__).resolve().parent.parent


def cargar_config(ruta: str | Path = "config.yaml") -> dict[str, Any]:
    """Lee config.yaml y devuelve un diccionario con toda la configuracion."""
    ruta = RAIZ / ruta
    with open(ruta, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # Convertimos las rutas relativas del YAML en rutas absolutas
    cfg["rutas"] = {k: (RAIZ / v) for k, v in cfg["rutas"].items()}
    return cfg


def asegurar_directorios(cfg: dict[str, Any]) -> None:
    """Crea las carpetas de salida si aun no existen."""
    for clave, ruta in cfg["rutas"].items():
        destino = ruta.parent if clave == "base_datos" else ruta
        destino.mkdir(parents=True, exist_ok=True)
