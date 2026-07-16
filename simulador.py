"""
simulador.py
-----------------
Penalty Shootout Predictor — Persona 3

Responsabilidades de este módulo (según el documento base):
    1. Simular disparos individuales de un jugador contra la zona
        elegida por el arquero (arbol_arquero.decidir_arquero), usando
       las probabilidades de Persona 2 (grafo_penales.calcular_probabilidades).
    2. Simular tandas completas de penales (5 rondas + muerte súbita)
       entre dos equipos.
    3. Repartir el trabajo de la simulación entre varios procesos con
       multiprocessing.Pool para acelerar el cálculo con n grande.

Funciones públicas que usará Persona 1 (interfaz.py):
    simular_penales(jugador, arquero, n=1000, presion=None, decisivo=False)
    simular_tanda(jugadores_local, jugadores_visita, arquero_local,
                  arquero_visita, n_simulaciones=1000, penales_por_equipo=5,
                  presion="alta")

Modelo de un disparo (independiente de la simulación de una tanda completa):
    1. El tiro puede irse fuera del arco con una probabilidad fija,
       PROB_FALLO, sin que importe lo que haga el arquero.
    2. Si no se va fuera, la zona real del disparo se sortea con las
       probabilidades del jugador (random.choices ponderado).
    3. Modelo binario de atajada: si el arquero se lanzó exactamente a
       la zona real del disparo, probabilidad alta de atajada
       (PROB_ATAJADA_ACIERTO); si se lanzó a cualquier otra zona,
       probabilidad baja de atajada por reflejos/reacción
       (PROB_ATAJADA_FALLO).
"""

import random
import multiprocessing as mp

from grafo_penales import calcular_probabilidades
from arbol_arquero import decidir_arquero

# ---------------------------------------------------------------------------
# Parámetros del modelo de disparo
# ---------------------------------------------------------------------------

# Probabilidad de que el disparo se vaya fuera del arco, independiente de a dónde se lance el arquero.
PROB_FALLO = 0.055

# Probabilidad de que el arquero adivinó exactamente la zona real del disparo y ataja el tiro
PROB_ATAJADA_ACIERTO = 0.60

# Probabilidad de que el arquero se lanzó a otra zona (probabilidad de reacción/reflejos)
PROB_ATAJADA_FALLO = 0.05

#
# Límite de seguridad de rondas de muerte súbita, para no simular un bucle infinito (muuuy improbable)
MAX_RONDAS_MUERTE_SUBITA = 15


def _resultado_disparo(probabilidades_zonas, zona_arquero):
    """
    Sortea el resultado de un disparo individual: si se va fuera, a qué
    zona real apunta y si el arquero (ya lanzado a 'zona_arquero') lo ataja.

    Retorna "gol", "atajada" o "fallado".
    """
    # random() retorna entre 0.0 y 1.0
    if random.random() < PROB_FALLO:
        return "fallado"

    zonas = list(probabilidades_zonas.keys())
    pesos = list(probabilidades_zonas.values())
    # elección aleatoria sesgada de escoger UNA zona
    # usamos [0] porque el retorno de la función es una lista
    zona_real = random.choices(zonas, weights=pesos, k=1)[0]

    prob_atajada = PROB_ATAJADA_ACIERTO if zona_real == zona_arquero else PROB_ATAJADA_FALLO

    # usamos random() para decidir si el arquero ataja o no
    return "atajada" if random.random() < prob_atajada else "gol"


def _repartir_en_lotes(n, n_procesos):
    """Reparte 'n' repeticiones en 'n_procesos' lotes lo más parejos posible."""
    base = n // n_procesos
    resto = n % n_procesos
    lotes = [base + (1 if i < resto else 0) for i in range(n_procesos)]
    return [lote for lote in lotes if lote > 0]

# ---------------------------------------------------------------------------
# 1. Simulación de disparos de un jugador contra un arquero
# ---------------------------------------------------------------------------

# Simula un lote de disparos

def _simular_lote_disparos(args):
    # args = (n_lote, probabilidades_zonas, zona_arquero, semilla)

    n_lote, probabilidades_zonas, zona_arquero, semilla = args
    random.seed(semilla)

    conteos = {"gol": 0, "atajada": 0, "fallado": 0}
    for _ in range(n_lote):
        resultado = _resultado_disparo(probabilidades_zonas, zona_arquero)
        conteos[resultado] += 1

    return conteos


