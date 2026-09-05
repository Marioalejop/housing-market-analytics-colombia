"""Logger unico para todo el pipeline: escribe en consola y en logs/pipeline.log."""
from __future__ import annotations

import logging
from pathlib import Path

_CONFIGURADO = False


def obtener_logger(nombre: str, carpeta_logs: Path | None = None) -> logging.Logger:
    global _CONFIGURADO
    if not _CONFIGURADO:
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s",
            datefmt="%H:%M:%S",
        )
        raiz = logging.getLogger("vivienda")
        raiz.setLevel(logging.INFO)

        consola = logging.StreamHandler()
        consola.setFormatter(formato)
        raiz.addHandler(consola)

        if carpeta_logs is not None:
            carpeta_logs.mkdir(parents=True, exist_ok=True)
            archivo = logging.FileHandler(carpeta_logs / "pipeline.log", encoding="utf-8")
            archivo.setFormatter(formato)
            raiz.addHandler(archivo)

        _CONFIGURADO = True

    return logging.getLogger(f"vivienda.{nombre}")
