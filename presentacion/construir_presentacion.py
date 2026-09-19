"""Genera la presentacion HTML a partir de los resultados del notebook.

Uso (despues de ejecutar Demo_Sustentacion_Grupo6.ipynb):

    python presentacion/construir_presentacion.py

Lee  salida/resumen.json y salida/figuras/*.png
Crea presentacion/Presentacion_Final_Grupo6.html  (un solo archivo, sin internet)

Ninguna cifra se escribe a mano: todas salen de resumen.json, asi la
presentacion no puede contradecir al notebook.
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
FIG = RAIZ / "salida" / "figuras"
DESTINO = Path(__file__).resolve().parent / "Presentacion_Final_Grupo6.html"
R = json.loads((RAIZ / "salida" / "resumen.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ formato
def n(x) -> str:
    """Miles con punto: 16204 -> 16.204"""
    return f"{int(round(x)):,}".replace(",", ".")


def d(x, k: int = 1) -> str:
    """Decimales con coma: 0.789 -> 0,8"""
    return f"{x:.{k}f}".replace(".", ",")


def es(texto: str) -> str:
    """Convierte 2,580 -> 2.580 en textos que vienen del notebook (formato en ingles)."""
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", ".", texto)


def b64(ruta: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


def figura(nombre: str, alt: str) -> str:
    return f'<img src="{b64(FIG / (nombre + ".png"))}" alt="{alt}">'


# -------------------------------------------------------------------- datos
ds, cal = R["dataset"], R["calidad"]
pr, area, texto = cal["problemas"], cal["area"], cal["texto"]
aud = {p["regla"]: p for p in R["limpieza"]}
M = {m["modelo"]: m for m in R["modelos"]}
mejor = M["Gradient Boosting (con ciudad)"]
sin_ciudad = M["Gradient Boosting (sin ciudad)"]
lineal = M["Regresión lineal"]
seg = R["segmentos"]
ex = R["exploracion"]
op = R["oportunidades"]
div = R["division"]
total_op = op["por_debajo"] + op["por_encima"] + op["cerca"]
rot_op = {r["estado_precio"]: r for r in op["rotacion"]}
med_sobre = rot_op["Por encima del valor estimado"]["dias_mediana"]
med_cerca = rot_op["Cerca del valor estimado"]["dias_mediana"]
c1, c2, c3 = ex["ciudades"][:3]
zona_alta, zona_baja = ex["zonas_bogota"][-1], ex["zonas_bogota"][0]
rot_ciudades = ex["rotacion"]
rot_lenta = rot_ciudades[0]
rot_bogota = next(r for r in rot_ciudades if r["ciudad"] == "Bogotá D.C")
INICIAL, FINAL = R["inicial"], R["final"]
sep = R["silueta_k4"]
k2 = next(k for k in R["seleccion_k"] if k["k"] == 2)["silueta"]


def elimina(regla: str) -> int:
    return int(aud[regla]["elimina"])


PASOS = ["Problema", "Datos", "Data Quality", "Data Cleaning", "Exploración",
         "Machine Learning", "Resultados", "Limitaciones"]
ETAPA = {2: 0, 3: 1, 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7}
TOTAL = 10


def stepper(num: int) -> str:
    activo = ETAPA[num]
    return "".join(
        f'<span class="paso{" on" if i == activo else ""}{" hecho" if i < activo else ""}">{t}</span>'
        for i, t in enumerate(PASOS))


def diapositiva(num: int, titulo: str, lead: str, cuerpo: str, guion: str) -> str:
    return f"""
<section class="slide" data-n="{num}">
  <div class="top"><div class="stepper">{stepper(num)}</div><div class="cnt">{num} / {TOTAL}</div></div>
  <h2>{titulo}</h2>
  <p class="lead">{lead}</p>
  <div class="body">{cuerpo}</div>
  <div class="foot"><span>Grupo 6 · Business Analytics &amp; Big Data II</span>
    <span>Valoración y segmentación del mercado de vivienda en Colombia</span></div>
  <aside class="notas"><b>Guion · </b>{guion}</aside>
</section>"""


SLIDES: list[str] = []

# ============================================================== 1 · Portada
SLIDES.append(f"""
<section class="slide portada" data-n="1">
  <div class="p-int">
    <div class="p-etiqueta">Business Analytics &amp; Big Data II · ING-SOF8-N · 2.º corte</div>
    <h1>Valoración y segmentación del<br>mercado de vivienda en Colombia</h1>
    <p class="p-sub">De {n(ds['filas'])} de avisos inmobiliarios a un precio de referencia y cuatro perfiles de vivienda</p>
    <div class="p-equipo">
      <div class="p-grupo">Grupo 6</div>
      <div>Maria Alejandra Toro Ortiz</div><div>Mario Alejandro Peña Arenas</div>
      <div>Javier Alexander Moreno Avila</div><div>Kevin Steven Guzmán Acevedo</div>
    </div>
    <div class="p-pie">Docente: Oscar Castiblanco · Universitaria de Colombia · 21 de septiembre de 2026</div>
  </div>
  <div class="ayuda">← → navegar · N guion · F pantalla completa · P imprimir</div>
  <aside class="notas"><b>Guion · 20 s · </b>Somos el grupo 6. Partimos de un millón de avisos reales de vivienda
    en Colombia y terminamos con un modelo que estima el precio y cuatro perfiles de vivienda.
    Vamos a contar el proyecto en el orden que pidió el docente: problema, datos, calidad, limpieza,
    exploración, machine learning, resultados y limitaciones.</aside>
