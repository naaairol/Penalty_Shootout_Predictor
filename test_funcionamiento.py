"""Prueba rápida para comprobar que las condiciones sí influyen."""

import json

import grafo_penales as gp
from simulador import simular_penales


def mostrar(nombre, resultado):
    print(f"\n--- {nombre} ---")
    print("Resultados:", json.dumps(resultado["resultados"], ensure_ascii=False))
    print("Zona del arquero:", resultado["zona_lanzamiento_arquero"])
    print("Efectos:", " | ".join(resultado["efectos_condiciones"]["summary"]))
    print("Parámetros:", json.dumps(resultado["parametros_modelo"], ensure_ascii=False))


def main():
    gp.cargar_penales()

    comun = {
        "jugador": "Messi",
        "arquero": "Emiliano Martínez",
        "n": 20_000,
        "presion": "baja",
        "decisivo": False,
        "ambiente": "Neutral",
        "ruido": "Bajo",
        "fase": "Octavos",
    }

    normal = simular_penales(
        **comun,
        clima="Normal",
        cancha="Seca",
    )

    lluvia = simular_penales(
        **comun,
        clima="Lluvia",
        cancha="Mojada",
    )

    mostrar("Clima normal y cancha seca", normal)
    mostrar("Lluvia y cancha mojada", lluvia)

    print("\nComparación del porcentaje de fallo")
    print(f"Normal:  {normal['resultados']['fallado']:.2f}%")
    print(f"Lluvia: {lluvia['resultados']['fallado']:.2f}%")

    if lluvia["parametros_modelo"]["prob_fallo"] > normal["parametros_modelo"]["prob_fallo"]:
        print("OK: la lluvia aumentó la probabilidad de fallo del modelo.")
    else:
        raise AssertionError("La lluvia no aumentó la probabilidad de fallo.")


if __name__ == "__main__":
    main()