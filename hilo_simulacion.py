from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from simulador import simular_penales


class Worker(QThread):
    """
    Ejecuta las simulaciones en un hilo secundario para evitar que la
    interfaz gráfica se congele. Dentro de simular_penales se utiliza
    multiprocessing para repartir el cálculo entre varios procesos.
    """

    listo = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        jugador: str,
        arquero: str,
        n: int,
        presion: str | None,
        decisivo: bool,
        clima: str = "Normal",
        cancha: str = "Seca",
        ambiente: str = "Neutral",
        ruido: str = "Bajo",
        fase: str = "Octavos",
    ):
        super().__init__()
        self.jugador = jugador
        self.arquero = arquero
        self.n = n
        self.presion = presion
        self.decisivo = decisivo
        self.clima = clima
        self.cancha = cancha
        self.ambiente = ambiente
        self.ruido = ruido
        self.fase = fase

    def run(self):
        try:
            resultado = simular_penales(
                jugador=self.jugador,
                arquero=self.arquero,
                n=self.n,
                presion=self.presion,
                decisivo=self.decisivo,
                clima=self.clima,
                cancha=self.cancha,
                ambiente=self.ambiente,
                ruido=self.ruido,
                fase=self.fase,
            )
            self.listo.emit(resultado)
        except Exception as exc:
            self.error.emit(str(exc))