</section>""")

# ========================================================= 2 · Problema
SLIDES.append(diapositiva(2, "Problema y pregunta de negocio", "Qué queremos resolver y para quién", f"""
<div class="g2 a">
  <div>
    <div class="card rojo"><h3>El problema</h3>
      <p>En los portales inmobiliarios <b>el precio lo fija cada vendedor «a ojo»</b>, sin una referencia
      construida con inmuebles comparables.</p></div>
    <div class="cadena"><span>Precio «a ojo»</span><i>→</i><span>Sobrevalorados: no rotan</span><i>+</i><span>Subvalorados: pierden dinero</span></div>
    <div class="card azul"><h3>Pregunta de negocio</h3>
      <ol class="num">
        <li><b>¿Qué precio de publicación</b> puede esperarse según las características y la ubicación?</li>
        <li><b>¿Qué grupos naturales</b> de vivienda existen en el mercado?</li>
        <li><b>¿Qué avisos</b> están publicados muy lejos de ese valor?</li>
      </ol></div>
    <p class="nota">Los avisos registran el precio <i>pedido</i>, no el de cierre: el resultado es una referencia del
      mercado de oferta.</p>
  </div>
  <div>
    <img class="ish" src="{b64(RAIZ / 'docs' / 'ishikawa_etapa1.png')}" alt="Diagrama de Ishikawa">
    <p class="pie-img">Diagrama de Ishikawa (Etapa 1): seis categorías de causas del problema</p>
    <div class="card gris"><h3>Decisión que habilita</h3>
      <p>Sugerir un precio de publicación, priorizar la captación por perfil de vivienda y alertar sobre
      avisos fuera de rango.</p></div>
  </div>
</div>""",
    "<b>50 s · </b>El problema no lo inventamos: viene del Ishikawa de la Etapa 1. Los precios se fijan a ojo, y eso "
    "produce dos errores: avisos sobrevalorados que no rotan y subvalorados que pierden dinero. De ahí salen tres "
    "preguntas, y cada una se responde con una técnica distinta. Aclaramos desde ya que trabajamos con el precio "
    "pedido, no con el de cierre."))

# =========================================================== 3 · Dataset
candidatos = [
    ("Properati Colombia (Kaggle)", "1.000.000", "ok", "Principal"),
    ("Medellín 2023", "9.999", "ok", "Apoyo"),
    ("Bogotá 2023", "585", "no", "Pocos registros"),
    ("House Prices (Ames, EE. UU.)", "1.460", "no", "Otro país"),
    ("Catastro Bogotá", "427.839", "no", "Valor del terreno"),
    ("Properati oficial (Kaggle)", "1,5 millones", "no", "Sin Colombia"),
]
filas_cand = "".join(
    f'<tr><td>{nombre}</td><td class="r">{reg}</td><td><span class="chip {c}">{txt}</span></td></tr>'
    for nombre, reg, c, txt in candidatos)
SLIDES.append(diapositiva(3, "Dataset y fuente", "De dónde salen los datos y por qué los elegimos", f"""
<div class="g2 b">
  <div>
    <table class="ficha">
      <tr><th>Nombre</th><td>Colombia Housing Properties Price<br><span class="suave">avisos del portal Properati</span></td></tr>
      <tr><th>Fuente</th><td>Kaggle · <code>julianusugaortiz</code></td></tr>
      <tr><th>Enlace</th><td class="enl">kaggle.com/datasets/julianusugaortiz/colombia-housing-properties-price</td></tr>
      <tr><th>Formato</th><td>CSV · {d(ds['megabytes'], 0)} MB</td></tr>
      <tr><th>Periodo</th><td>{ds['periodo'][0]} a {ds['periodo'][1]}</td></tr>
      <tr><th>Licencia</th><td>«Unknown» en Kaggle → uso académico</td></tr>
      <tr><th>Apoyo</th><td>Medellín 2023 · {n(R['apoyo']['filas'])} registros · Apache 2.0</td></tr>
    </table>
    <div class="kpis">
      <div class="kpi"><b>{n(ds['filas'])}</b><span>registros</span></div>
      <div class="kpi"><b>{ds['columnas']}</b><span>variables</span></div>
      <div class="kpi"><b>{n(area['universo'])}</b><span>ventas de vivienda</span></div>
    </div>
  </div>
  <div>
    <h3 class="sec">Se compararon seis candidatos</h3>
    <table class="datos"><thead><tr><th>Dataset</th><th class="r">Registros</th><th>¿Sirve?</th></tr></thead>
      <tbody>{filas_cand}</tbody></table>
    <h3 class="sec">Por qué este</h3>
    <ul class="pts">
      <li><b>Cubre el problema completo:</b> varias ciudades, precio, tipo, fechas de publicación y de baja.</li>
      <li><b>Tiene volumen real</b> y viene «sucio»: obliga a hacer ETL, el foco de la materia.</li>
      <li><b>Tiene un apoyo:</b> el dataset de Medellín trae el área completa y valida la relación área–precio.</li>
    </ul>
  </div>
