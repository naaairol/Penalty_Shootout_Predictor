"""
grafo_penales.py
-----------------
Penalty Shootout Predictor — Persona 2: Datos + Grafo

Responsabilidades de este módulo (según el documento base):
    1. Lectura del CSV de penales históricos (jugadores).
    2. Construcción del grafo jugador -> zonas (networkx), donde cada
       arista representa "hacia dónde suele patear un jugador" y su
       peso es el número/porcentaje de penales hacia esa zona.
    3. Cálculo de probabilidades por zona (conteo de frecuencias).
    4. Filtros (presión alta) para que la predicción sea más "inteligente".

Funciones públicas que usará Persona 1 (interfaz.py):
    cargar_penales(ruta)
    calcular_probabilidades(jugador, presion=None)

Persona 3 (arbol_arquero.py / simulador.py) puede además usar:
    construir_grafo(jugador)
    listar_jugadores()
"""

import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Configuración de las 9 zonas del arco (igual para todo el equipo)
# ---------------------------------------------------------------------------

ZONAS = ["AI", "AC", "AD", "MI", "MC", "MD", "BI", "BC", "BD"]

# Mapa zona -> columna del CSV
COLUMNA_ZONA = {
    "AI": "porcentaje_ai", "AC": "porcentaje_ac", "AD": "porcentaje_ad",
    "MI": "porcentaje_mi", "MC": "porcentaje_mc", "MD": "porcentaje_md",
    "BI": "porcentaje_bi", "BC": "porcentaje_bc", "BD": "porcentaje_bd",
}

# Nombres legibles (útiles para Persona 1, panel de predicción)
NOMBRE_ZONA = {
    "AI": "Alto Izquierda", "AC": "Alto Centro",  "AD": "Alto Derecha",
    "MI": "Medio Izquierda", "MC": "Medio Centro", "MD": "Medio Derecha",
    "BI": "Bajo Izquierda", "BC": "Bajo Centro",  "BD": "Bajo Derecha",
}

# Ruta por defecto, coincide con la estructura del documento base:
#   penalty_predictor/datos/penales_jugadores.csv
RUTA_POR_DEFECTO = os.path.join("datos", "penales_jugadores.csv")

# DataFrame cacheado en memoria después de cargar_penales()
_df_jugadores = None


# ---------------------------------------------------------------------------
# 1. Carga de datos
# ---------------------------------------------------------------------------

def cargar_penales(ruta=RUTA_POR_DEFECTO):
    """
    Lee el CSV histórico de penales de jugadores y lo deja disponible
    para el resto de funciones del módulo.

    Parámetros:
        ruta (str): ruta al CSV (por defecto datos/penales_jugadores.csv)

    Retorna:
        pandas.DataFrame con los penales cargados.
    """
    global _df_jugadores

    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo de penales: {ruta}")

    # utf-8-sig porque el CSV original trae BOM al inicio
    df = pd.read_csv(ruta, encoding="utf-8-sig")

    columnas_requeridas = ["jugador", "zona_favorita", "segunda_zona",
                            "total_penales", "rendimiento_presion"] + list(COLUMNA_ZONA.values())
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {faltantes}")

    _df_jugadores = df
    return df


def listar_jugadores():
    """Devuelve la lista de nombres de jugadores disponibles (para combos de la UI)."""
    _validar_datos_cargados()
    return sorted(_df_jugadores["jugador"].unique().tolist())


def _validar_datos_cargados():
    if _df_jugadores is None:
        raise RuntimeError(
            "No hay datos cargados. Llama primero a cargar_penales(ruta)."
        )


def _buscar_jugador(df, jugador):
    """Busca un jugador por coincidencia (insensible a mayúsculas)."""
    coincidencias = df[df["jugador"].str.lower().str.contains(jugador.lower().strip())]
    if coincidencias.empty:
        disponibles = ", ".join(df["jugador"].unique())
        raise ValueError(
            f"No se encontró al jugador '{jugador}'.\nDisponibles: {disponibles}"
        )
    return coincidencias.iloc[0]


# ---------------------------------------------------------------------------
# 2. Grafo jugador -> zonas
# ---------------------------------------------------------------------------

def construir_grafo(jugador, df=None):
    """
    Construye un grafo dirigido: jugador -> 9 zonas del arco.

    El peso de cada arista (weight) es el número estimado de penales
    pateados hacia esa zona (porcentaje histórico aplicado sobre el
    total de penales del jugador), tal como lo pide el documento base:

        Messi -> BI = 8 penales
        Messi -> BD = 5 penales
        Messi -> MC = 2 penales
        Messi -> AI = 1 penal

    Retorna:
        networkx.DiGraph
    """
    df = df if df is not None else _df_jugadores
    _validar_datos_cargados() if df is None else None

    fila = _buscar_jugador(df, jugador)
    total = max(int(fila["total_penales"]), 1)

    G = nx.DiGraph()
    G.add_node(fila["jugador"], tipo="jugador")

    for zona, columna in COLUMNA_ZONA.items():
        porcentaje = float(fila[columna])
        peso = round((porcentaje / 100) * total, 2)
        G.add_node(zona, tipo="zona", nombre=NOMBRE_ZONA[zona])
        G.add_edge(fila["jugador"], zona, weight=peso, porcentaje=porcentaje)

    return G


