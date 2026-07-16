"""
arbol_arquero.py
-----------------
Penalty Shootout Predictor — Persona 3: Árbol de decisión del arquero

Responsabilidades de este módulo (según el documento base):
    1. Tomar el diccionario de probabilidades que entrega Persona 2
       (grafo_penales.calcular_probabilidades) y decidir a qué zona
       se lanza el arquero, siguiendo el árbol de decisión definido
       en el documento base del proyecto.

Función pública que usará Persona 1 (interfaz.py) y Persona 3 (simulador.py):
    decidir_arquero(probabilidades, presion=None, decisivo=False)

Árbol de decisión implementado:

    Arquero analiza penal
    ├── ¿El pateador tiene zona favorita?
    │   ├── Sí
    │   │   ├── ¿La confianza es alta?
    │   │   │   ├── Sí → Lanzarse a esa zona (zona_favorita)
    │   │   │   └── No → Usar segunda zona más probable (segunda_zona)
    │   └── No
    │       ├── ¿Es penal decisivo?
    │       │   ├── Sí → Cubrir zona segura/baja (entre BI/BC/BD, la de mayor probabilidad)
    │       │   └── No → Elegir zona estadísticamente común (zona_favorita, aunque la confianza sea baja)

Traducción de las preguntas del árbol a los datos de Persona 2:
    - "¿Tiene zona favorita?" = probabilidades["confianza"] != "baja" (alta o media)
    - "¿Confianza alta?"      = probabilidades["confianza"] == "alta"
    - "¿Es decisivo?"         = parámetro `decisivo`, se decide fuera de este
                                módulo (Persona 1, según número de penal /
                                marcador de la tanda).
"""

# Zonas bajas del arco, candidatas a "zona segura" cuando no hay patrón
# claro en un penal decisivo.
ZONAS_BAJAS = ["BI", "BC", "BD"]


def decidir_arquero(probabilidades, presion=None, decisivo=False):
    """
    Decide a qué zona se lanza el arquero, recorriendo el árbol de
    decisión del documento base a partir de las probabilidades del
    pateador (calculadas por Persona 2 en calcular_probabilidades).

    Parámetros:
        probabilidades (dict): salida de
            grafo_penales.calcular_probabilidades(jugador, presion, df),
            con al menos las claves "probabilidades", "zona_favorita",
            "segunda_zona" y "confianza".
        presion (str|None): no cambia la lógica del árbol (la presión ya
            fue aplicada por Persona 2 al calcular las probabilidades),
            se recibe solo para dejar constancia en la ruta/recomendación.
        decisivo (bool): True si el penal es decisivo (lo determina
            Persona 1 según el número de penal o el marcador de la tanda).

    Retorna un diccionario:
        {
          "zona_lanzamiento": str,
          "confianza_decision": "alta"|"media"|"baja",
          "recomendacion": str,
          "ruta": [str, ...],   # pasos recorridos en el árbol
        }
    """
    ruta = ["Arquero analiza penal"]

    tiene_zona_favorita = probabilidades["confianza"] != "baja"

    if tiene_zona_favorita:
        ruta.append("¿Zona favorita? Sí")
        confianza_alta = probabilidades["confianza"] == "alta"

        if confianza_alta:
            ruta.append("¿Confianza alta? Sí")
            zona = probabilidades["zona_favorita"]
            confianza_decision = "alta"
            recomendacion = (
                f"El pateador tiene una zona favorita muy marcada: el arquero "
                f"se lanza a {zona} (probabilidad {probabilidades['probabilidad_favorita']}%)."
            )
        else:
            ruta.append("¿Confianza alta? No")
            zona = probabilidades["segunda_zona"]
            confianza_decision = "media"
            recomendacion = (
                f"La zona favorita no es lo bastante dominante (confianza media): "
                f"el arquero cubre la segunda zona más probable, {zona} "
                f"(probabilidad {probabilidades['probabilidad_segunda']}%)."
            )

        ruta.append(f"→ {zona}")

    else:
        ruta.append("¿Zona favorita? No")

        if decisivo:
            ruta.append("¿Es penal decisivo? Sí")
            probs_bajas = {z: probabilidades["probabilidades"][z] for z in ZONAS_BAJAS}
            zona = max(probs_bajas, key=lambda z: probs_bajas[z])
            confianza_decision = "baja"
            recomendacion = (
                f"No hay un patrón claro en el pateador y el penal es decisivo: "
                f"el arquero se cubre en la zona baja más probable, {zona}."
            )
        else:
            ruta.append("¿Es penal decisivo? No")
            zona = probabilidades["zona_favorita"]
            confianza_decision = "baja"
            recomendacion = (
                f"No hay un patrón claro y el penal no es decisivo: el arquero "
                f"igual elige la zona estadísticamente más común, {zona}, "
                f"aunque la confianza sea baja."
            )

        ruta.append(f"→ {zona}")

    return {
        "zona_lanzamiento": zona,
        "confianza_decision": confianza_decision,
        "recomendacion": recomendacion,
        "ruta": ruta,
    }
