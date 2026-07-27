"""
simulador.py
-----------------
Penalty Shootout Predictor — Persona 3

Este módulo integra:
    1. Probabilidades históricas calculadas por el grafo.
    2. Condiciones del partido: clima, cancha, ambiente, ruido, fase,
       presión y penal decisivo.
    3. Árbol de decisión del arquero.
    4. Simulaciones Monte Carlo de penales individuales distribuidas con multiprocessing.Pool.

Las condiciones son reglas heurísticas del modelo del proyecto. Por ejemplo,
la lluvia aumenta el riesgo de fallo y refuerza ligeramente los tiros bajos.
"""

from __future__ import annotations

import multiprocessing as mp
import random

from arbol_arquero import decidir_arquero
from grafo_penales import calcular_probabilidades


# ---------------------------------------------------------------------------
# Parámetros base del modelo
# ---------------------------------------------------------------------------

PROB_FALLO = 0.055
PROB_ATAJADA_ACIERTO = 0.60
PROB_ATAJADA_FALLO = 0.05
ZONAS_BAJAS = ("BI", "BC", "BD")
ZONAS_CENTRALES = ("AC", "MC", "BC")


def _normalizar_texto(valor) -> str:
    return str(valor or "").strip().lower()


def _limitar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


# ---------------------------------------------------------------------------
# Condiciones del partido
# ---------------------------------------------------------------------------

def calcular_efectos_condiciones(
    clima="Normal",
    cancha="Seca",
    ambiente="Neutral",
    ruido="Bajo",
    fase="Octavos",
    presion=None,
    decisivo=False,
):
    """
    Convierte las condiciones seleccionadas en ajustes del modelo.

    Los bonos de fallo, arquero y pateador se expresan en puntos
    porcentuales. Los sesgos bajo y central son factores relativos.
    """
    efectos = {
        "miss_bonus": 0.0,
        "keeper_bonus": 0.0,
        "player_bonus": 0.0,
        "center_bias": 0.0,
        "low_bias": 0.0,
        "summary": [],
    }

    clima_n = _normalizar_texto(clima)
    cancha_n = _normalizar_texto(cancha)
    ambiente_n = _normalizar_texto(ambiente)
    ruido_n = _normalizar_texto(ruido)
    fase_n = _normalizar_texto(fase)
    presion_n = _normalizar_texto(presion)

    if clima_n == "lluvia":
        efectos["miss_bonus"] += 4.0
        efectos["low_bias"] += 0.08
        efectos["summary"].append(
            "lluvia: aumenta el riesgo de fallo y favorece tiros bajos"
        )
    elif clima_n == "calor intenso":
        efectos["miss_bonus"] += 1.5
        efectos["summary"].append(
            "calor intenso: ligera pérdida de precisión"
        )
    elif clima_n in {"frío intenso"}:
        efectos["miss_bonus"] += 2.0
        efectos["summary"].append(
            "frío intenso: menor precisión"
        )

    if cancha_n == "mojada":
        efectos["miss_bonus"] += 3.0
        efectos["low_bias"] += 0.10
        efectos["summary"].append(
            "cancha mojada: balón más rápido y mayor tendencia baja"
        )
    elif cancha_n in {"pesada / deteriorada"}:
        efectos["miss_bonus"] += 4.0
        efectos["center_bias"] += 0.08
        efectos["summary"].append(
            "cancha pesada: ejecución más conservadora"
        )

    if ambiente_n == "público a favor del pateador":
        efectos["player_bonus"] += 3.0
        efectos["summary"].append(
            "público favorable al pateador"
        )
    elif ambiente_n == "público a favor del arquero":
        efectos["keeper_bonus"] += 3.0
        efectos["miss_bonus"] += 1.0
        efectos["summary"].append(
            "público favorable al arquero"
        )

    if ruido_n == "medio":
        efectos["miss_bonus"] += 1.0
        efectos["summary"].append("ruido medio")
    elif ruido_n == "alto":
        efectos["miss_bonus"] += 2.5
        efectos["keeper_bonus"] += 1.0
        efectos["summary"].append("ruido alto: mayor tensión")

    # La fase es un ajuste heurístico moderado del proyecto.
    if fase_n == "semifinal":
        efectos["miss_bonus"] += 1.0
        efectos["summary"].append("semifinal: tensión adicional")
    elif fase_n == "final":
        efectos["miss_bonus"] += 2.0
        efectos["keeper_bonus"] += 0.5
        efectos["summary"].append("final: máxima tensión competitiva")

    if presion_n == "alta":
        efectos["miss_bonus"] += 4.0
        efectos["keeper_bonus"] += 2.0
        efectos["summary"].append("presión alta")

    if decisivo:
        efectos["miss_bonus"] += 3.0
        efectos["keeper_bonus"] += 2.0
        efectos["summary"].append("penal decisivo")

    return efectos