def graficar_grafo(jugador, guardar_como=None):
    """
    Dibuja el grafo jugador -> zonas con matplotlib (grosor de línea
    proporcional al peso). Útil para el panel de la interfaz o para
    verificación visual.

    Si 'guardar_como' se especifica, guarda la imagen en esa ruta en
    lugar de mostrarla en pantalla.
    """
    G = construir_grafo(jugador)
    pos = nx.spring_layout(G, seed=42)

    pesos = [G[u][v]["weight"] for u, v in G.edges()]
    max_peso = max(pesos) if pesos else 1

    plt.figure(figsize=(6, 6))
    nx.draw_networkx_nodes(G, pos, node_color="#dddddd", node_size=1200)
    nx.draw_networkx_labels(G, pos, font_size=9)
    nx.draw_networkx_edges(
        G, pos,
        width=[1 + 4 * (p / max_peso) for p in pesos],
        arrowsize=15,
    )
    etiquetas = {(u, v): d["weight"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=etiquetas, font_size=8)

    plt.title(f"Grafo de penales: {jugador}")
    plt.axis("off")

    if guardar_como:
        plt.savefig(guardar_como, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


# ---------------------------------------------------------------------------
# 3. Cálculo de probabilidades (con filtro de presión)
# ---------------------------------------------------------------------------

def calcular_probabilidades(jugador, presion=None, df=None):
    """
    Calcula la probabilidad de disparo hacia cada una de las 9 zonas
    para un jugador, aplicando (opcionalmente) un filtro de presión.

    Parámetros:
        jugador (str): nombre (o parte del nombre) del jugador.
        presion (str|None): None | "alta" | "baja".
            - None:  usa el porcentaje histórico general de cada zona.
            - "alta": refuerza la zona favorita / segunda zona usando
              'rendimiento_presion' como factor (jugadores que rinden
              bien bajo presión concentran más su disparo en su zona
              de confianza; los que rinden mal se vuelven más erráticos).
            - "baja": distribución más pareja entre zonas (menos
              predecible al no haber presión decisiva).
        df: opcional, para pruebas unitarias. Si no se pasa usa el
            DataFrame cargado con cargar_penales().

    Retorna un diccionario:
        {
          "jugador": str,
          "probabilidades": {zona: porcentaje, ...},   # suman 100
          "zona_favorita": str,
          "probabilidad_favorita": float,
          "segunda_zona": str,
          "probabilidad_segunda": float,
          "confianza": "alta" | "media" | "baja",
          "presion_aplicada": None | "alta" | "baja",
        }
    """
    df = df if df is not None else _df_jugadores
    _validar_datos_cargados() if df is None else None

    fila = _buscar_jugador(df, jugador)

    # Probabilidades base = porcentajes históricos por zona
    probs = {zona: float(fila[col]) for zona, col in COLUMNA_ZONA.items()}

    zona_fav = str(fila["zona_favorita"]).upper()
    zona_seg = str(fila["segunda_zona"]).upper()
    rendimiento = float(fila["rendimiento_presion"])  # 0-100

    presion_normalizada = presion.lower().strip() if presion else None

    if presion_normalizada == "alta":
        # Factor entre 1.0 y 2.0 según qué tan bien rinde bajo presión
        factor = 1 + (rendimiento / 100)
        for zona in probs:
            if zona == zona_fav:
                probs[zona] *= factor
            elif zona == zona_seg:
                probs[zona] *= (1 + (factor - 1) / 2)

    elif presion_normalizada == "baja":
        # Sin presión decisiva, el disparo tiende a ser más parejo
        promedio = 100 / len(ZONAS)
        for zona in probs:
            probs[zona] = probs[zona] * 0.7 + promedio * 0.3

    # Normalizar para que la suma sea 100%
    total = sum(probs.values())
    if total > 0:
        probs = {z: round((v / total) * 100, 2) for z, v in probs.items()}

    zonas_ordenadas = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    zona_top, prob_top = zonas_ordenadas[0]
    zona_segunda, prob_segunda = zonas_ordenadas[1]

    if prob_top >= 40:
        confianza = "alta"
    elif prob_top >= 25:
        confianza = "media"
    else:
        confianza = "baja"

    return {
        "jugador": fila["jugador"],
        "probabilidades": probs,
        "zona_favorita": zona_top,
        "probabilidad_favorita": prob_top,
        "segunda_zona": zona_segunda,
        "probabilidad_segunda": prob_segunda,
        "confianza": confianza,
        "presion_aplicada": presion_normalizada,
    }
