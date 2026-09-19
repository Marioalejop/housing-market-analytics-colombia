"""ETAPA 4 - TRANSFORMACION (la T de ETL): el nucleo del proyecto.

Cada funcion resuelve UN problema de calidad de datos y deja constancia en
la auditoria. El orden importa: primero se homologa, luego se filtra por
negocio, luego se limpia y por ultimo se enriquece.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.auditoria import Auditoria
from src.utils.log import obtener_logger

log = obtener_logger("etl.transform")

TEXTO = ["pais", "departamento", "ciudad", "zona", "barrio", "tipo_propiedad", "tipo_operacion",
         "moneda", "periodo_precio"]
NUMERICAS = [
    "precio", "superficie_total", "superficie_cubierta",
    "habitaciones", "dormitorios", "banos", "latitud", "longitud",
]


def tipificar(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte cada columna a su tipo correcto. Lo no convertible queda nulo."""
    df = df.copy()
    for col in ("fecha_publicacion", "fecha_baja"):
        if col in df:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "id_aviso" in df:
        df["id_aviso"] = df["id_aviso"].astype("string").str.strip()
    for col in NUMERICAS:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in TEXTO:
        if col in df:
            df[col] = df[col].astype("string").str.strip().str.title()
    log.info("Tipos homologados (fechas, numericos y texto normalizado).")
    return df


