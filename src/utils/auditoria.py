"""Registro de auditoria del ETL.

Cada paso de limpieza deja constancia de cuantas filas entraron, cuantas
salieron y por que. Este registro se guarda en la base de datos y es la
evidencia de que el pre-procesamiento fue trazable y no una caja negra.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class Auditoria:
    """Acumula el resultado de cada paso del ETL."""

    ejecucion: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    pasos: list[dict] = field(default_factory=list)

    def registrar(self, paso: str, filas_antes: int, filas_despues: int, detalle: str = "") -> None:
        eliminadas = filas_antes - filas_despues
        pct = (eliminadas / filas_antes * 100) if filas_antes else 0.0
        self.pasos.append(
            {
                "ejecucion": self.ejecucion,
                "orden": len(self.pasos) + 1,
                "paso": paso,
                "filas_antes": filas_antes,
                "filas_despues": filas_despues,
                "filas_eliminadas": eliminadas,
                "pct_eliminado": round(pct, 3),
                "detalle": detalle,
            }
        )

    def a_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.pasos)

    def resumen(self) -> str:
        if not self.pasos:
            return "Sin pasos registrados."
        lineas = [f"{'PASO':<38} {'ANTES':>10} {'DESPUES':>10} {'ELIMIN.':>10} {'%':>7}"]
        lineas.append("-" * 80)
        for p in self.pasos:
            lineas.append(
                f"{p['paso']:<38} {p['filas_antes']:>10,} {p['filas_despues']:>10,} "
                f"{p['filas_eliminadas']:>10,} {p['pct_eliminado']:>6.2f}%"
            )
        inicial, final = self.pasos[0]["filas_antes"], self.pasos[-1]["filas_despues"]
        retencion = (final / inicial * 100) if inicial else 0
        lineas.append("-" * 80)
        lineas.append(f"Retencion final: {final:,} de {inicial:,} filas ({retencion:.2f}%)")
        return "\n".join(lineas)