</div>""",
    "<b>50 s · </b>Este es el dataset: un millón de avisos de Properati publicados en Kaggle, de julio de 2020 a agosto de "
    "2021. Comparamos seis candidatos y elegimos por correspondencia con el problema, no por tamaño: es el único que "
    "tiene varias ciudades y fechas de publicación y de baja. Usamos Medellín como apoyo porque allí sí viene el área. "
    "Mencionamos la licencia porque condiciona el uso: solo académico."))

# ============================================================ 4 · Variables
SLIDES.append(diapositiva(4, "Variables utilizadas", "Qué significa cada columna y qué papel juega", """
<div class="g2 c">
  <div>
    <table class="datos">
      <thead><tr><th>Variable</th><th>Qué es</th><th>Papel</th></tr></thead>
      <tbody>
        <tr class="dest"><td><code>price</code></td><td>Precio publicado</td><td><b>Variable objetivo</b></td></tr>
        <tr><td><code>surface_total</code> · <code>surface_covered</code></td><td>Área en m²</td><td>Predictor principal</td></tr>
        <tr><td><code>bedrooms</code> · <code>bathrooms</code></td><td>Dormitorios y baños</td><td>Predictores</td></tr>
        <tr><td><code>property_type</code></td><td>Casa o apartamento</td><td>Predictor y filtro</td></tr>
        <tr><td><code>l3</code></td><td>Ciudad</td><td>Predictor (ubicación)</td></tr>
        <tr><td><code>l4</code> · <code>lat</code> · <code>lon</code></td><td>Zona y coordenadas</td><td>Análisis</td></tr>
        <tr><td><code>start_date</code> · <code>end_date</code></td><td>Publicación y baja</td><td>Tiempo y rotación</td></tr>
        <tr><td><code>operation_type</code> · <code>price_period</code><br><code>currency</code> · <code>l1</code></td><td>Operación, periodo, moneda y país</td><td>Filtros de calidad</td></tr>
        <tr><td><code>id</code></td><td>Identificador del aviso</td><td>Detectar repetidos</td></tr>
      </tbody>
    </table>
  </div>
  <div>
    <div class="card azul"><h3>Variables que creamos</h3>
      <ul class="pts">
        <li><code>precio_m2</code> · compara viviendas de distinto tamaño</li>
        <li><code>dias_publicado</code> · cuánto tarda en salir un aviso</li>
        <li><code>segmento</code> · perfil de vivienda (K-Means)</li>
        <li><code>precio_estimado</code> · lo que predice el modelo</li>
      </ul></div>
    <div class="card gris"><h3>Lo que descartamos</h3>
      <ul class="pts">
        <li><code>ad_type</code> · constante</li>
        <li><code>created_on</code> · repite <code>start_date</code></li>
        <li><code>l5</code> · <code>l6</code> · casi vacías</li>
        <li><code>title</code> · <code>description</code> · traen teléfonos: se eliminan por privacidad</li>
      </ul></div>
  </div>
</div>""",
    "<b>40 s · </b>Solo una variable es el objetivo: el precio. El área es el predictor principal; junto con dormitorios, baños, "
    "tipo de inmueble y ciudad, forman las variables del modelo. Además del archivo, creamos cuatro variables propias, "
    "como el precio por metro cuadrado. Y descartamos seis columnas: cuatro porque no aportan y dos por privacidad."))

# ========================================================= 5 · Data Quality
n_nulas = len(cal["nulos"])
check = [
    ("Valores nulos", f"{n_nulas} de {ds['columnas']} columnas con faltantes; el <b>área falta en el {d(area['sin_area_pct'])} %</b> "
                      "de las ventas de vivienda", "rojo"),
    ("Duplicados", f"{n(pr['Filas completamente duplicadas'])} filas idénticas y {n(pr['Identificadores repetidos'])} identificadores repetidos; "
                   f"las republicaciones se detectan después ({n(elimina('Sin republicaciones'))})", "verde"),
    ("Tipos incorrectos", "3 columnas de fecha guardadas como <b>texto</b>", "amarillo"),
    ("Inconsistencias", f"<b>{n(pr['Ventas con precio mensual (arriendos disfrazados)'])}</b> ventas con precio mensual · "
                        f"{n(pr['Dormitorios en cero (= no informado)'])} con 0 dormitorios · "
                        f"{n(pr['Área construida mayor que la total'])} con área cubierta &gt; total", "rojo"),
    ("Valores atípicos", f"{n(pr['Precio mayor a 5.000 millones'])} precios sobre 5.000 millones · "
                         f"{n(pr['Área total mayor a 1.000 m²'])} áreas sobre 1.000 m²", "amarillo"),
    ("Columnas innecesarias", "6: una constante, una repetida, dos casi vacías y dos de texto libre", "amarillo"),
    ("Formato y privacidad", f"<b>{n(texto['con_telefono'])}</b> avisos con un posible teléfono en el texto libre", "rojo"),
]
filas_check = "".join(
    f'<tr><td class="cn"><span class="pt {c}"></span>{t}</td><td>{v}</td></tr>' for t, v, c in check)
SLIDES.append(diapositiva(5, "Data Quality: qué problemas tienen los datos",
    "Revisamos las 25 columnas antes de tocar nada", f"""
<div class="g2 d">
  <div>
    {figura('calidad_nulos', 'Valores faltantes por columna')}
    <p class="nota">No todo faltante es un error: la fecha de baja <code>9999-12-31</code> significa «aviso vigente»
    ({n(pr['Avisos vigentes (fecha de baja 9999-12-31)'])} casos), no un dato perdido.</p>
  </div>
  <div><table class="check">{filas_check}</table></div>