def simular_penales(jugador, arquero, n=1000, presion=None, decisivo=False, df=None):
    """
    Simula 'n' disparos de un jugador contra un arquero, repartiendo el
    trabajo entre varios procesos con multiprocessing.Pool.

    El árbol de decisión (arbol_arquero.decidir_arquero) y el grafo de
    probabilidades (grafo_penales.calcular_probabilidades) se calculan
    UNA sola vez, para fijar la zona a la que se lanza el arquero;
    luego esa zona se usa en las 'n' repeticiones.

    Parámetros:
        jugador (str): nombre (o parte del nombre) del jugador que patea.
        arquero (str): nombre del arquero (solo se usa como etiqueta en
            el resultado; la decisión de a dónde lanzarse depende
            exclusivamente de las probabilidades del jugador).
        n (int): cantidad de disparos a simular.
        presion (str|None): None | "alta" | "baja", igual que en
            grafo_penales.calcular_probabilidades.
        decisivo (bool): si el penal es decisivo, para el árbol de decisión.
        df: opcional, DataFrame ya cargado (para pruebas unitarias).

    Retorna un diccionario:
        {
          "jugador": str,
          "arquero": str,
          "n_simulaciones": int,
          "zona_lanzamiento_arquero": str,
          "confianza_decision_arquero": "alta"|"media"|"baja",
          "recomendacion_arquero": str,
          "ruta_decision_arquero": [str, ...],
          "resultados": {"gol": %, "atajada": %, "fallado": %},
          "conteos": {"gol": int, "atajada": int, "fallado": int},
        }
    """

    # Calculamos las probabilidades para el pateador
    probabilidades = calcular_probabilidades(jugador, presion=presion, df=df)
    # Calculamos la única decisión que va a tomar el arquero
    decision = decidir_arquero(probabilidades, presion=presion, decisivo=decisivo)
    # Guardamos la zona a la que el arquero se va a lanzar
    zona_arquero = decision["zona_lanzamiento"]

    # Definimos cuantos hilos (núcleos lógicos del procesador) se van a utilizar
    n_procesos = min(mp.cpu_count(), max(1, n))
    # Definimos la carga para hilo
    lotes = _repartir_en_lotes(n, n_procesos)

    # Paquete de datos para cada hilo
    tareas = [
        (n_lote, probabilidades["probabilidades"], zona_arquero, random.randint(0, 2**31 - 1))
        for n_lote in lotes
    ]

    with mp.Pool(processes=len(tareas)) as pool:
        resultados_parciales = pool.map(_simular_lote_disparos, tareas)

    conteos = {"gol": 0, "atajada": 0, "fallado": 0}
    for parcial in resultados_parciales:
        for clave in conteos:
            conteos[clave] += parcial[clave]

    resultados_pct = {
        clave: round((valor / n) * 100, 2) for clave, valor in conteos.items()
    }

    return {
        "jugador": probabilidades["jugador"],
        "arquero": arquero,
        "n_simulaciones": n,
        "zona_lanzamiento_arquero": zona_arquero,
        "confianza_decision_arquero": decision["confianza_decision"],
        "recomendacion_arquero": decision["recomendacion"],
        "ruta_decision_arquero": decision["ruta"],
        "resultados": resultados_pct,
        "conteos": conteos,
    }


# ---------------------------------------------------------------------------
# 2. Simulación de una tanda completa entre dos equipos
# ---------------------------------------------------------------------------

def _construir_perfil(jugador, presion, df):
    """
    Precalcula, UNA sola vez por jugador, sus probabilidades por zona y
    la zona a la que se lanzaría el arquero rival en un penal normal y
    en uno decisivo. Así, al repetir miles de tandas, no hace falta
    volver a llamar al grafo ni al árbol de decisión en cada repetición.
    """
    probabilidades = calcular_probabilidades(jugador, presion=presion, df=df)
    zona_normal = decidir_arquero(probabilidades, presion=presion, decisivo=False)["zona_lanzamiento"]
    zona_decisiva = decidir_arquero(probabilidades, presion=presion, decisivo=True)["zona_lanzamiento"]

    return {
        "jugador": probabilidades["jugador"],
        "probabilidades": probabilidades["probabilidades"],
        "zona_normal": zona_normal,
        "zona_decisiva": zona_decisiva,
    }


