# Valoración y segmentación del mercado de vivienda en Colombia

Proyecto de **Business Analytics & Big Data II**. Pipeline ETL en Python sobre datos
inmobiliarios reales, con base de datos dimensional, modelos de aprendizaje
supervisado y no supervisado, y salida preparada para Power BI.

---

## 1. Necesidad de negocio (Etapa 1)

> **Actor:** una inmobiliaria o un portal de avisos clasificados.
>
> **Problema:** los precios de publicación los fija cada vendedor "a ojo". Eso produce
> inmuebles sobrevalorados que no rotan y subvalorados que dejan dinero sobre la mesa.
> Además, la empresa no tiene una lectura clara de qué segmentos componen su inventario.
>
> **Preguntas que responde el proyecto:**
>
> 1. ¿Cuál es el precio de mercado esperado de un inmueble dadas sus características?
>    *(regresión — aprendizaje supervisado)*
> 2. ¿Qué grupos naturales de inmuebles existen en el mercado, sin decidirlo a priori?
>    *(clustering — aprendizaje no supervisado)*
> 3. ¿Qué avisos están publicados muy por debajo de su valor estimado?
>    *(oportunidades de compra — cruce de ambos modelos)*
>
> **Decisión que habilita:** sugerir un precio de publicación, priorizar la captación de
> inventario por segmento y alertar sobre oportunidades.

El análisis de causas está en [`docs/ishikawa_etapa1.png`](docs/ishikawa_etapa1.png), generado
por código con `python herramientas/generar_ishikawa.py`. La ficha de la Etapa 1 en Word se
maneja en la carpeta local y se sube a la plataforma de la Universidad; no va al repositorio.

---

## 2. Datos (Etapa 2)