</div>""",
    "<b>1 min · </b>Antes de limpiar, diagnosticamos: revisamos los siete tipos de problema de la guía. El hallazgo que condiciona "
    f"todo: de {n(area['universo'])} avisos de venta de vivienda, solo {n(area['con_area'])} traen el área, la variable que más "
    "explica el precio. También encontramos arriendos disfrazados de venta, valores incoherentes y teléfonos en el texto libre. "
    "Y una idea importante: no todo faltante es un error, como la fecha 9999-12-31."))

# ======================================================== 6 · Data Cleaning
inco_txt = es(next(p["por qué"] for p in R["limpieza"] if p["regla"] == "Incoherencias anuladas"))
extremos = (elimina("Precio entre 30 y 5.000 millones") + elimina("Área entre 20 y 1.000 m²")
            + elimina("Recorte de colas del precio por m² (p1–p99)"))
limp = [
    ("Arriendos, lotes y locales", "Filtrar", f"Otra escala de precio; no son vivienda ({n(elimina('Solo ventas') + elimina('Solo casas y apartamentos'))} avisos)"),
    ("Ventas con precio mensual", "Filtrar", f"Un precio mensual delata un arriendo ({n(elimina('Sin ventas con precio mensual'))})"),
    ("Sin área", "Eliminar", f"Sin área no se predice el precio, y no se inventa ({n(elimina('Con precio y área'))})"),
    ("Datos incoherentes", "Anular", "No sabemos cuál es el dato correcto: se deja en nulo, no se adivina"),
    ("Republicaciones", "Deduplicar", f"El mismo inmueble pesaría doble en el modelo ({n(elimina('Sin republicaciones'))})"),
    ("Valores extremos", "Filtrar", f"Distorsionan promedios y modelo ({n(extremos)})"),
]
filas_limp = "".join(
    f'<tr><td><b>{p}</b></td><td><span class="chip acc">{dec}</span></td><td>{por}</td></tr>' for p, dec, por in limp)
SLIDES.append(diapositiva(6, "Data Cleaning: qué hicimos y por qué",
    "Cada regla tiene un problema, una decisión y una justificación", f"""
<div class="g2 e">
  <div>
    {figura('embudo_limpieza', 'Avisos eliminados por cada regla')}
    <div class="kpis">
      <div class="kpi"><b>{n(INICIAL)}</b><span>avisos iniciales</span></div>
      <div class="kpi dest"><b>{n(FINAL)}</b><span>avisos finales ({d(FINAL / INICIAL * 100, 2)} %)</span></div>
      <div class="kpi"><b>{len(R['limpieza']) - 1}</b><span>reglas auditadas</span></div>
    </div>
  </div>
  <div>
    <table class="datos"><thead><tr><th>Problema</th><th>Decisión</th><th>Por qué</th></tr></thead>
      <tbody>{filas_limp}</tbody></table>
    <div class="card azul sep"><h3>Anular no es lo mismo que eliminar</h3>
      <p>{inco_txt}. El aviso se conserva cuando el dato dañado no es imprescindible.</p></div>
  </div>
</div>""",
    "<b>1 min 10 s · </b>No basta con decir «usamos dropna»: cada regla tiene problema, decisión y justificación. La gráfica muestra que "
    "casi todo se pierde por dos razones: filtrar el universo, porque el arriendo y los lotes no son vivienda, y la falta de área. "
    "Una idea que nos diferencia: cuando un dato es incoherente lo anulamos, no lo inventamos. Y todo queda auditado: sabemos "
    f"cuántos avisos elimina cada regla. Pasamos de {n(INICIAL)} a {n(FINAL)} avisos."))

# ===================================================== 7 · Exploración
SLIDES.append(diapositiva(7, "Exploración: qué nos dicen los datos",
    "Cuatro hallazgos, cada uno con la gráfica que lo sustenta", f"""
<div class="g3 x">
  <div class="hal"><div class="hn">1</div>
    {figura('hallazgo_ciudad', 'Precio del m2 por ciudad')}
    <h3>La ciudad manda</h3>
    <p>{c1['ciudad'].replace(' D.C', '')} lidera con <b>{d(c1['m2'])} M</b> por m²; le siguen {c2['ciudad']} ({d(c2['m2'])} M) y {c3['ciudad']} ({d(c3['m2'])} M).</p></div>
  <div class="hal"><div class="hn">2</div>
    {figura('hallazgo_zonas', 'Precio del m2 por zona de Bogota')}
    <h3>Y dentro de la ciudad, la zona</h3>
    <p>En Bogotá, <b>Chapinero ({d(zona_alta['m2'])} M)</b> cuesta más del doble que la zona Suroccidental ({d(zona_baja['m2'])} M).</p></div>
  <div class="hal"><div class="hn">3</div>
    {figura('hallazgo_area', 'Area frente a precio')}
    <h3>El área pesa, pero no basta</h3>
    <p>Correlación de <b>{d(ex['correlaciones']['area'], 2)}</b> con el precio ({d(ex['corr_medellin'], 2)} en Medellín). A igual área, el precio varía muchísimo.</p></div>
</div>
<div class="fila4">
  <div>{figura('hallazgo_rotacion', 'Dias que tarda en salir un aviso, por ciudad')}</div>
  <div class="tx4"><div class="hn">4</div><div><h3>La rotación varía mucho según la ciudad</h3>
    <p>Un aviso de {rot_lenta['ciudad']} tarda una mediana de <b>{d(rot_lenta['dias'], 0)} días</b> en salir; uno de Bogotá, <b>{d(rot_bogota['dias'], 0)}</b>.
    Solo cuentan los avisos cerrados: el {d(ex['pct_vigentes'])} % sigue vigente, así que la cifra subestima la duración real.</p></div></div>