def _simular_lote_tandas(args):
    """
    Simula un lote de tandas completas. Función de nivel de módulo
    (picklable) para repartirse entre procesos con multiprocessing.Pool.

    args = (n_lote, perfiles_local, perfiles_visita, penales_por_equipo, semilla)
    """
    n_lote, perfiles_local, perfiles_visita, penales_por_equipo, semilla = args
    random.seed(semilla)

    n_local = len(perfiles_local)
    n_visita = len(perfiles_visita)

    conteos = {"gana_local": 0, "gana_visita": 0, "empate": 0}

    for _ in range(n_lote):
        goles_local = 0
        goles_visita = 0
        indice = 0

        # Fase normal: rondas alternadas, reciclando la lista de jugadores.
        for ronda in range(penales_por_equipo):
            decisivo = ronda == penales_por_equipo - 1  # último penal de la ronda normal

            perfil_l = perfiles_local[indice % n_local]
            zona_l = perfil_l["zona_decisiva"] if decisivo else perfil_l["zona_normal"]
            if _resultado_disparo(perfil_l["probabilidades"], zona_l) == "gol":
                goles_local += 1

            perfil_v = perfiles_visita[indice % n_visita]
            zona_v = perfil_v["zona_decisiva"] if decisivo else perfil_v["zona_normal"]
            if _resultado_disparo(perfil_v["probabilidades"], zona_v) == "gol":
                goles_visita += 1

            indice += 1

        # Muerte súbita: 1 vs 1, siempre decisiva, hasta desempatar.
        rondas_extra = 0
        while goles_local == goles_visita and rondas_extra < MAX_RONDAS_MUERTE_SUBITA:
            perfil_l = perfiles_local[indice % n_local]
            if _resultado_disparo(perfil_l["probabilidades"], perfil_l["zona_decisiva"]) == "gol":
                goles_local += 1

            perfil_v = perfiles_visita[indice % n_visita]
            if _resultado_disparo(perfil_v["probabilidades"], perfil_v["zona_decisiva"]) == "gol":
                goles_visita += 1

            indice += 1
            rondas_extra += 1

        if goles_local > goles_visita:
            conteos["gana_local"] += 1
        elif goles_visita > goles_local:
            conteos["gana_visita"] += 1
        else:
            conteos["empate"] += 1

    return conteos


def simular_tanda(jugadores_local, jugadores_visita, arquero_local, arquero_visita,
                   n_simulaciones=1000, penales_por_equipo=5, presion="alta", df=None):
    """
    Simula 'n_simulaciones' tandas completas de penales entre dos
    equipos, repartiendo el trabajo entre varios procesos con
    multiprocessing.Pool.

    Cada tanda tiene 'penales_por_equipo' rondas alternadas (local,
    visita, local, visita, ...) reciclando la lista de jugadores en
    orden cíclico si hace falta; si hay empate al terminar esas rondas,
    continúa en muerte súbita 1 vs 1 hasta desempatar.

    El perfil de cada jugador (probabilidades por zona + zona del
    arquero rival, en penal normal y en decisivo) se precalcula UNA
    sola vez antes de simular las repeticiones.

    Parámetros:
        jugadores_local (list[str]): pateadores del equipo local, en
            orden de tanda.
        jugadores_visita (list[str]): pateadores del equipo visitante.
        arquero_local (str): arquero del equipo local (ataja los
            penales de jugadores_visita).
        arquero_visita (str): arquero del equipo visitante (ataja los
            penales de jugadores_local).
        n_simulaciones (int): cantidad de tandas a simular.
        penales_por_equipo (int): rondas de la fase normal (5 por defecto).
        presion (str|None): presión aplicada al calcular probabilidades,
            igual que en grafo_penales.calcular_probabilidades
            ("alta" por defecto, típico de una tanda de penales).
        df: opcional, DataFrame ya cargado (para pruebas unitarias).

    Retorna un diccionario:
        {
          "equipo_local": {"jugadores": [...], "arquero_rival": str, "gana_pct": float},
          "equipo_visitante": {"jugadores": [...], "arquero_rival": str, "gana_pct": float},
          "empate_pct": float,
          "n_simulaciones": int,
        }
    """
    if not jugadores_local or not jugadores_visita:
        raise ValueError("Ambas listas de jugadores deben tener al menos un elemento.")

    perfiles_local = [_construir_perfil(j, presion, df) for j in jugadores_local]
    perfiles_visita = [_construir_perfil(j, presion, df) for j in jugadores_visita]

    n_procesos = min(mp.cpu_count(), max(1, n_simulaciones))
    lotes = _repartir_en_lotes(n_simulaciones, n_procesos)

    tareas = [
        (n_lote, perfiles_local, perfiles_visita, penales_por_equipo, random.randint(0, 2**31 - 1))
        for n_lote in lotes
    ]

    with mp.Pool(processes=len(tareas)) as pool:
        resultados_parciales = pool.map(_simular_lote_tandas, tareas)

    conteos = {"gana_local": 0, "gana_visita": 0, "empate": 0}
    for parcial in resultados_parciales:
        for clave in conteos:
            conteos[clave] += parcial[clave]

    return {
        "equipo_local": {
            "jugadores": [p["jugador"] for p in perfiles_local],
            "arquero_rival": arquero_visita,
            "gana_pct": round((conteos["gana_local"] / n_simulaciones) * 100, 2),
        },
        "equipo_visitante": {
            "jugadores": [p["jugador"] for p in perfiles_visita],
            "arquero_rival": arquero_local,
            "gana_pct": round((conteos["gana_visita"] / n_simulaciones) * 100, 2),
        },
        "empate_pct": round((conteos["empate"] / n_simulaciones) * 100, 2),
        "n_simulaciones": n_simulaciones,
    }