**Dataset principal:** [Colombia Housing Properties Price](https://www.kaggle.com/datasets/julianusugaortiz/colombia-housing-properties-price)
(`co_properties.csv`, avisos del portal Properati Colombia): 1.000.000 de avisos y 25 variables,
publicados entre julio de 2020 y agosto de 2021. CSV de 589 MB (146 MB comprimido). La licencia
figura como «Unknown» en Kaggle; se usa solo con fines académicos.

**Dataset de apoyo:** [Medellín Properties (2023)](https://www.kaggle.com/datasets/cesaregr/medelln-properties)
(`medellin_properties.csv`): 9.999 inmuebles y 12 variables, licencia Apache 2.0. Trae el área
completa, el estrato y la antigüedad, que sirven para validar la relación entre área y precio.

La comparación de candidatos y la justificación de la selección están en la ficha de la Etapa 2.

Se eligió el dataset principal por tres razones:

- **Viene sucio de verdad** (nulos masivos, duplicados, precios en 0, avisos de venta con periodo
  de precio mensual) → hay ETL real que hacer.
- **Tiene dimensiones** (geografía y tiempo) → permite un modelo en estrella y un dashboard con sentido.
- **Tiene volumen** → obliga a leer por bloques y a usar formatos columnares.

> **Limitación principal:** entre los 465.424 avisos de venta de casas y apartamentos, el área
> falta en el 94,5 %. Es el cuello de botella del modelo de precio; la Etapa 4 evaluará si puede
> recuperarse desde el texto de la descripción.

**Ubicación en Properati:** `l1` país, `l2` departamento, `l3` ciudad, `l4` zona, `l5` localidad y
`l6` barrio. Como el barrio está vacío en el 94,5 % de los avisos, el análisis por ubicación se
hace por ciudad y zona.

**Instalación de los datos** (la descarga pública no requiere cuenta de Kaggle):

```bash
curl -L -o co_properties.zip "https://www.kaggle.com/api/v1/datasets/download/julianusugaortiz/colombia-housing-properties-price"
unzip co_properties.zip -d data/raw/
```

Resultado esperado: `data/raw/co_properties.csv`, de 617.694.986 bytes.

Si usas otro dataset con nombres de columna distintos, ajusta **solo** el bloque
`mapeo_columnas` de `config.yaml`. El resto del código no se toca.

---

## 3. Cómo ejecutar

```bash
pip install -r requirements.txt

python main.py todo              # pipeline completo
```

O etapa por etapa:

| Comando | Etapa del proyecto | Qué hace |
|---|---|---|
| `python main.py etl` | 2 y 4 | Extrae, limpia, transforma y carga a SQLite |
| `python main.py eda` | 3 | Exploración: figuras y tablas descriptivas |
| `python main.py segmentar` | 5a | Isolation Forest + K-Means (no supervisado) |
| `python main.py entrenar` | 5b | Compara 4 modelos de regresión (supervisado) |
| `python main.py vistas` | 6 | Crea las vistas de consumo para Power BI |

Opción útil mientras desarrollas: `python main.py etl --muestra 50000`.

**¿Todavía no tienes el CSV real?** Puedes verificar que el pipeline funciona con datos
sintéticos que imitan el esquema y su suciedad:

```bash
python herramientas/generar_muestra_prueba.py --filas 20000
# y cambia extraccion.archivo a "muestra_prueba.csv" en config.yaml
```

> Los datos de prueba **no sirven** para el informe final: son inventados. Solo prueban el código.

---

## 4. Arquitectura

```
CSV crudo  ──►  EXTRACT   ──►  TRANSFORM  ──►  LOAD  ──►  SQLite (modelo estrella)
(data/raw)      por bloques    limpieza +      dim + hechos        │
                               enriquecimiento                     ├──► Python: modelos ML
                                                                   └──► Power BI: vistas
```

```
proyecto_vivienda/
├── main.py                  Orquestador (CLI)
├── config.yaml              TODA la parametrización: rutas, reglas de negocio, umbrales
├── data/
│   ├── raw/                 CSV original (no se modifica nunca)
│   └── processed/           Dataset limpio en Parquet
├── db/vivienda.db           Base de datos SQLite
├── sql/
│   ├── 01_schema.sql        DDL del modelo dimensional
│   └── 02_vistas_powerbi.sql  Vistas de consumo
├── src/
│   ├── etl/                 extract.py · transform.py · load.py
│   ├── eda/explorar.py      Exploración
│   ├── modelos/             no_supervisado.py · supervisado.py
│   └── utils/               log.py · auditoria.py
├── herramientas/            Utilidades: generador de datos de prueba y del Ishikawa
├── docs/                    Diagramas de las entregas (Ishikawa)
├── artefactos/              Modelos entrenados (.pkl / .keras)
└── reportes/                figuras/ y tablas/ para el informe
```

---

## 5. El ETL en detalle (Etapa 4)

El corazón del proyecto. Cada paso queda registrado en la tabla `etl_auditoria`, de modo
que se puede demostrar cuántas filas entraron, cuántas salieron y por qué:

| # | Paso | Criterio |
|---|---|---|
| 1 | Tipificación | Fechas, numéricos y texto normalizado; lo inconvertible queda nulo |
| 2 | Filtro de negocio | Solo **venta**, solo **casas y apartamentos**, solo **Colombia** y sin avisos con precio **mensual** (arriendos publicados como venta) |
| 3 | Homologación de moneda | Avisos en USD convertidos a COP con la tasa del config |
| 4 | Tratamiento de nulos | Imputación deducida (área), contextual (baños por ciudad+habitaciones) y etiquetado (zona y barrio). Solo se eliminan filas sin precio o sin área |
| 5 | Duplicados | Filas idénticas + **identificador del aviso** + clave de negocio (mismo inmueble republicado) |
| 5b | **Coherencia (Data Clinic)** | Área cubierta mayor que la total, `dormitorios = 0` (no informado), dormitorios mayores que ambientes y coordenadas fuera de Colombia: se **anulan**, no se adivinan |
| 6 | Enriquecimiento | `precio_m2`, ratios, calendario, `segmento_tamano` y **`dias_publicado`** (rotación) |
| 7 | Rangos de dominio | Descarta lo físicamente imposible (precio 0, casa de 3 m², 40 baños) |
| 8 | Recorte de colas | Percentiles 1 % y 99 % del precio por m² |

**Rotación del inventario:** `dias_publicado` se calcula como la diferencia entre la fecha de
baja y la de publicación. Properati marca los avisos aún vigentes con la fecha centinela
`9999-12-31`; esos casos **no son un dato faltante**, son avisos activos, así que quedan con
`dias_publicado` nulo, `esta_activo = 1` y **no se descartan** en el filtro de rangos. Esta
variable es la que sustenta la causa *"no hay revisión periódica de avisos con mucho tiempo
publicados"* del diagrama de Ishikawa.

**Carga:** la tabla plana se descompone en un **esquema en estrella**
(`hecho_inmueble` + `dim_ubicacion`, `dim_tiempo`, `dim_tipo`, `dim_segmento`), que es
exactamente el modelo que Power BI espera consumir.

---

## 6. Modelado (Etapa 5)

### Aprendizaje NO supervisado — `main.py segmentar`

1. **Isolation Forest** — detecta avisos anómalos que ninguna regla fija habría atrapado
   (combinaciones raras de área, precio y ubicación). Es la última capa del control de
   calidad y esos registros se marcan en `hecho_inmueble.es_anomalo`.
2. **K-Means** — segmenta el mercado sin usar el precio como etiqueta. El número de
   grupos se justifica con **método del codo + coeficiente de silueta**, y los grupos se
   visualizan proyectados con **PCA**.
3. Cada cluster se traduce a lenguaje de negocio en `dim_segmento` (Económico, Estándar,
   Alto, Premium) y **se usa después como variable de entrada del modelo supervisado**.

### Aprendizaje supervisado — `main.py entrenar`

Regresión sobre `log(precio)` — el precio es muy asimétrico y el logaritmo estabiliza la
varianza. Las métricas siempre se reportan en pesos.

| Modelo | Rol |
|---|---|
| Ridge | Línea base interpretable |
| Random Forest | Bagging de árboles |
| Gradient Boosting | Boosting de árboles |
| Red neuronal (Keras) | Continuidad del trabajo previo del curso |

Métricas: **MAE**, **RMSE**, **R²** y **MAPE**, guardadas en `modelo_metricas`.
Se añade **importancia por permutación** para explicar qué mueve realmente el precio.

> **`dias_publicado` se excluye a propósito del modelo de precio.** Solo se conoce cuando el
> aviso ya salió del portal, y el modelo debe sugerir un precio *en el momento de publicar*:
> incluirlo sería usar información del futuro. Esa variable se usa para analizar la rotación
> (vista `v_rotacion`), no para estimar el precio.

---

## 7. Interpretación y Power BI (Etapa 6)

`python main.py vistas` crea las vistas de consumo. En Power BI:

**Obtener datos → ODBC / conector SQLite** apuntando a `db/vivienda.db`.

| Vista | Uso en el dashboard |
|---|---|
| `v_inmuebles` | Tabla de detalle con todas las dimensiones resueltas |
| `v_kpi_ciudad` | Tarjetas y mapa: precio por m² por ciudad |
| `v_evolucion_mensual` | Gráfico de tendencia |
| `v_segmentos` | Filtro y comparativa entre segmentos del K-Means |
| `v_oportunidades` | Avisos publicados >15 % por debajo del valor estimado |
| `v_rotacion` | Días publicado y % de avisos lentos (>180 días) por ciudad y segmento |

---

## 8. Trazabilidad

| Tabla | Contenido |
|---|---|
| `etl_auditoria` | Filas antes/después y motivo de cada paso del ETL |
| `modelo_metricas` | Histórico de desempeño de cada modelo por ejecución |
| `logs/pipeline.log` | Traza completa de cada ejecución |