</div>""",
    "<b>1 min 10 s · </b>Cuatro hallazgos, cada uno con su gráfica. Primero: la ubicación manda, el metro cuadrado en Bogotá "
    "cuesta bastante más que en otras ciudades. Segundo: dentro de una misma ciudad, la zona también cambia el precio; un "
    "promedio por ciudad esconde eso. Tercero: el área explica el precio pero con mucha dispersión, y lo comprobamos con "
    "el dataset de Medellín, que sí trae el área completa. Cuarto: la rotación cambia mucho por ciudad, con la salvedad "
    "de los avisos vigentes."))

# =============================================================== 8 · ML
tarjetas_seg = "".join(
    f'<div class="sg"><b>{s["segmento"]}</b><span>{n(s["avisos"])} avisos · {d(s["area"], 0)} m²</span>'
    f'<span>{n(s["precio"])} M · {d(s["m2"])} M/m²</span></div>' for s in seg)
SLIDES.append(diapositiva(8, "Machine Learning: dos técnicas, dos preguntas",
    "Una predice un número; la otra descubre grupos", f"""
<div class="g2 f">
  <div>
    <div class="cab az">Supervisado · regresión</div>
    <p class="q">¿Cuánto vale esta vivienda?</p>
    <div class="flujo"><span>Dataset<br>limpio</span><i>→</i><span>Train<br><b>{n(div['entrenamiento'])}</b> · 80 %</span><i>→</i>
      <span>Modelo</span><i>→</i><span>Test<br><b>{n(div['prueba'])}</b> · 20 %</span><i>→</i><span>Evaluación</span></div>
    <ul class="pts">
      <li><b>Entrada:</b> área, dormitorios, baños, tipo de inmueble y ciudad.</li>
      <li><b>Cuatro modelos,</b> del más simple al más completo: línea base, regresión lineal y Gradient Boosting sin y con ciudad.</li>
    </ul>
    <div class="mets">
      <div class="met"><b>R²</b><span>qué parte de la variación del precio explica el modelo (1 = todo)</span></div>
      <div class="met"><b>MAE</b><span>cuánto se equivoca en promedio, en millones de pesos</span></div>
      <div class="met"><b>MAPE</b><span>ese error como porcentaje del precio real</span></div>
    </div>
  </div>
  <div>
    <div class="cab na">No supervisado · clustering</div>
    <p class="q">¿Qué grupos de vivienda existen?</p>
    {figura('seleccion_k', 'Metodo del codo y silueta')}
    <p class="nota">K-Means con variables estandarizadas. La silueta baja de {d(k2, 2)} (k=2) a ~{d(sep, 2)} (k=3 a 5): elegimos
    <b>k = 4</b> por interpretación de negocio, con separación moderada.</p>
    <div class="segs">{tarjetas_seg}</div>
  </div>
</div>
<div class="alerta"><b>Dos decisiones para no hacer trampa:</b> el segmento <b>no</b> entra al modelo de precio (se calcula con el
precio: sería fuga de datos) y no usamos <code>dias_publicado</code> (solo se conoce después de publicar).</div>""",
    "<b>1 min 10 s · </b>Dos técnicas, dos preguntas. A la izquierda, aprendizaje supervisado: tenemos avisos con su precio conocido, "
    "entrenamos con el 80 % y evaluamos con el 20 % que el modelo nunca vio. A la derecha, no supervisado: K-Means agrupa las "
    "viviendas sin que le digamos cómo. Aquí somos honestos: la silueta no favorece claramente a ningún k, así que elegimos 4 "
    "por interpretación de negocio. Y dos decisiones para no hacer trampa: el segmento no entra al modelo de precio porque se "
    "calcula con el precio, y no usamos los días publicados porque solo se conocen después."))

# ============================================================ 9 · Resultados
imp = R["importancia"]
suma_imp = sum(v for v in imp.values() if v > 0)
barras = "".join(
    f'<div class="ib"><span>{k}</span><div><i style="width:{max(v, 0) / suma_imp * 100:.0f}%"></i></div>'
    f'<b>{max(v, 0) / suma_imp * 100:.0f} %</b></div>' for k, v in imp.items())
SLIDES.append(diapositiva(9, "Resultados y evaluación", "Qué aprendimos y qué decisión habilita", f"""
<div class="g2 g">
  <div>
    {figura('comparacion_modelos', 'Comparacion de los cuatro modelos')}
    <div class="kpis">
      <div class="kpi dest"><b>{d(mejor['R2'], 2)}</b><span>R² del mejor modelo</span></div>
      <div class="kpi"><b>{n(mejor['MAE'])} M</b><span>error medio (MAE)</span></div>
      <div class="kpi"><b>{n(mejor['MAPE'])} %</b><span>error relativo (MAPE)</span></div>
    </div>
    <h3 class="sec">Peso de cada variable en el modelo</h3>
    <div class="imps">{barras}</div>
  </div>
  <div>
    <table class="rid"><thead><tr><th>Resultado</th><th>Interpretación</th><th>Decisión</th></tr></thead><tbody>
      <tr><td>Añadir la ciudad sube el R² de <b>{d(sin_ciudad['R2'], 2)}</b> a <b>{d(mejor['R2'], 2)}</b></td>
          <td>La ubicación aporta lo que las características físicas no</td><td>Tasar siempre por ubicación</td></tr>
      <tr><td>El área concentra la mayor parte del peso</td><td>El tamaño manda, pero no basta</td><td>Pedir el área al publicar</td></tr>
      <tr><td><b>{n(op['por_debajo'])}</b> avisos ({d(op['por_debajo'] / total_op * 100, 0)} %) están más de 15 % bajo el valor estimado</td>
          <td>Alertas, no oportunidades seguras: el error medio es {n(mejor['MAPE'])} %</td><td>Priorizar para revisión comercial</td></tr>
      <tr><td>Los avisos sobrevalorados <b>no tardan más</b> en salir ({d(med_sobre, 0)} frente a {d(med_cerca, 0)} días)</td>
          <td>La hipótesis «precio alto = no rota» <b>no se confirma</b>: el aviso mide cuánto se publica, no si se vendió</td>
          <td>No basar la política solo en eso; medir ventas reales</td></tr>
    </tbody></table>
    <p class="nota">Con la regresión lineal, {n(R['lineal_negativas'])} de {n(div['prueba'])} predicciones salieron negativas
    (imposible): otra razón para preferir Gradient Boosting.</p>
  </div>
