"""Genera el diagrama de Ishikawa (espina de pescado) de la Etapa 1.

El diagrama se construye por codigo para que sea reproducible y quede
versionado junto al proyecto: si una causa cambia, se edita CAUSAS y se
vuelve a ejecutar, en vez de rehacer un dibujo a mano.

Uso:
    python herramientas/generar_ishikawa.py
Salida:
    docs/ishikawa_etapa1.png   (listo para insertar en el documento de Word)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

RAIZ = Path(__file__).resolve().parent.parent

# Debe coincidir PALABRA POR PALABRA con el problema central declarado en el
# documento de la entrega. Si el diagrama y el texto dicen cosas distintas, la
# rubrica lo penaliza como incoherencia.
PROBLEMA = ("Dificultad para\nestablecer un precio\nde mercado adecuado\n"
            "para los inmuebles\nde vivienda")

# (categoria, [causas])  ->  las 3 primeras van arriba, las 3 siguientes abajo
CAUSAS = [
    ("PERSONAS", [
        "Los asesores fijan el precio “a ojo”,\nsin criterio técnico de valoración",
        "Falta de capacitación en tasación\nbasada en datos comparables",
    ]),
    ("PROCESOS", [
        "No existe un proceso estandarizado\npara calcular o validar el precio",
        "No hay revisión periódica de avisos\ncon mucho tiempo publicados",
    ]),
    # La guia del docente pide NO nombrar todavia las tecnicas (K-Means,
    # Machine Learning...): en la Etapa 1 se describe el problema, no la
    # solucion. Por eso las causas hablan de ausencia de herramientas, sin
    # mencionar el algoritmo.
    ("TECNOLOGÍA", [
        "No hay un modelo que estime\nel precio esperado",
        "No hay segmentación automática\ndel inventario",
    ]),
    ("PRODUCTO / SERVICIO", [
        "Alta heterogeneidad entre inmuebles\n(área, tipo, ubicación, antigüedad)",
        "Comparación manual entre inmuebles\ninviable a escala",
    ]),
    ("INFORMACIÓN / DATOS", [
        "Avisos con nulos, duplicados y\nprecios en distintas monedas",
        "Solo hay precio de publicación,\nno precio de cierre real",
    ]),
    ("ENTORNO", [
        "Fluctuación del mercado\ninmobiliario",
        "Variables macro: tasa de cambio\ne inflación",
    ]),
]

AZUL = "#1f3864"      # espina central y titulos (azul institucional)
GRIS = "#333333"

# Un color por categoria, en el mismo orden de CAUSAS. Ayuda a leer el
# diagrama de un vistazo sin depender del color para entenderlo: la etiqueta
# de texto sigue siendo la que identifica cada categoria.
COLORES = [
    "#2b6cb0",   # Personas          - azul
    "#c05621",   # Procesos          - naranja
    "#276749",   # Tecnologia        - verde
    "#9b2c2c",   # Producto/Servicio - rojo
    "#553c9a",   # Informacion/Datos - morado
    "#7b4b23",   # Entorno           - cafe
]


def dibujar() -> Path:
    fig, ax = plt.subplots(figsize=(17, 9.5))
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 9.5)
    ax.axis("off")

    y_espina = 4.75
    x_ini, x_fin = 0.6, 13.15

    # --- Espina central ---
    ax.annotate(
        "",
        xy=(x_fin, y_espina),
        xytext=(x_ini, y_espina),
        arrowprops=dict(arrowstyle="-|>", linewidth=3.2, color=AZUL, mutation_scale=32),
    )

    # --- Cabeza: el problema ---
    cabeza = FancyBboxPatch(
        (13.35, y_espina - 1.55), 3.4, 3.1,
        boxstyle="round,pad=0.12,rounding_size=0.18",
        linewidth=2.6, edgecolor=AZUL, facecolor="#f2dcdb",
    )
    ax.add_patch(cabeza)
    ax.text(
        15.05, y_espina + 1.02, "PROBLEMA CENTRAL",
        ha="center", va="center", fontsize=10.5, weight="bold", color=AZUL,
    )
    ax.text(
        15.05, y_espina - 0.22, PROBLEMA,
        ha="center", va="center", fontsize=11, color=GRIS, linespacing=1.5,
    )

    # --- Espinas por categoria ---
    x_bases = [3.0, 7.0, 11.0]         # punto donde la espina toca el eje
    desplazamiento = 2.2               # cuanto se inclina hacia atras
    alto = 2.9                         # altura de la espina

    for i, (categoria, causas) in enumerate(CAUSAS):
        arriba = i < 3
        x_base = x_bases[i % 3]
        signo = 1 if arriba else -1
        color = COLORES[i]

        x_punta = x_base - desplazamiento
        y_punta = y_espina + signo * alto

        # Linea diagonal de la espina, en el color de la categoria
        ax.plot(
            [x_punta, x_base], [y_punta, y_espina],
            color=color, linewidth=2.6, solid_capstyle="round", zorder=2,
        )

        # Etiqueta de la categoria: fondo solido y texto blanco
        ax.text(
            x_punta, y_punta + signo * 0.42, categoria,
            ha="center", va="center", fontsize=11.5, weight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.42", facecolor=color,
                      edgecolor=color, linewidth=1.6),
            zorder=4,
        )

        # Causas: pequenas ramas sobre la diagonal
        for j, causa in enumerate(causas, start=1):
            t = j / (len(causas) + 1)          # posicion a lo largo de la diagonal
            x_rama = x_base + (x_punta - x_base) * t
            y_rama = y_espina + (y_punta - y_espina) * t

            ax.plot(
                [x_rama, x_rama + 0.28], [y_rama, y_rama],
                color=color, linewidth=1.8, zorder=2,
            )
            ax.text(
                x_rama + 0.40, y_rama, causa,
                ha="left", va="center", fontsize=8.6, color=GRIS, linespacing=1.35,
                zorder=3,
            )

    # --- Titulo ---
    ax.text(
        0.35, 9.15,
        "Diagrama de Ishikawa — Etapa 1: Identificación de la necesidad",
        ha="left", va="top", fontsize=15, weight="bold", color=AZUL,
    )
    ax.text(
        0.35, 8.72,
        "Valoración y segmentación del mercado de vivienda en Colombia  ·  "
        "Business Analytics & Big Data II",
        ha="left", va="top", fontsize=10, color="#666666",
    )

    destino = RAIZ / "docs" / "ishikawa_etapa1.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return destino


if __name__ == "__main__":
    ruta = dibujar()
    print(f"Diagrama generado: {ruta}")
