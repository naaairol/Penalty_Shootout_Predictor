from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from simulador import simular_penales


class Worker(QThread):
    # Hilo secundario que ejecuta las simulaciones de Monte Carlo en segundo plano sin congelar la interfaz gráfica.

    listo = Signal(dict)
    error = Signal(str)

    def __init__(self, jugador: str, arquero: str, n: int, presion: str | None, decisivo: bool):
        super().__init__()
        self.jugador = jugador
        self.arquero = arquero
        self.n = n
        self.presion = presion
        self.decisivo = decisivo

    def run(self):
        try:
            resultado = simular_penales(
                self.jugador,
                self.arquero,
                n=self.n,
                presion=self.presion,
                decisivo=self.decisivo,
            )
            self.listo.emit(resultado)
        except Exception as exc:
            self.error.emit(str(exc))