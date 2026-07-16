"""Script de prueba rápido para arbol_arquero.py y simulador.py (Persona 3)."""

import json

import grafo_penales as gp
from arbol_arquero import decidir_arquero
from simulador import simular_penales, simular_tanda


def main():
    gp.cargar_penales()  # datos/penales_jugadores.csv por defecto

    jugadores = gp.listar_jugadores()
    print(f"Jugadores disponibles: {len(jugadores)}")

    # --- Caso 1: confianza alta (Messi, con presión alta) -----------------
    probs_messi = gp.calcular_probabilidades("Messi", presion="alta")
    print("\n[Caso 1] Messi, presion=alta")
    print("confianza:", probs_messi["confianza"], "| zona_favorita:", probs_messi["zona_favorita"])
    decision_messi = decidir_arquero(probs_messi, presion="alta", decisivo=False)
    print(json.dumps(decision_messi, ensure_ascii=False, indent=2))
    assert decision_messi["zona_lanzamiento"] in gp.ZONAS

    # --- Caso 2: forzar confianza baja + decisivo --------------------------
    probs_baja = {
        "jugador": "Jugador Ficticio",
        "probabilidades": {"AI": 12, "AC": 11, "AD": 12, "MI": 11, "MC": 11, "MD": 11, "BI": 12, "BC": 10, "BD": 10},
        "zona_favorita": "AI",
        "probabilidad_favorita": 12,
        "segunda_zona": "AD",
        "probabilidad_segunda": 12,
        "confianza": "baja",
        "presion_aplicada": None,
    }
    print("\n[Caso 2] confianza baja, decisivo=True")
    decision_baja_decisiva = decidir_arquero(probs_baja, decisivo=True)
    print(json.dumps(decision_baja_decisiva, ensure_ascii=False, indent=2))
    assert decision_baja_decisiva["zona_lanzamiento"] in ("BI", "BC", "BD")

    print("\n[Caso 2b] confianza baja, decisivo=False")
    decision_baja_normal = decidir_arquero(probs_baja, decisivo=False)
    print(json.dumps(decision_baja_normal, ensure_ascii=False, indent=2))
    assert decision_baja_normal["zona_lanzamiento"] == probs_baja["zona_favorita"]

    # --- simular_penales: caso confianza alta -------------------------------
    print("\n[simular_penales] Messi vs Emiliano Martinez, n=2000, presion=alta")
    resultado_penales = simular_penales("Messi", "Emiliano Martínez", n=2000, presion="alta", decisivo=False)
    print(json.dumps(resultado_penales, ensure_ascii=False, indent=2))
    total_pct = sum(resultado_penales["resultados"].values())
    assert abs(total_pct - 100) < 0.5
    assert resultado_penales["n_simulaciones"] == 2000
    assert sum(resultado_penales["conteos"].values()) == 2000

    # --- simular_penales: caso decisivo, jugador distinto -------------------
    print("\n[simular_penales] Julian Alvarez vs Juan Musso, n=1500, decisivo=True")
    resultado_decisivo = simular_penales("lvarez", "Juan Musso", n=1500, presion="alta", decisivo=True)
    print(json.dumps(resultado_decisivo, ensure_ascii=False, indent=2))
    assert sum(resultado_decisivo["conteos"].values()) == 1500

    # --- simular_tanda: tanda completa entre dos equipos --------------------
    jugadores_local = ["Messi", "lvarez", "Lautaro Mart", "De Paul", "Mac Allister"]
    jugadores_visita = ["Molina", "Otamendi", "Acu", "Tagliafico", "Paredes"]

    print("\n[simular_tanda] Local vs Visita, n=500")
    resultado_tanda = simular_tanda(
        jugadores_local, jugadores_visita,
        arquero_local="Emiliano Martínez", arquero_visita="Juan Musso",
        n_simulaciones=500, penales_por_equipo=5, presion="alta",
    )
    print(json.dumps(resultado_tanda, ensure_ascii=False, indent=2))

    total_tanda_pct = (
        resultado_tanda["equipo_local"]["gana_pct"]
        + resultado_tanda["equipo_visitante"]["gana_pct"]
        + resultado_tanda["empate_pct"]
    )
    assert abs(total_tanda_pct - 100) < 1.0
    assert resultado_tanda["n_simulaciones"] == 500

    print("\nTODAS LAS PRUEBAS PASARON OK")


if __name__ == "__main__":
    main()