def filtrar_negocio(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Deja solo el universo que responde la pregunta de negocio."""
    t = cfg["transformacion"]

    antes = len(df)
    df = df[df["tipo_operacion"].isin(t["operaciones_validas"])]
    aud.registrar("Filtro: solo operaciones de venta", antes, len(df), str(t["operaciones_validas"]))

    antes = len(df)
    df = df[df["tipo_propiedad"].isin(t["tipos_propiedad_validos"])]
    aud.registrar("Filtro: casas y apartamentos", antes, len(df), str(t["tipos_propiedad_validos"]))

    if "pais" in df.columns:
        antes = len(df)
        df = df[df["pais"].isin(t["paises_validos"])]
        aud.registrar("Filtro: solo Colombia", antes, len(df), str(t["paises_validos"]))

    # Data Clinic: el periodo de precio "Mensual" delata un arriendo publicado
    # como venta. El precio no es comparable con el resto.
    if "periodo_precio" in df.columns:
        antes = len(df)
        df = df[~df["periodo_precio"].isin(t["periodos_precio_excluidos"])]
        aud.registrar("Filtro: ventas con precio mensual", antes, len(df),
                      "periodo_precio en " + str(t["periodos_precio_excluidos"]))
    return df


def homologar_moneda(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Lleva todos los precios a una sola moneda.

    Sin este paso el modelo compara peras con manzanas: un aviso de 300.000 USD
    y otro de 300.000.000 COP se veria como el mismo numero de magnitud distinta.
    """
    t = cfg["transformacion"]
    objetivo, tasa = t["moneda_objetivo"], t["tasa_usd_cop"]
    df = df.copy()

    antes = len(df)
    es_usd = df["moneda"].str.upper() == "USD"
    convertidos = int(es_usd.sum())
    df.loc[es_usd, "precio"] = df.loc[es_usd, "precio"] * tasa
    df.loc[es_usd, "moneda"] = objetivo
    df = df[df["moneda"].str.upper() == objetivo]
    aud.registrar(
        "Homologacion de moneda a " + objetivo,
        antes,
        len(df),
        f"{convertidos:,} avisos en USD convertidos a tasa {tasa:,}",
    )
    return df


def corregir_incoherencias(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Anula los valores imposibles en vez de adivinarlos (reglas del Data Clinic).

    Estas reglas no eliminan filas: dejan el dato en nulo. Si la columna es
    obligatoria, la fila caera despues en el paso de nulos y quedara registrado
    alli; si no lo es, el aviso se conserva sin ese dato.
    """
    df = df.copy()
    n = len(df)

    # 1. El area construida no puede superar al area total: no se sabe cual es
    #    la correcta, asi que se anulan las dos.
    if {"superficie_total", "superficie_cubierta"}.issubset(df.columns):
        incoherente = df["superficie_cubierta"] > df["superficie_total"]
        df.loc[incoherente, ["superficie_total", "superficie_cubierta"]] = np.nan
        aud.registrar("Coherencia: area cubierta > area total", n, n,
                      f"{int(incoherente.sum()):,} areas anuladas")

    # 2. Cero dormitorios significa "no informado", no un inmueble sin alcobas.
    if "dormitorios" in df.columns:
        ceros = df["dormitorios"] == 0
        df.loc[ceros, "dormitorios"] = np.nan
        aud.registrar("Coherencia: dormitorios en cero", n, n,
                      f"{int(ceros.sum()):,} valores pasados a nulo")

        if "habitaciones" in df.columns:
            mayor = df["dormitorios"] > df["habitaciones"]
            df.loc[mayor, "dormitorios"] = np.nan
            aud.registrar("Coherencia: dormitorios > ambientes", n, n,
                          f"{int(mayor.sum()):,} valores anulados")

    # 3. Coordenadas fuera de Colombia: se anulan, pero el aviso se conserva
    #    porque la ciudad sigue siendo valida.
    if {"latitud", "longitud"}.issubset(df.columns):
        caja = cfg["transformacion"]["bbox_colombia"]
        dentro = (df["latitud"].between(*caja["lat"]) & df["longitud"].between(*caja["lon"]))
        fuera = df["latitud"].notna() & ~dentro
        df.loc[fuera, ["latitud", "longitud"]] = np.nan
        aud.registrar("Coherencia: coordenadas fuera de Colombia", n, n,
                      f"{int(fuera.sum()):,} coordenadas anuladas")

    return df


def tratar_nulos(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Imputa lo que se puede deducir y elimina solo lo irrecuperable."""
    t = cfg["transformacion"]
    df = df.copy()

    reporte = (df.isna().mean() * 100).round(2).sort_values(ascending=False)
    log.info("Porcentaje de nulos por columna:\n%s", reporte.to_string())

    # 1. La superficie cubierta se deduce de la total y viceversa
    if {"superficie_total", "superficie_cubierta"}.issubset(df.columns):
        df["superficie_total"] = df["superficie_total"].fillna(df["superficie_cubierta"])
        df["superficie_cubierta"] = df["superficie_cubierta"].fillna(df["superficie_total"])

    # 2. Habitaciones y dormitorios son casi sinonimos en este dataset
    if {"habitaciones", "dormitorios"}.issubset(df.columns):
        df["habitaciones"] = df["habitaciones"].fillna(df["dormitorios"])

    # 3. Banos: imputacion contextual con la mediana de ciudad + habitaciones
    if "banos" in df:
        df["banos"] = df["banos"].fillna(
            df.groupby(["ciudad", "habitaciones"])["banos"].transform("median")
        )
        df["banos"] = df["banos"].fillna(df["banos"].median())

    # 4. Zona y barrio sin dato: no se inventan, se etiquetan
    for col in ("zona", "barrio"):
        if col in df:
            df[col] = df[col].fillna("Sin Dato")

    # 5. Lo obligatorio no se imputa: sin precio o sin area el registro no sirve
    antes = len(df)
    df = df.dropna(subset=t["columnas_obligatorias"])
    aud.registrar(
        "Nulos: eliminacion por campos obligatorios",
        antes,
        len(df),
        "obligatorios=" + ", ".join(t["columnas_obligatorias"]) + "; el resto fue imputado",
    )
    return df


def eliminar_duplicados(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Un mismo inmueble suele publicarse varias veces: sesga el modelo si no se trata."""
    t = cfg["transformacion"]

    antes = len(df)
    df = df.drop_duplicates()
    aud.registrar("Duplicados: filas identicas", antes, len(df))

    # El identificador del aviso detecta el mismo registro exportado dos veces,
    # algo que la comparacion por caracteristicas no distingue de dos inmuebles
    # realmente parecidos.
    if "id_aviso" in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=["id_aviso"], keep="first")
        aud.registrar("Duplicados: por identificador del aviso", antes, len(df), "clave=id_aviso")

    clave = [c for c in t["clave_duplicados"] if c in df.columns]
    antes = len(df)
    df = df.drop_duplicates(subset=clave, keep="first")
    aud.registrar("Duplicados: por clave de negocio", antes, len(df), "clave=" + ", ".join(clave))
    return df


def aplicar_rangos(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Reglas de dominio: descarta lo fisicamente imposible (precio 0, casa de 5 m2, 40 banos)."""
    t = cfg["transformacion"]
    admiten_nulo = set(t.get("rangos_admiten_nulo", []))

    for col, (minimo, maximo) in t["rangos_validos"].items():
        if col not in df.columns:
            continue
        antes = len(df)
        dentro = df[col].between(minimo, maximo)
        # En algunas columnas el nulo es un caso valido, no un dato faltante:
        # dias_publicado es nulo en los avisos que siguen activos.
        nota = ""
        if col in admiten_nulo:
            dentro = dentro | df[col].isna()
            nota = " (se conservan los nulos)"
        df = df[dentro]
        aud.registrar(f"Rango valido: {col}", antes, len(df), f"[{minimo:,} , {maximo:,}]{nota}")
    return df


def recortar_colas(df: pd.DataFrame, cfg: dict, aud: Auditoria) -> pd.DataFrame:
    """Recorte estadistico de los extremos del precio por m2 (outliers residuales)."""
    t = cfg["transformacion"]
    p_inf, p_sup = t["percentil_inferior"], t["percentil_superior"]
    li, ls = df["precio_m2"].quantile([p_inf, p_sup])

    antes = len(df)
    df = df[df["precio_m2"].between(li, ls)]
    aud.registrar(
        "Recorte de colas del precio por m2",
        antes,
        len(df),
        f"limite inferior={li:,.0f} | limite superior={ls:,.0f}",
    )
    return df


def enriquecer(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Variables derivadas: aqui es donde el ETL crea valor analitico."""
    df = df.copy()

    df["precio_m2"] = df["precio"] / df["superficie_total"]
    df["area_por_habitacion"] = df["superficie_total"] / df["habitaciones"].replace(0, np.nan)
    df["ratio_bano_habitacion"] = df["banos"] / df["habitaciones"].replace(0, np.nan)

    if "superficie_cubierta" in df:
        df["pct_cubierta"] = (df["superficie_cubierta"] / df["superficie_total"]).clip(0, 1)

    if "fecha_publicacion" in df:
        f = df["fecha_publicacion"]
        df["anio"] = f.dt.year
        df["mes"] = f.dt.month
        df["trimestre"] = f.dt.quarter
        df["anio_mes"] = f.dt.to_period("M").astype("string")

    # --- Rotacion del inventario ---
    # Es la variable que sustenta la causa "no hay revision periodica de avisos
    # con mucho tiempo publicados" del diagrama de Ishikawa (Etapa 1).
    if {"fecha_publicacion", "fecha_baja"}.issubset(df.columns):
        centinela = cfg["transformacion"].get("anio_centinela_activo", 2900)
        baja = df["fecha_baja"]

        # Los avisos vigentes se marcan con una fecha de baja imposible
        # (Properati usa 9999-12-31): no son un dato faltante, son casos activos.
        activo = baja.isna() | (baja.dt.year >= centinela)
        df["esta_activo"] = activo.astype(int)

        dias = (baja - df["fecha_publicacion"]).dt.days
        df["dias_publicado"] = dias.where(~activo)   # nulo si sigue activo

        cerrados = df["dias_publicado"].notna().sum()
        log.info(
            "Rotacion: %s avisos activos y %s cerrados con duracion calculable "
            "(mediana %.0f dias).",
            f"{int(df['esta_activo'].sum()):,}",
            f"{cerrados:,}",
            df["dias_publicado"].median() if cerrados else float("nan"),
        )

    # Segmento de tamano: categoria util para segmentar el dashboard
    df["segmento_tamano"] = pd.cut(
        df["superficie_total"],
        bins=[0, 60, 100, 160, 250, np.inf],
        labels=["Compacto", "Medio", "Amplio", "Grande", "Premium"],
    ).astype("string")

    log.info("Variables derivadas creadas: precio_m2, ratios, calendario y segmento de tamano.")
    return df


def transformar(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, Auditoria]:
    """Orquesta el pipeline completo de limpieza y devuelve el dataset + la auditoria."""
    aud = Auditoria()
    aud.registrar("Carga inicial (datos crudos)", len(df), len(df), "sin transformar")

    df = tipificar(df)
    df = filtrar_negocio(df, cfg, aud)
    df = homologar_moneda(df, cfg, aud)
    df = corregir_incoherencias(df, cfg, aud)
    df = tratar_nulos(df, cfg, aud)
    df = eliminar_duplicados(df, cfg, aud)
    df = enriquecer(df, cfg)
    df = aplicar_rangos(df, cfg, aud)
    df = recortar_colas(df, cfg, aud)

    df = df.reset_index(drop=True)
    df.insert(0, "id_inmueble", np.arange(1, len(df) + 1))

    log.info("Resultado del pre-procesamiento:\n%s", aud.resumen())
    return df, aud