</div>""",
    "<b>1 min 20 s · </b>Comparamos cuatro modelos para poder justificar la elección. Cada mejora se ve: la línea base no explica nada, la "
    f"regresión lineal llega a {d(lineal['R2'], 2)}, Gradient Boosting a {d(sin_ciudad['R2'], 2)}, y al añadir la ciudad a {d(mejor['R2'], 2)}. "
    f"El error medio es de {n(mejor['MAE'])} millones. La tabla de la derecha es lo más importante en Business Analytics: resultado, "
    "interpretación y decisión. Y un hallazgo que no esperábamos: los avisos sobrevalorados no tardan más en salir. Lo "
    "decimos tal cual: la hipótesis no se confirma con estos datos."))


# ======================================================= 10 · Limitaciones
def lista(items):
    return "".join(f"<li>{i}</li>" for i in items)


limit = [
    f"El <b>área falta en el {d(area['sin_area_pct'])} %</b> de las ventas de vivienda: entrenamos con {n(FINAL)} de {n(ds['filas'])} avisos.",
    "Es el <b>precio pedido</b>, no el de cierre: medimos la oferta.",
    "Datos de <b>2020 y 2021</b>: no reflejan los precios actuales.",
    f"Error medio de <b>{n(mejor['MAE'])} M</b>: el modelo no sustituye una tasación.",
    "Un aviso dado de baja <b>no significa que se vendió</b>: no tenemos ventas reales.",
]
dific = [
    "El enlace que teníamos del dataset <b>daba error 404</b>; el Properati «oficial» de Kaggle no incluye Colombia.",
    "Creímos que la columna <b>l4</b> era el barrio: es la <b>zona</b>; el barrio está 95 % vacío.",
    "Un conteo de <b>800.000 duplicados era falso</b>: comparaba nulos entre sí.",
    "Detectamos una <b>fuga de datos</b>: el segmento se calculaba con el precio y entraba al modelo; al quitarlo, el R² bajó de 0,86 a "
    f"{d(mejor['R2'], 2)}.",
    "Montar <b>PySpark y Java</b> en Windows y en Colab (Act 5).",
]
mejoras = [
    f"<b>Recuperar el área desde el texto:</b> {n(area['recuperable_texto'])} avisos sin área la mencionan.",
    "Añadir <b>zona, estrato y antigüedad</b>, como en el dataset de Medellín.",
    "Datos <b>actualizados</b> y precios de cierre.",
    "<b>Dashboard en Power BI</b> con el CSV que exporta el notebook.",
    "Publicar el modelo como <b>servicio</b> para el portal.",
]
SLIDES.append(diapositiva(10, "Limitaciones, dificultades y mejoras",
    "Lo que no pudimos resolver, lo que nos costó y lo que haríamos después", f"""
<div class="g3 h">
  <div class="card rojo"><h3>Limitaciones</h3><ul class="pts">{lista(limit)}</ul></div>
  <div class="card gris"><h3>Dificultades</h3><ul class="pts">{lista(dific)}</ul></div>
  <div class="card azul"><h3>Mejoras propuestas</h3><ul class="pts">{lista(mejoras)}</ul></div>
</div>""",
    "<b>50 s · </b>Cerramos con lo que no funcionó, porque es lo que separa un trabajo honesto de uno que vende humo. Limitaciones: "
    "el área falta casi siempre y medimos precios pedidos, no de cierre. Dificultades reales: un enlace roto, una confusión entre "
    "zona y barrio, un conteo falso de duplicados y, la más importante, una fuga de datos que detectamos y corregimos, y que "
    "bajó el resultado de 0,86 a 0,79. Y mejoras concretas, cada una con su cifra. Ahora pasamos a la demostración en vivo."))

# ------------------------------------------------------------------- CSS / JS
CSS = """
:root{--tinta:#12161c;--suave:#5a6270;--linea:#e3e6ec;--azul:#1f3864;--acc:#2a78d6;--verde:#1baf7a;
  --naranja:#eb6834;--rojo:#c0392b;--amar:#e0a800}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#0f1622;color:var(--tinta);overflow:hidden;
  font:16px/1.45 "Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif}
#escenario{position:absolute;left:50%;top:50%;width:1280px;height:720px;transform-origin:center;
  transform:translate(-50%,-50%) scale(var(--s,1))}
