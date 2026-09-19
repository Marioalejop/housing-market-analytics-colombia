# Valoración y segmentación del mercado de vivienda en Colombia

[![Abrir en Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Marioalejop/housing-market-analytics-colombia/blob/main/Demo_Sustentacion_Grupo6.ipynb)

Proyecto final de **Business Analytics & Big Data II** (Ingeniería de Software VIII, Universitaria de
Colombia) · **Grupo 6**.

A partir de **1.000.000 de avisos** de vivienda de Properati, el proyecto revisa la calidad de los datos,
los limpia, los explora y entrena dos modelos: uno que **estima el precio** de una vivienda y otro que
la **clasifica en cuatro perfiles**.

## El proyecto en un solo notebook

Todo el trabajo está en **[`Demo_Sustentacion_Grupo6.ipynb`](Demo_Sustentacion_Grupo6.ipynb)**: no depende
de ningún otro código. Cada celda va precedida de un recuadro que explica **qué hace, por qué y qué
observar**, y las secciones siguen el orden de la presentación:

| Sección | Qué responde |
|---|---|
| 2. Dataset | ¿De dónde salen los datos y cómo son? |
| 3. Variables | ¿Qué significa cada columna y para qué se usa? |
| 4. Data Quality | ¿Qué problemas tienen los datos? |
| 5. Data Cleaning | ¿Qué se hizo para corregirlos y por qué? |
| 6. Exploración | ¿Qué dicen los datos? |
| 7. ML supervisado | ¿Cuánto vale una vivienda? |
| 8. ML no supervisado | ¿Qué grupos de vivienda existen? |
| 9. Resultados | ¿Qué se aprendió y qué decisión habilita? |
| 10. Limitaciones | ¿Qué no se pudo resolver? |

El notebook se sube **ya ejecutado**, así que se puede leer en GitHub sin correr nada.

## Resultados

| | |
|---|---|
| Avisos analizados | 1.000.000 |
| Avisos útiles tras la limpieza | 16.204 (1,62 %) |
| Mejor modelo | Gradient Boosting con ciudad |
| R² | **0,79** (regresión lineal: 0,59) |
| Error medio (MAE) | 134 millones de pesos (22 % del precio) |
| Perfiles de vivienda | 4 (K-Means) |

> **Limitación principal:** el **área falta en el 94 % de los avisos de venta de vivienda**, y es la
> variable que más explica el precio. Por eso solo 16.204 avisos llegan al modelo.

## Contenido del repositorio

```
Demo_Sustentacion_Grupo6.ipynb    Todo el proyecto: datos, limpieza, modelos y resultados
presentacion/
  Presentacion_Final_Grupo6.html  Presentación de 10 diapositivas (se abre en el navegador)
  construir_presentacion.py       Regenera la presentación desde los resultados del notebook
salida/                           Lo que produce el notebook (ver abajo)
datos/                            Datasets (el principal se descarga; ver más abajo)
docs/ishikawa_etapa1.png          Diagrama de Ishikawa de la Etapa 1
requirements.txt
```

## Cómo ejecutarlo

**En Google Colab (recomendado).** Abrir con el botón de arriba y elegir *Entorno de ejecución →
Ejecutar todas*. El notebook descarga los datos por sí solo. Tarda unos 2 a 3 minutos.

**En el computador.**

```bash
pip install -r requirements.txt jupyter
jupyter notebook Demo_Sustentacion_Grupo6.ipynb
```

Ejecutar todas las celdas. Si `datos/co_properties.csv` no existe, el notebook lo descarga de Kaggle.

## Los datos

| | |
|---|---|
| **Principal** | [Colombia Housing Properties Price](https://www.kaggle.com/datasets/julianusugaortiz/colombia-housing-properties-price) (avisos de Properati) |
| Tamaño | 1.000.000 registros × 25 variables · CSV de 618 MB |
| Periodo | 26 de julio de 2020 a 19 de agosto de 2021 |
| Licencia | «Unknown» en Kaggle: **uso exclusivamente académico** |
| **Apoyo** | [Medellín Properties 2023](https://www.kaggle.com/datasets/cesaregr/medelln-properties) · 9.999 × 12 · Apache 2.0 |

El archivo principal **no se sube al repositorio** por su tamaño. En `datos/` sí están el dataset de
Medellín y `co_properties_muestra_5000.csv`, una muestra de 5.000 avisos de venta de vivienda para
inspeccionar la estructura sin descargar nada.

## Lo que produce el notebook (`salida/`)

| Archivo | Para qué sirve |
|---|---|
| `resumen.json` | Todas las cifras del proyecto. De aquí sale la presentación |
| `figuras/` | Las gráficas que usa la presentación |
| `viviendas_powerbi.csv` | Viviendas limpias con segmento y precio estimado, listo para **Power BI** |

Para el dashboard: *Power BI → Obtener datos → Texto o CSV → `salida/viviendas_powerbi.csv`*.

Después de volver a ejecutar el notebook, la presentación se regenera con:

```bash
python presentacion/construir_presentacion.py
```

## Decisiones importantes

- **Anular, no adivinar.** Cuando un dato es incoherente (por ejemplo, área construida mayor que la
  total) se deja en nulo en lugar de inventar un valor.
- **Sin fuga de datos.** El segmento del K-Means se calcula con el precio, así que **no** se usa como
  variable para predecir el precio. Tampoco se usan los días publicados, que solo se conocen después de
  publicar el aviso.
- **k = 4 por interpretación de negocio.** La silueta no favorece claramente a ningún número de grupos.
- **Estimaciones honestas.** El precio estimado de cada aviso sale de un modelo que no lo vio entrenar
  (validación cruzada de 5 partes).

## Limitaciones

- Faltan datos: el área falta en el 94 % de las ventas de vivienda.
- Los avisos registran el **precio pedido**, no el de cierre.
- Los datos son de 2020 y 2021: no reflejan los precios actuales.
- Un aviso dado de baja no significa que el inmueble se vendió.

## Integrantes

Maria Alejandra Toro Ortiz · Mario Alejandro Peña Arenas · Javier Alexander Moreno Avila ·
Kevin Steven Guzmán Acevedo

Docente: Oscar Castiblanco · Universitaria de Colombia