def ajustar_probabilidades_condiciones(probabilidades, efectos):
    """
    Ajusta la distribución por zonas y la normaliza para que sume 100 %.
    """
    ajustadas = {
        zona: max(0.01, float(valor))
        for zona, valor in probabilidades.items()
    }

    if efectos.get("low_bias", 0.0):
        for zona in ZONAS_BAJAS:
            if zona in ajustadas:
                ajustadas[zona] *= 1.0 + efectos["low_bias"]

    if efectos.get("center_bias", 0.0):
        for zona in ZONAS_CENTRALES:
            if zona in ajustadas:
                ajustadas[zona] *= 1.0 + efectos["center_bias"]

    total = sum(ajustadas.values()) or 1.0
    return {
        zona: round(valor * 100.0 / total, 4)
        for zona, valor in ajustadas.items()
    }


def reconstruir_resultado_probabilidades(resultado_base, probabilidades_ajustadas):
    """
    Actualiza zona favorita, segunda zona y confianza después de aplicar
    las condiciones. Esto evita que el árbol use datos antiguos.
    """
    ordenadas = sorted(
        probabilidades_ajustadas.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    zona_favorita, prob_favorita = ordenadas[0]
    segunda_zona, prob_segunda = ordenadas[1]

    if prob_favorita >= 40:
        confianza = "alta"
    elif prob_favorita >= 25:
        confianza = "media"
    else:
        confianza = "baja"

    resultado = dict(resultado_base)
    resultado.update({
        "probabilidades": probabilidades_ajustadas,
        "zona_favorita": zona_favorita,
        "probabilidad_favorita": round(prob_favorita, 2),
        "segunda_zona": segunda_zona,
        "probabilidad_segunda": round(prob_segunda, 2),
        "confianza": confianza,
    })
    return resultado


def calcular_parametros_disparo(efectos):
    """
    Convierte los efectos en probabilidades efectivas del disparo.
    """
    prob_fallo = PROB_FALLO + (
        efectos.get("miss_bonus", 0.0)
        - efectos.get("player_bonus", 0.0)
    ) / 100.0

    prob_atajada_acierto = (
        PROB_ATAJADA_ACIERTO
        + efectos.get("keeper_bonus", 0.0) / 100.0
    )

    # Cuando no coincide la zona, el bono del arquero tiene menor peso.
    prob_atajada_fallo = (
        PROB_ATAJADA_FALLO
        + efectos.get("keeper_bonus", 0.0) / 200.0
    )

    return {
        "prob_fallo": _limitar(prob_fallo, 0.01, 0.45),
        "prob_atajada_acierto": _limitar(
            prob_atajada_acierto, 0.05, 0.90
        ),
        "prob_atajada_fallo": _limitar(
            prob_atajada_fallo, 0.01, 0.35
        ),
    }


# ---------------------------------------------------------------------------
# Modelo de un disparo
# ---------------------------------------------------------------------------

def _resolver_disparo(
    probabilidades_zonas,
    zona_arquero,
    prob_fallo=PROB_FALLO,
    prob_atajada_acierto=PROB_ATAJADA_ACIERTO,
    prob_atajada_fallo=PROB_ATAJADA_FALLO,
):
    """Retorna una tupla: (resultado, zona_real_o_None)."""
    if random.random() < prob_fallo:
        return "fallado", None

    zonas = list(probabilidades_zonas.keys())
    pesos = [max(0.0, float(v)) for v in probabilidades_zonas.values()]

    if not zonas:
        raise ValueError("No existen zonas para simular el disparo.")

    if sum(pesos) <= 0:
        zona_real = random.choice(zonas)
    else:
        zona_real = random.choices(zonas, weights=pesos, k=1)[0]

    prob_atajada = (
        prob_atajada_acierto
        if zona_real == zona_arquero
        else prob_atajada_fallo
    )

    resultado = (
        "atajada"
        if random.random() < prob_atajada
        else "gol"
    )
    return resultado, zona_real



def _repartir_en_lotes(n, n_procesos):
    """Reparte n repeticiones en lotes lo más parejos posible."""
    base = n // n_procesos
    resto = n % n_procesos
    lotes = [base + (1 if i < resto else 0) for i in range(n_procesos)]
    return [lote for lote in lotes if lote > 0]


# ---------------------------------------------------------------------------
# 1. Simulación de disparos contra un arquero
# ---------------------------------------------------------------------------

def _simular_lote_disparos(args):
    (
        n_lote,
        probabilidades_zonas,
        zona_arquero,
        prob_fallo,
        prob_atajada_acierto,
        prob_atajada_fallo,
        semilla,
    ) = args

    random.seed(semilla)

    conteos = {"gol": 0, "atajada": 0, "fallado": 0}
    conteos_zonas = {zona: 0 for zona in probabilidades_zonas}

    for _ in range(n_lote):
        resultado, zona_real = _resolver_disparo(
            probabilidades_zonas,
            zona_arquero,
            prob_fallo,
            prob_atajada_acierto,
            prob_atajada_fallo,
        )
        conteos[resultado] += 1

        if zona_real is not None:
            conteos_zonas[zona_real] += 1

    return {
        "conteos": conteos,
        "conteos_zonas": conteos_zonas,
    }


def simular_penales(
    jugador,
    arquero,
    n=1000,
    presion=None,
    decisivo=False,
    clima="Normal",
    cancha="Seca",
    ambiente="Neutral",
    ruido="Bajo",
    fase="Octavos",
    df=None,
):
    """
    Simula n disparos aplicando los datos históricos, las condiciones
    del partido, el árbol de decisión y multiprocessing.
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError("La cantidad de simulaciones debe ser un entero mayor que cero.")

    probabilidades_base = calcular_probabilidades(
        jugador,
        presion=presion,
        df=df,
    )

    efectos = calcular_efectos_condiciones(
        clima=clima,
        cancha=cancha,
        ambiente=ambiente,
        ruido=ruido,
        fase=fase,
        presion=presion,
        decisivo=decisivo,
    )

    probabilidades_zonas = ajustar_probabilidades_condiciones(
        probabilidades_base["probabilidades"],
        efectos,
    )

    probabilidades = reconstruir_resultado_probabilidades(
        probabilidades_base,
        probabilidades_zonas,
    )

    decision = decidir_arquero(
        probabilidades,
        presion=presion,
        decisivo=decisivo,
    )
    zona_arquero = decision["zona_lanzamiento"]

    parametros = calcular_parametros_disparo(efectos)

    n_procesos = min(mp.cpu_count(), n)
    lotes = _repartir_en_lotes(n, n_procesos)

    tareas = [
        (
            n_lote,
            probabilidades_zonas,
            zona_arquero,
            parametros["prob_fallo"],
            parametros["prob_atajada_acierto"],
            parametros["prob_atajada_fallo"],
            random.randint(0, 2**31 - 1),
        )
        for n_lote in lotes
    ]

    with mp.Pool(processes=len(tareas)) as pool:
        resultados_parciales = pool.map(
            _simular_lote_disparos,
            tareas,
        )

    conteos = {"gol": 0, "atajada": 0, "fallado": 0}
    conteos_zonas = {zona: 0 for zona in probabilidades_zonas}

    for parcial in resultados_parciales:
        for clave in conteos:
            conteos[clave] += parcial["conteos"][clave]

        for zona in conteos_zonas:
            conteos_zonas[zona] += parcial["conteos_zonas"][zona]

    resultados_pct = {
        clave: round(valor * 100.0 / n, 2)
        for clave, valor in conteos.items()
    }

    tiros_con_zona = sum(conteos_zonas.values())
    if tiros_con_zona > 0:
        probabilidades_simuladas = {
            zona: round(conteo * 100.0 / tiros_con_zona, 2)
            for zona, conteo in conteos_zonas.items()
        }
    else:
        probabilidades_simuladas = {
            zona: round(valor, 2)
            for zona, valor in probabilidades_zonas.items()
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
        "conteos_zonas": conteos_zonas,
        "probabilidades_base": probabilidades_base["probabilidades"],
        "probabilidades_ajustadas": probabilidades_zonas,
        "probabilidades_simuladas": probabilidades_simuladas,
        "efectos_condiciones": efectos,
        "parametros_modelo": {
            "prob_fallo": round(parametros["prob_fallo"] * 100, 2),
            "prob_atajada_si_coincide": round(
                parametros["prob_atajada_acierto"] * 100, 2
            ),
            "prob_atajada_si_no_coincide": round(
                parametros["prob_atajada_fallo"] * 100, 2
            ),
        },
    }