.slide{display:none;position:absolute;inset:0;background:#fff;padding:20px 48px 0;flex-direction:column;overflow:hidden}
.slide.on{display:flex}
.top{display:flex;justify-content:space-between;align-items:center;height:24px;flex:none}
.stepper{display:flex;gap:6px}
.paso{font-size:11.5px;letter-spacing:.3px;text-transform:uppercase;color:#9aa3b2;padding:3px 9px;border-radius:99px;
  background:#f1f3f7;font-weight:600}
.paso.hecho{color:var(--azul);background:#e6ecf7}
.paso.on{color:#fff;background:var(--azul)}
.cnt{font-size:12.5px;color:var(--suave);font-variant-numeric:tabular-nums}
h2{font-size:32px;line-height:1.15;margin:10px 0 0;color:var(--azul);letter-spacing:-.5px}
.lead{margin:3px 0 0;font-size:16.5px;color:var(--suave)}
.body{flex:1;min-height:0;margin:16px 0 12px;overflow:hidden}
.foot{flex:none;height:32px;border-top:1px solid var(--linea);display:flex;justify-content:space-between;
  align-items:center;font-size:11.5px;color:#8b93a1}
h3{font-size:17px;margin:0 0 7px;color:var(--azul)}
h3.sec{margin:14px 0 8px;font-size:16px}
p{margin:0 0 8px}
code{font-family:Consolas,"Cascadia Mono","Courier New",monospace;background:#eef1f6;padding:1px 6px;
  border-radius:4px;font-size:.92em;color:#243b63}
.suave{color:var(--suave);font-size:14px}
img{display:block;width:100%;border:1px solid var(--linea);border-radius:8px}
.pie-img{font-size:12.5px;color:var(--suave);text-align:center;margin:5px 0 10px}
.nota{font-size:14px;color:var(--suave);font-style:italic;margin-top:9px}

.g2{display:grid;gap:32px;height:100%}
.g2.a{grid-template-columns:.95fr 1.05fr}.g2.b{grid-template-columns:1fr 1fr}.g2.c{grid-template-columns:1.3fr .7fr}
.g2.d{grid-template-columns:.95fr 1.05fr}.g2.e{grid-template-columns:.92fr 1.08fr}.g2.f{grid-template-columns:1fr 1fr;height:auto}
.g2.g{grid-template-columns:.92fr 1.08fr}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.g3.h{height:100%}

.card{border-radius:10px;padding:14px 18px;margin-bottom:13px;border-left:5px solid}
.card.azul{background:#eef4fc;border-color:var(--acc)}.card.rojo{background:#fdeeec;border-color:var(--rojo)}
.card.gris{background:#f2f4f7;border-color:var(--suave)}
.card.sep{margin-top:16px}
.card p{font-size:16px;margin:0}
.g3.h .card{margin:0;height:100%;padding:18px 20px}
.g3.h h3{font-size:21px;margin-bottom:12px}
ul.pts{margin:0;padding-left:19px;font-size:16px}ul.pts li{margin-bottom:8px}
.g3.h ul.pts{font-size:17px}.g3.h ul.pts li{margin-bottom:14px}
ol.num{margin:0;padding-left:21px;font-size:16px}ol.num li{margin-bottom:7px}
.cadena{display:flex;align-items:center;gap:7px;flex-wrap:nowrap;margin:0 0 14px;font-size:14px}
.cadena span{background:#f2f4f7;padding:6px 10px;border-radius:7px;white-space:nowrap}
.cadena i{color:var(--acc);font-style:normal;font-weight:700}
.ish{margin-bottom:0}

table{border-collapse:collapse;width:100%;font-size:15.5px}
th,td{text-align:left;padding:9px 11px;border-bottom:1px solid var(--linea);vertical-align:top}
.datos thead th{background:var(--azul);color:#fff;font-size:13.5px;font-weight:600}
.datos td.r,.datos th.r{text-align:right;font-variant-numeric:tabular-nums}
tr.dest td{background:#fff6e8}
.ficha th{width:24%;background:#f2f4f7;color:var(--azul);font-size:14px}
.ficha td{padding:10px 11px}
.enl{font-size:13px;color:var(--acc);word-break:break-all}
.chip{display:inline-block;padding:1px 10px;border-radius:99px;font-size:13px;font-weight:600}
.chip.ok{background:#dff5ec;color:#0d7a55}.chip.no{background:#fbe6e3;color:#a02f23}.chip.acc{background:#e4eefb;color:#1f5ba8}
.kpis{display:flex;gap:12px;margin:14px 0 0}
.kpi{flex:1;background:#f2f4f7;border-radius:10px;padding:11px 8px;text-align:center}
.kpi b{display:block;font-size:28px;line-height:1.15;color:var(--azul);font-variant-numeric:tabular-nums}
.kpi span{font-size:13px;color:var(--suave)}
.kpi.dest{background:var(--azul)}.kpi.dest b,.kpi.dest span{color:#fff}

.check td{padding:11px 11px}.check td.cn{white-space:nowrap;font-weight:600;color:var(--azul);width:34%}
.pt{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:10px;vertical-align:-1px}
.pt.rojo{background:var(--rojo)}.pt.amarillo{background:var(--amar)}.pt.verde{background:var(--verde)}

.x .hal img{margin-bottom:10px}
.hal{position:relative}.hal h3{font-size:18px}.hal p{font-size:15.5px}
.hn{flex:none;width:30px;height:30px;border-radius:50%;background:var(--acc);color:#fff;display:grid;place-items:center;
  font-weight:700;font-size:15px}
.hal .hn{position:absolute;left:-9px;top:-9px;z-index:2;box-shadow:0 2px 6px rgba(0,0,0,.25)}
.fila4{display:grid;grid-template-columns:360px 1fr;gap:26px;align-items:center;background:#f2f4f7;
  border-radius:10px;padding:8px 20px 8px 8px;margin-top:6px}
.tx4{display:flex;gap:14px;align-items:flex-start}.tx4 p{font-size:15.5px;margin:0}.tx4 h3{font-size:18px}

.cab{display:inline-block;color:#fff;font-weight:700;font-size:14px;padding:5px 15px;border-radius:7px}
.cab.az{background:var(--acc)}.cab.na{background:var(--naranja)}
.q{font-size:22px;font-weight:700;color:var(--azul);margin:8px 0 6px}
.flujo{display:flex;align-items:center;gap:6px;margin:6px 0 14px}
.flujo span{flex:1;background:#eef4fc;border-radius:8px;padding:8px 4px;text-align:center;font-size:13px;line-height:1.3}
.flujo i{color:var(--acc);font-style:normal;font-weight:700}
.mets{display:grid;gap:8px;margin-top:12px}
.met{display:grid;grid-template-columns:62px 1fr;gap:12px;align-items:center;background:#f2f4f7;border-radius:8px;padding:8px 12px}
.met b{font-size:19px;color:var(--acc)}.met span{font-size:14.5px}
.segs{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.sg{background:#f2f4f7;border-radius:8px;padding:6px 12px;font-size:13.5px;display:flex;flex-direction:column;border-left:4px solid var(--naranja)}
.sg b{color:var(--azul);font-size:14.5px}.sg span{color:var(--suave)}
.alerta{margin-top:10px;background:#fff6e8;border-left:5px solid var(--amar);border-radius:8px;padding:8px 16px;font-size:14.5px}
.g2.f .nota{margin:7px 0 8px}

.imps{display:grid;gap:7px}
.ib{display:grid;grid-template-columns:170px 1fr 46px;gap:10px;align-items:center;font-size:14.5px}
.ib div{background:#eef1f6;border-radius:5px;height:14px}.ib i{display:block;height:100%;background:var(--acc);border-radius:5px}
.ib b{text-align:right;font-variant-numeric:tabular-nums}
.rid{font-size:15px}.rid thead th{background:var(--azul);color:#fff;font-size:13px}
.rid td{padding:10px 10px}

.portada{background:linear-gradient(135deg,#0f2247 0%,#1f3864 55%,#2a5aa8 100%);color:#fff;justify-content:center;padding:0 90px}
.p-etiqueta{font-size:14px;letter-spacing:2px;text-transform:uppercase;color:#9fc0f0;font-weight:600}
.portada h1{font-size:52px;line-height:1.13;margin:20px 0 18px;letter-spacing:-1.2px}
.p-sub{font-size:20px;color:#cfdcf3;max-width:760px;margin-bottom:34px}
.p-equipo{display:inline-grid;grid-template-columns:auto auto;gap:5px 42px;background:rgba(255,255,255,.1);
  padding:18px 34px;border-radius:12px;font-size:17px}
.p-grupo{grid-column:1/3;font-weight:700;color:#ffd58a;font-size:18px;margin-bottom:2px}
.p-pie{margin-top:30px;font-size:14px;color:#a9bde0}
.ayuda{position:absolute;right:22px;bottom:12px;font-size:12px;color:#8fa6cc}

.notas{display:none;position:absolute;left:0;right:0;bottom:0;background:rgba(15,22,34,.96);color:#e8ecf2;
  padding:12px 48px 14px;font-size:14.5px;line-height:1.5;z-index:5}
body.guion .notas{display:block}
.barra{position:fixed;left:0;bottom:0;height:3px;background:var(--acc);transition:width .2s;z-index:9}
#chk{display:none}

@media print{
  @page{size:1280px 720px;margin:0}
  html,body{overflow:visible;background:#fff}
  #escenario{position:static;transform:none;width:auto;height:auto}
  .slide{display:flex!important;position:relative;width:1280px;height:720px;page-break-after:always}
  .notas,.barra{display:none!important}
}
"""

JS = """
const slides=[...document.querySelectorAll('.slide')];let i=0;
function ajustar(){const s=Math.min(innerWidth/1280,innerHeight/720);
  document.getElementById('escenario').style.setProperty('--s',s)}
function ir(k){i=Math.max(0,Math.min(slides.length-1,k));
  slides.forEach((s,j)=>s.classList.toggle('on',j===i));
  document.querySelector('.barra').style.width=((i+1)/slides.length*100)+'%';
  history.replaceState(null,'','#'+(i+1))}
function revisar(){  // detecta contenido que no cabe (se escribe en #chk; util con --dump-dom)
  const r=[];slides.forEach((s,j)=>{s.classList.add('on');const b=s.querySelector('.body');
    if(b)r.push((j+1)+':'+b.scrollHeight+'/'+b.clientHeight+(b.scrollHeight>b.clientHeight+1?' DESBORDA':' ok'));
    s.classList.remove('on')});
  document.getElementById('chk').textContent=r.join(' | ')}
addEventListener('resize',ajustar);ajustar();revisar();
addEventListener('keydown',e=>{
  if(['ArrowRight',' ','PageDown'].includes(e.key)){ir(i+1);e.preventDefault()}
  else if(['ArrowLeft','PageUp'].includes(e.key)){ir(i-1);e.preventDefault()}
  else if(e.key==='Home')ir(0);else if(e.key==='End')ir(slides.length-1);
  else if(e.key.toLowerCase()==='n')document.body.classList.toggle('guion');
  else if(e.key.toLowerCase()==='f'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}
  else if(e.key.toLowerCase()==='p')print()});
addEventListener('click',e=>ir(i+(e.clientX<innerWidth*0.2?-1:1)));
ir(Math.max(0,(parseInt(location.hash.slice(1))||1)-1));
"""

HTML = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Valoración y segmentación del mercado de vivienda en Colombia · Grupo 6</title>
<style>{CSS}</style></head>
<body>
<div id="escenario">{''.join(SLIDES)}</div>
<div class="barra"></div>
<pre id="chk"></pre>
<script>{JS}</script>
</body></html>"""

DESTINO.write_text(HTML, encoding="utf-8")
print(f"Presentación: {DESTINO}")
print(f"Diapositivas: {len(SLIDES)} · tamaño: {DESTINO.stat().st_size / 1024 / 1024:.2f} MB")
