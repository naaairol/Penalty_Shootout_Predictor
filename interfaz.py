from __future__ import annotations

import multiprocessing as mp
import os
import random
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QParallelAnimationGroup, QRect, QThread, Signal, Qt)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QGraphicsScene,
    QGraphicsView, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QStackedWidget,
    QGraphicsBlurEffect,
    QVBoxLayout, QWidget
)

import grafo_penales as gp
from arbol_arquero import decidir_arquero
from simulador import simular_penales


BASE_DIR = Path(__file__).resolve().parent

# El programa revisa varias ubicaciones y usa la primera que exista.
POSIBLES_CSV = [
    BASE_DIR / "penales_jugadores.csv",
    BASE_DIR / "datitos.csv",
    BASE_DIR / "datos" / "penales_jugadores.csv",
]
CSV_PATH = next((ruta for ruta in POSIBLES_CSV if ruta.exists()), POSIBLES_CSV[0])
ARQUEROS_CSV_PATH = BASE_DIR / "penales_arqueros.csv"
SIMULACIONES_PREDETERMINADAS = 2000

IMG_DIR = BASE_DIR / "imagenes"
LOGOS_DIR = IMG_DIR / "logos"
PLAYERS_DIR = IMG_DIR / "Imagenes jugadores"
KEEPERS_DIR = IMG_DIR / "Imagenes arqueros"
STADIUMS_DIR = IMG_DIR / "estadios"
SIM_DIR = IMG_DIR / "simulacion"

HOME = Path.home()
ONEDRIVE = Path(os.environ.get("OneDrive", HOME / "OneDrive"))

EXTERNAL_IMAGE_ROOTS = [
    PLAYERS_DIR,
    KEEPERS_DIR,
    IMG_DIR / "Imagenes jugadores",
    IMG_DIR / "Imagenes arqueros",
    HOME / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes jugadores",
    HOME / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes arqueros",
    ONEDRIVE / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes jugadores",
    ONEDRIVE / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes arqueros",
]

ZONAS = [
    ["AI", "AC", "AD"],
    ["MI", "MC", "MD"],
    ["BI", "BC", "BD"],
]

NOMBRES = {
    "AI": "Alto izquierda", "AC": "Alto centro", "AD": "Alto derecha",
    "MI": "Medio izquierda", "MC": "Medio centro", "MD": "Medio derecha",
    "BI": "Bajo izquierda", "BC": "Bajo centro", "BD": "Bajo derecha",
}

LOGOS_EQUIPOS = {
    "Argentina": "argentina.png",
    "Ecuador": "ecuador.png",
    "Francia": "francia.png",
    "Inglaterra": "inglaterra.png",
    "España": "espana.png",
    "Brasil": "brasil.png",
    "Portugal": "portugal.png",
}


ESTILO = r"""
* {
    font-family: "Segoe UI";
    color: #edf7f2;
}

QMainWindow, QWidget {
    background: #030910;
}

QFrame#topbar {
    background: #07131d;
    border-bottom: 1px solid #1e3948;
}

QFrame#panel, QFrame#card, QFrame#majorCard {
    background: #08151f;
    border: 1px solid #203a49;
    border-radius: 16px;
}

QFrame#majorCard {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #0b1c28, stop:1 #06111a);
}

QFrame#selectedCard {
    background: #0b221c;
    border: 2px solid #43ed8f;
    border-radius: 16px;
}

QLabel#brand {
    font-size: 20px;
    font-weight: 900;
    color: #43ed8f;
    letter-spacing: 1px;
}

QLabel#pageTitle {
    font-size: 28px;
    font-weight: 900;
    color: white;
}

QLabel#heroTitle {
    font-size: 55px;
    font-weight: 900;
    color: white;
}

QLabel#heroAccent {
    font-size: 55px;
    font-weight: 900;
    color: #43ed8f;
}

QLabel#subtitle, QLabel#muted {
    color: #8aa0ad;
    font-size: 13px;
}

QLabel#section {
    color: #43ed8f;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 2px;
}

QLabel#metric {
    color: #43ed8f;
    font-size: 26px;
    font-weight: 900;
}

QLabel#bigMetric {
    color: #43ed8f;
    font-size: 46px;
    font-weight: 900;
}

QLabel#warning {
    color: #ffca56;
    font-weight: 700;
}

QPushButton {
    min-height: 44px;
    padding: 0 20px;
    border: 1px solid #18a75b;
    border-radius: 11px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0b8e49, stop:1 #15b862);
    color: white;
    font-size: 13px;
    font-weight: 850;
}

QPushButton:hover {
    border-color: #62ffae;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #10a957, stop:1 #1bd071);
}

QPushButton:disabled {
    background: #172630;
    border-color: #2b414d;
    color: #607480;
}

QPushButton#secondary {
    background: #0b1924;
    border-color: #2a495b;
    color: #c9d7de;
}

QPushButton#secondary:hover {
    background: #102535;
    border-color: #4a7186;
}

QPushButton#helpButton {
    background: #102331;
    border: 1px solid #36586b;
    min-width: 100px;
}

QPushButton#zoneButton {
    min-width: 120px;
    min-height: 82px;
    background: #0b1d29;
    border: 1px solid #2a4b5d;
    font-size: 15px;
}

QPushButton#zoneButton:hover {
    border: 2px solid #43ed8f;
    background: #103025;
}

QPushButton#treeNode {
    min-width: 160px;
    min-height: 55px;
    background: #0d2230;
    border: 1px solid #2b5368;
}

QPushButton#treeNodeActive {
    min-width: 160px;
    min-height: 55px;
    background: #123623;
    border: 2px solid #43ed8f;
}

QComboBox, QSpinBox {
    min-height: 44px;
    padding: 0 12px;
    border: 1px solid #2b4d60;
    border-radius: 10px;
    background: #06131d;
    font-size: 13px;
}

QComboBox:hover, QSpinBox:hover {
    border-color: #43ed8f;
}

QComboBox QAbstractItemView {
    background: #081923;
    border: 1px solid #2b4d60;
    selection-background-color: #109652;
}

QCheckBox {
    spacing: 10px;
    color: #cbd8df;
}

QCheckBox::indicator {
    width: 21px;
    height: 21px;
}

QCheckBox::indicator:unchecked {
    background: #07141e;
    border: 1px solid #34586b;
    border-radius: 6px;
}

QCheckBox::indicator:checked {
    background: #38da80;
    border: 1px solid #65ffb0;
    border-radius: 6px;
}

QProgressBar {
    min-height: 9px;
    border: none;
    border-radius: 5px;
    background: #142632;
}

QProgressBar::chunk {
    border-radius: 5px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #21b965, stop:1 #55f39a);
}

QScrollArea {
    border: none;
    background: transparent;
}

QGraphicsView {
    border: none;
    background: transparent;
}

QWidget#welcomePage {
    background:#02070d;
}

QFrame#welcomeLeft {
    border-right:1px solid #1b3442;
    background:qlineargradient(
        x1:0,y1:0,x2:1,y2:1,
        stop:0 #07131d,
        stop:0.55 #09202b,
        stop:1 #061019
    );
}

QLabel#heroSubtitle {
    color:#91a7b4;
    font-size:17px;
    line-height:1.4;
}

QPushButton#primaryLarge {
    min-height:58px;
    border-radius:14px;
    font-size:15px;
}

QFrame#bottomNav {
    background:#06111a;
    border-top:1px solid #1e3847;
}

QPushButton#navButton {
    min-height:58px;
    padding:4px 8px;
    background:transparent;
    border:1px solid transparent;
    border-radius:10px;
    color:#879ca8;
    font-size:11px;
    font-weight:700;
}

QPushButton#navButton:hover {
    background:#0a1c28;
    border-color:#29495a;
    color:white;
}

QPushButton#navButton[active="true"] {
    background:#0b2431;
    border:1px solid #1a6b48;
    color:#43ed8f;
}


QWidget#simulationField {
    background:#06121b;
    border-radius:14px;
}


QPushButton#modeCard {
    min-height: 260px;
    padding: 24px;
    text-align: left;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #0b1c28, stop:1 #07131d);
    border:1px solid #29495a;
    border-radius:18px;
    font-size:18px;
    font-weight:850;
}

QPushButton#modeCard:hover {
    border:2px solid #43ed8f;
    background:#0d2722;
}

QPushButton#modeCard[active="true"] {
    border:2px solid #43ed8f;
    background:#103025;
}
"""


def slug(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", str(texto))
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", limpio).strip("_").lower()
    return limpio


def clave_compacta(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", str(texto))
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]", "", limpio).lower()


def nombre_legible_desde_archivo(nombre: str) -> str:
    texto = Path(nombre).stem.replace("_", " ").replace("-", " ")
    texto = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])", " ", texto)
    return " ".join(p.capitalize() for p in texto.split())


def raices_imagenes() -> list[Path]:
    roots = [IMG_DIR, PLAYERS_DIR, KEEPERS_DIR, LOGOS_DIR, STADIUMS_DIR, SIM_DIR]
    roots.extend(EXTERNAL_IMAGE_ROOTS)
    disponibles = []
    vistos = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        if resolved in vistos or not root.exists():
            continue
        vistos.add(resolved)
        disponibles.append(root)
    return disponibles


def buscar_imagen(carpeta: Path, nombre: str) -> Path | None:
    objetivo = clave_compacta(nombre)
    if carpeta.exists():
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            directa = carpeta / f"{slug(nombre)}{ext}"
            if directa.exists():
                return directa
        try:
            for archivo in carpeta.rglob("*"):
                if (archivo.is_file() and archivo.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                        and clave_compacta(archivo.stem) == objetivo):
                    return archivo
        except (OSError, PermissionError):
            pass
    return None


def buscar_imagen_persona(nombre: str, equipo: str, tipo: str, pose: str | None = None) -> Path | None:
    nombre_key = clave_compacta(nombre)
    equipo_key = clave_compacta(equipo)
    pose_key = clave_compacta(pose or "")
    tipo_key = clave_compacta(tipo)
    candidatos: list[tuple[int, Path]] = []

    for root in raices_imagenes():
        try:
            for archivo in root.rglob("*"):
                if not archivo.is_file() or archivo.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    continue
                if clave_compacta(archivo.stem) != nombre_key:
                    continue
                ruta_key = clave_compacta(str(archivo.parent))
                puntos = 0
                if equipo_key and equipo_key in ruta_key:
                    puntos += 8
                if pose_key and pose_key in ruta_key:
                    puntos += 6
                if tipo_key and tipo_key in ruta_key:
                    puntos += 4
                if IMG_DIR in archivo.parents:
                    puntos += 2
                candidatos.append((puntos, archivo))
        except (OSError, PermissionError):
            continue

    if not candidatos:
        return None
    candidatos.sort(key=lambda item: item[0], reverse=True)
    return candidatos[0][1]


def listar_arqueros_por_equipo(equipo: str) -> list[str]:
    equipo_key = clave_compacta(equipo)
    encontrados: dict[str, str] = {}
    for root in raices_imagenes():
        try:
            for archivo in root.rglob("*"):
                if not archivo.is_file() or archivo.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    continue
                parent_key = clave_compacta(str(archivo.parent))
                if equipo_key not in parent_key:
                    continue
                if "pateando" in parent_key or "parado" in parent_key:
                    continue
                if "arquero" not in parent_key and "keeper" not in parent_key:
                    continue
                nombre = nombre_legible_desde_archivo(archivo.name)
                encontrados[clave_compacta(nombre)] = nombre
        except (OSError, PermissionError):
            continue
    return sorted(encontrados.values())


ARQUEROS_RESPALDO = {
    "Argentina": ["Emiliano Martínez"],
    "Francia": ["Hugo Lloris", "Mike Maignan"],
    "Inglaterra": ["Jordan Pickford"],
    "España": ["David Raya", "Joan García", "Unai Simón"],
}


def listar_estadios() -> list[str]:
    """Obtiene los nombres de estadio directamente desde imagenes/estadios."""
    if not STADIUMS_DIR.exists():
        return []

    nombres = []
    for archivo in STADIUMS_DIR.rglob("*"):
        if archivo.is_file() and archivo.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            nombre = nombre_legible_desde_archivo(archivo.name)
            if nombre not in nombres:
                nombres.append(nombre)

    return sorted(nombres)


def buscar_imagen_estadio(nombre: str) -> Path | None:
    """
    Busca el estadio aunque el ComboBox muestre un nombre legible y el archivo
    tenga guiones, espacios, mayúsculas o acentos diferentes.
    """
    if not STADIUMS_DIR.exists():
        return None

    objetivo = clave_compacta(nombre)
    mejor = None

    for archivo in STADIUMS_DIR.rglob("*"):
        if not archivo.is_file():
            continue
        if archivo.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue

        stem = clave_compacta(archivo.stem)

        if stem == objetivo:
            return archivo

        if objetivo in stem or stem in objetivo:
            mejor = archivo

    return mejor


class Worker(QThread):
    listo = Signal(dict)
    error = Signal(str)

    def __init__(self, jugador, arquero, n, presion, decisivo):
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


class Card(QFrame):
    def __init__(self, layout=None, object_name="card"):
        super().__init__()
        self.setObjectName(object_name)
        if layout:
            self.setLayout(layout)


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cómo utilizar Penalty Vision Pro")
        self.resize(760, 650)
        self.setStyleSheet(ESTILO)

        root = QVBoxLayout(self)
        title = QLabel("¿CÓMO UTILIZAR PENALTY VISION PRO?")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        intro = QLabel(
            "La aplicación analiza el comportamiento histórico de un pateador y "
            "genera una recomendación explicable para el arquero."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        root.addWidget(intro)

        pasos = [
            ("01", "Selecciona los equipos",
             "Escoge el equipo que patea y el equipo que defiende. No pueden ser iguales."),
            ("02", "Configura el escenario",
             "Define estadio, clima, cancha, fase, presión y si el penal es decisivo."),
            ("03", "Selecciona protagonistas",
             "Elige el pateador, el arquero y la cantidad de simulaciones."),
            ("04", "Revisa la predicción",
             "Observa el mapa de calor, las probabilidades y la recomendación."),
            ("05", "Explora el árbol",
             "Presiona los nodos para conocer por qué el sistema tomó cada decisión."),
            ("06", "Prueba la simulación",
             "Selecciona manualmente una de las nueve zonas del arco."),
            ("07", "Compara el resultado",
             "La aplicación compara tu elección con el patrón histórico y la decisión del arquero."),
        ]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)

        for numero, titulo, descripcion in pasos:
            fila = QHBoxLayout()
            badge = QLabel(numero)
            badge.setObjectName("metric")
            badge.setFixedWidth(58)
            fila.addWidget(badge)

            text_box = QVBoxLayout()
            t = QLabel(titulo)
            t.setStyleSheet("font-size:17px;font-weight:800;")
            d = QLabel(descripcion)
            d.setObjectName("muted")
            d.setWordWrap(True)
            text_box.addWidget(t)
            text_box.addWidget(d)
            fila.addLayout(text_box, 1)

            layout.addWidget(Card(fila))

        layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll)

        close = QPushButton("ENTENDIDO")
        close.clicked.connect(self.accept)
        root.addWidget(close)


class ImageLabel(QLabel):
    def __init__(
        self,
        size=(170, 170),
        fallback="SIN IMAGEN",
        transparent=False,
    ):
        super().__init__()
        self.setFixedSize(*size)
        self.setAlignment(Qt.AlignCenter)
        self.fallback = fallback
        self.transparent = transparent

        if transparent:
            self.setStyleSheet(
                "background:transparent;border:none;"
                "font-size:16px;color:#708692;"
            )
        else:
            self.setStyleSheet(
                "background:#06131d;border:1px solid #2a4b5c;"
                "border-radius:16px;font-size:16px;color:#708692;"
            )

        self.setText(fallback)

    def load(self, path: Path | None):
        if not path or not path.exists():
            self.setPixmap(QPixmap())
            self.setText(self.fallback)
            return False

        pix = QPixmap(str(path))
        if pix.isNull():
            self.setPixmap(QPixmap())
            self.setText(self.fallback)
            return False

        self.setText("")
        self.setPixmap(
            pix.scaled(
                self.width(),
                self.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        return True


class CoverImageLabel(QLabel):
    """Muestra una imagen ocupando toda la tarjeta sin deformarla."""

    def __init__(self, size=(590, 330), fallback="IMAGEN DEL ESTADIO"):
        super().__init__()
        self.setFixedSize(*size)
        self.setAlignment(Qt.AlignCenter)
        self.fallback = fallback
        self.original = QPixmap()
        self.setStyleSheet(
            "background:#07131d;border:1px solid #2a4b5c;"
            "border-radius:16px;color:#708692;font-size:16px;"
        )
        self.setText(fallback)

    def load(self, path: Path | None):
        if not path or not path.exists():
            self.original = QPixmap()
            self.setPixmap(QPixmap())
            self.setText(self.fallback)
            self.setToolTip(
                f"No se encontró una imagen en:\n{STADIUMS_DIR}"
            )
            return False

        pix = QPixmap(str(path))
        if pix.isNull():
            self.original = QPixmap()
            self.setPixmap(QPixmap())
            self.setText(self.fallback)
            return False

        self.original = pix
        self.setText("")
        self._refresh()
        self.setToolTip(str(path))
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self.original.isNull():
            return

        scaled = self.original.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        x = max(0, (scaled.width() - self.width()) // 2)
        y = max(0, (scaled.height() - self.height()) // 2)
        cropped = scaled.copy(x, y, self.width(), self.height())
        self.setPixmap(cropped)


class GoalHeatmap(QWidget):
    def __init__(self):
        super().__init__()
        self.probs = {z: 0.0 for row in ZONAS for z in row}
        self.highlight = None
        self.setMinimumSize(520, 345)

    def set_data(self, probs, highlight):
        self.probs = probs
        self.highlight = highlight
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = 22
        w = self.width() - margin * 2
        h = self.height() - margin * 2

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#102534"))
        gradient.setColorAt(1, QColor("#06121c"))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#8399a5"), 4))
        painter.drawRoundedRect(margin, margin, w, h, 12, 12)

        cw, ch = w / 3, h / 3
        max_prob = max(self.probs.values()) if self.probs else 1

        for i, row in enumerate(ZONAS):
            for j, zone in enumerate(row):
                x = margin + j * cw
                y = margin + i * ch
                p = float(self.probs.get(zone, 0.0))
                ratio = p / max(max_prob, 1)

                if ratio >= 0.75:
                    color = QColor(220, 53, 69, 210)
                elif ratio >= 0.45:
                    color = QColor(235, 161, 31, 205)
                elif ratio >= 0.25:
                    color = QColor(40, 166, 95, 195)
                else:
                    color = QColor(14, 65, 76, 185)

                painter.setBrush(color)
                painter.setPen(
                    QPen(
                        QColor("#55f39a") if zone == self.highlight else QColor("#2d5665"),
                        4 if zone == self.highlight else 1,
                    )
                )
                painter.drawRect(int(x), int(y), int(cw), int(ch))

                painter.setPen(QColor("white"))
                painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
                painter.drawText(
                    int(x), int(y + 8), int(cw), int(ch / 2),
                    Qt.AlignCenter, zone
                )
                painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
                painter.drawText(
                    int(x), int(y + ch / 2 - 8), int(cw), int(ch / 2),
                    Qt.AlignCenter, f"{p:.1f}%"
                )


class InteractiveTree(QWidget):
    node_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.route = []
        self.info = QLabel("Selecciona un nodo para conocer su explicación.")
        self.info.setWordWrap(True)
        self.info.setObjectName("muted")

        root = QVBoxLayout(self)
        title = QLabel("ÁRBOL DE DECISIÓN INTERACTIVO")
        title.setObjectName("section")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)

        definitions = [
            ("inicio", "¿Existe zona favorita?", 0, 1),
            ("confianza", "¿Confianza alta?", 1, 0),
            ("presion", "¿Presión alta?", 1, 2),
            ("segunda", "Segunda zona", 2, 0),
            ("favorita", "Zona favorita", 2, 1),
            ("baja", "Mejor zona baja", 2, 2),
            ("decision", "DECISIÓN FINAL", 3, 1),
        ]

        for key, text, row, col in definitions:
            btn = QPushButton(text)
            btn.setObjectName("treeNode")
            btn.clicked.connect(lambda _, k=key: self.explain(k))
            self.nodes[key] = btn
            grid.addWidget(btn, row, col)

        root.addLayout(grid)
        root.addWidget(Card(QVBoxLayout(), "panel"))
        root.itemAt(root.count() - 1).widget().layout().addWidget(self.info)

    def set_path(self, route):
        self.route = route or []
        text_route = " ".join(str(x).lower() for x in self.route)

        for key, btn in self.nodes.items():
            active = any(token in text_route for token in key.split("_"))
            btn.setObjectName("treeNodeActive" if active else "treeNode")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.nodes["decision"].setObjectName("treeNodeActive")
        self.nodes["decision"].style().unpolish(self.nodes["decision"])
        self.nodes["decision"].style().polish(self.nodes["decision"])

    def explain(self, key):
        explanations = {
            "inicio":
                "El sistema comprueba si alguna zona concentra una probabilidad "
                "suficientemente mayor que las demás.",
            "confianza":
                "La confianza depende de qué tan dominante es la primera zona "
                "respecto de la segunda y del resto del arco.",
            "presion":
                "En escenarios de presión alta o penal decisivo se priorizan "
                "decisiones más conservadoras y zonas históricamente repetidas.",
            "segunda":
                "Cuando la confianza no es suficiente, la segunda zona más "
                "frecuente puede ser una alternativa razonable.",
            "favorita":
                "La zona favorita es la que posee la mayor probabilidad histórica "
                "estimada para el pateador seleccionado.",
            "baja":
                "Cuando la confianza es baja y el penal es decisivo, el árbol puede "
                "priorizar una zona baja con buen peso histórico.",
            "decision":
                "Este nodo resume la recomendación final producida después de "
                "recorrer las reglas anteriores.",
        }
        self.info.setText(explanations[key])
        self.node_clicked.emit(key)


class GoalOverlay(QWidget):
    """Portería dividida en nueve zonas clicables."""

    zone_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.probs = {z: 0.0 for fila in ZONAS for z in fila}
        self.hovered_zone = None
        self.selected_zone = None
        self.recommended_zone = None
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background:transparent;")

    def set_probabilities(self, probs, recommended_zone=None):
        self.probs = probs or self.probs
        self.recommended_zone = recommended_zone
        self.update()

    def zone_at(self, pos):
        rect = self.rect().adjusted(8, 8, -8, -8)
        if not rect.contains(pos):
            return None
        cell_w = rect.width() / 3
        cell_h = rect.height() / 3
        col = min(2, max(0, int((pos.x() - rect.left()) / cell_w)))
        row = min(2, max(0, int((pos.y() - rect.top()) / cell_h)))
        return ZONAS[row][col]

    def mouseMoveEvent(self, event):
        self.hovered_zone = self.zone_at(event.position().toPoint())
        self.update()

    def leaveEvent(self, event):
        self.hovered_zone = None
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            zone = self.zone_at(event.position().toPoint())
            if zone:
                self.selected_zone = zone
                self.update()
                self.zone_clicked.emit(zone)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)

        # Fondo suave de la portería
        painter.setBrush(QColor(4, 15, 22, 75))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        cell_w = rect.width() / 3
        cell_h = rect.height() / 3
        max_prob = max(self.probs.values()) if self.probs else 1.0

        for row, fila in enumerate(ZONAS):
            for col, zone in enumerate(fila):
                x = rect.left() + int(col * cell_w)
                y = rect.top() + int(row * cell_h)
                cell = QRect(x, y, int(cell_w), int(cell_h))
                prob = float(self.probs.get(zone, 0.0))
                intensity = prob / max(max_prob, 1.0)

                if zone == self.selected_zone:
                    fill = QColor(61, 237, 143, 125)
                elif zone == self.hovered_zone:
                    fill = QColor(71, 198, 255, 95)
                elif intensity >= 0.70:
                    fill = QColor(220, 58, 69, 90)
                elif intensity >= 0.40:
                    fill = QColor(236, 171, 35, 75)
                else:
                    fill = QColor(27, 112, 77, 40)

                painter.fillRect(cell, fill)
                painter.setPen(QPen(QColor(205, 224, 233, 125), 1))
                painter.drawRect(cell)

                if zone == self.recommended_zone:
                    painter.setPen(QPen(QColor('#55f39a'), 3))
                    painter.drawRect(cell.adjusted(2, 2, -2, -2))

                painter.setPen(QColor('white'))
                painter.setFont(QFont('Segoe UI', 10, QFont.Bold))
                painter.drawText(cell.adjusted(0, 7, 0, 0), Qt.AlignHCenter | Qt.AlignTop, zone)
                painter.setFont(QFont('Segoe UI', 11, QFont.Bold))
                painter.drawText(cell, Qt.AlignCenter, f'{prob:.1f}%')

        # Marco principal
        painter.setPen(QPen(QColor(238, 245, 248, 235), 5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)


class SimulationField(QWidget):
    zone_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(510)
        self.setObjectName('simulationField')

        self.background = CoverImageLabel((900, 510), '')
        self.background.setParent(self)
        self.background.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.background.setStyleSheet(
            'background:qlineargradient(x1:0,y1:0,x2:0,y2:1,'
            'stop:0 #0b2638,stop:0.65 #0a4932,stop:1 #08291d);'
            'border:none;border-radius:14px;'
        )

        # Desenfoque del estadio para que funcione solo como fondo.
        self.background_blur = QGraphicsBlurEffect(self)
        self.background_blur.setBlurRadius(11)
        self.background.setGraphicsEffect(self.background_blur)

        # Capa oscura encima del estadio para mejorar la legibilidad.
        self.dark_overlay = QLabel(self)
        self.dark_overlay.setStyleSheet(
            'background:rgba(2, 8, 13, 118);'
            'border:none;border-radius:14px;'
        )
        self.dark_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.goal_overlay = GoalOverlay(self)
        self.goal_overlay.zone_clicked.connect(self.zone_selected.emit)

        self.player = ImageLabel((190, 265), 'JUGADOR', transparent=True)
        self.player.setParent(self)
        self.player.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.keeper = ImageLabel((190, 225), 'ARQUERO', transparent=True)
        self.keeper.setParent(self)
        self.keeper.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.ball = ImageLabel((58, 58), '', transparent=True)
        self.ball.setParent(self)
        self.ball.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.result = QLabel('', self)
        self.result.setAlignment(Qt.AlignCenter)
        self.result.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.ball_anim = QPropertyAnimation(self.ball, b'pos', self)
        self.keeper_anim = QPropertyAnimation(self.keeper, b'pos', self)
        self.player_anim = QPropertyAnimation(self.player, b'pos', self)
        self.animation_group = QParallelAnimationGroup(self)
        self.animation_group.addAnimation(self.ball_anim)
        self.animation_group.addAnimation(self.keeper_anim)
        self.animation_group.addAnimation(self.player_anim)
        self.animation_group.finished.connect(self._animation_finished)
        self.pending_outcome = 'GOL'

    def set_probabilities(self, probs, recommended_zone):
        self.goal_overlay.set_probabilities(probs, recommended_zone)

    def set_assets(self, player_name, keeper_name, stadium_name, kicking_team, defending_team):
        self.player.load(buscar_imagen_persona(player_name, kicking_team, 'jugadores', 'Pateando'))
        self.keeper.load(buscar_imagen_persona(keeper_name, defending_team, 'arqueros'))

        stadium_path = buscar_imagen_estadio(stadium_name)
        self.background.load(stadium_path)

        ball_path = buscar_imagen(SIM_DIR, 'balon')
        if ball_path:
            self.ball.load(ball_path)
        else:
            self.ball.setText('⚽')
            self.ball.setStyleSheet('background:transparent;border:none;font-size:40px;')

        self.reset_positions()
        self.raise_elements()

    def raise_elements(self):
        self.background.lower()
        self.dark_overlay.raise_()
        self.goal_overlay.raise_()
        self.keeper.raise_()
        self.player.raise_()
        self.ball.raise_()
        self.result.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self.background.setGeometry(0, 0, w, h)
        self.dark_overlay.setGeometry(0, 0, w, h)

        goal_w = min(520, int(w * 0.56))
        goal_h = min(270, int(h * 0.53))
        self.goal_overlay.setGeometry(w // 2 - goal_w // 2, 28, goal_w, goal_h)

        if self.animation_group.state() != QParallelAnimationGroup.Running:
            self.reset_positions()
        self.result.setGeometry(0, h - 88, w, 76)
        self.raise_elements()

    def reset_positions(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        self.keeper.move(w // 2 - self.keeper.width() // 2, 78)
        self.player.move(max(20, w // 2 - 360), h - self.player.height() - 18)
        self.ball.move(w // 2 - self.ball.width() // 2, h - 120)
        self.result.setText('')

    def zone_target(self, zone):
        goal = self.goal_overlay.geometry().adjusted(8, 8, -8, -8)
        row = {'A': 0, 'M': 1, 'B': 2}[zone[0]]
        col = {'I': 0, 'C': 1, 'D': 2}[zone[1]]
        cw = goal.width() / 3
        ch = goal.height() / 3
        x = goal.left() + int(cw * col + cw / 2) - self.ball.width() // 2
        y = goal.top() + int(ch * row + ch / 2) - self.ball.height() // 2
        return QPoint(x, y)

    def play(self, chosen_zone, keeper_zone, outcome):
        self.animation_group.stop()
        self.pending_outcome = outcome
        self.reset_positions()
        self.goal_overlay.selected_zone = chosen_zone
        self.goal_overlay.update()

        start_ball = self.ball.pos()
        ball_target = self.zone_target(chosen_zone)
        keeper_center = self.zone_target(keeper_zone)
        keeper_target = QPoint(
            keeper_center.x() - self.keeper.width() // 2 + self.ball.width() // 2,
            keeper_center.y() - self.keeper.height() // 2 + self.ball.height() // 2,
        )
        player_start = self.player.pos()
        player_target = QPoint(player_start.x() + 105, player_start.y() - 12)

        self.ball_anim.setDuration(1250)
        self.ball_anim.setStartValue(start_ball)
        self.ball_anim.setEndValue(ball_target)
        self.ball_anim.setEasingCurve(QEasingCurve.InQuad)

        self.keeper_anim.setDuration(1000)
        self.keeper_anim.setStartValue(self.keeper.pos())
        self.keeper_anim.setEndValue(keeper_target)
        self.keeper_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.player_anim.setDuration(620)
        self.player_anim.setStartValue(player_start)
        self.player_anim.setEndValue(player_target)
        self.player_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.raise_elements()
        self.animation_group.start()

    def _animation_finished(self):
        self.show_result(self.pending_outcome)

    def show_result(self, outcome):
        colors = {'GOL': '#55f39a', 'ATAJADA': '#48c6ff', 'FALLADO': '#ff5c69'}
        self.result.setStyleSheet(
            'background:rgba(2,8,13,205);'
            f'font-size:44px;font-weight:900;color:{colors[outcome]};'
        )
        self.result.setText(outcome)


class PenaltyVisionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Penalty Vision Pro")
        self.resize(1500, 900)
        self.setStyleSheet(ESTILO)

        self.df = pd.DataFrame()
        self.df_keepers = pd.DataFrame()
        self.context = {}
        self.probs = None
        self.decision = None
        self.sim_result = None
        self.worker = None
        self.previous_page = 0

        self.load_data()

        root = QWidget()
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.topbar = self.build_topbar()
        main_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self.bottom_nav = self.build_bottom_nav()
        main_layout.addWidget(self.bottom_nav)

        self.setCentralWidget(root)

        self.pages = {
            "welcome": self.build_welcome(),
            "help": self.build_help_page(),
            "teams": self.build_teams(),
            "mode": self.build_mode_page(),
            "conditions": self.build_conditions(),
            "selection": self.build_selection(),
            "dashboard": self.build_dashboard(),
            "tree": self.build_tree_page(),
            "simulation": self.build_simulation_page(),
            "report": self.build_report(),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.go("welcome")

    def load_data(self):
        try:
            if not CSV_PATH.exists():
                rutas_probadas = "\n".join(
                    f"- {ruta}" for ruta in POSIBLES_CSV
                )
                raise FileNotFoundError(
                    "No se encontró el archivo con los datos de jugadores.\n\n"
                    "Rutas revisadas:\n"
                    f"{rutas_probadas}"
                )

            gp.cargar_penales(str(CSV_PATH))
            self.df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

            if ARQUEROS_CSV_PATH.exists():
                self.df_keepers = pd.read_csv(
                    ARQUEROS_CSV_PATH,
                    encoding="utf-8-sig"
                )
            else:
                self.df_keepers = pd.DataFrame()

            if self.df.empty:
                raise ValueError("El archivo de jugadores está vacío.")

            columnas_obligatorias = {"jugador"}
            faltantes = columnas_obligatorias - set(self.df.columns)
            if faltantes:
                raise ValueError(
                    "Faltan columnas obligatorias en el CSV: "
                    + ", ".join(sorted(faltantes))
                )

        except Exception as exc:
            self.df = pd.DataFrame()
            self.df_keepers = pd.DataFrame()
            QMessageBox.critical(
                self,
                "Error al cargar datos",
                "No se pudo iniciar el análisis.\n\n"
                f"Archivo seleccionado:\n{CSV_PATH}\n\n"
                f"Detalle:\n{exc}"
            )


    def build_topbar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(68)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(28, 0, 28, 0)

        brand = QLabel("⚽  PENALTY VISION PRO")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        layout.addStretch()

        self.page_indicator = QLabel("")
        self.page_indicator.setObjectName("muted")
        layout.addWidget(self.page_indicator)

        help_btn = QPushButton("❓  AYUDA")
        help_btn.setObjectName("helpButton")
        help_btn.clicked.connect(self.open_help_dialog)
        layout.addWidget(help_btn)
        return bar

    def build_bottom_nav(self):
        nav = QFrame()
        nav.setObjectName("bottomNav")
        nav.setFixedHeight(82)

        layout = QHBoxLayout(nav)
        layout.setContentsMargins(24, 8, 24, 8)
        layout.setSpacing(8)

        brand_box = QVBoxLayout()
        brand = QLabel("PENALTY")
        brand.setStyleSheet("font-size:12px;font-weight:900;color:white;")
        accent = QLabel("VISION PRO")
        accent.setStyleSheet("font-size:12px;font-weight:900;color:#43ed8f;")
        brand_box.addWidget(brand)
        brand_box.addWidget(accent)

        brand_widget = QWidget()
        brand_widget.setLayout(brand_box)
        brand_widget.setFixedWidth(150)
        layout.addWidget(brand_widget)

        self.nav_buttons = {}
        items = [
            ("welcome", "⌂", "Inicio"),
            ("help", "?", "Guía"),
            ("teams", "◈", "Equipos"),
            ("mode", "⇄", "Modo"),
            ("conditions", "⌖", "Escenario"),
            ("selection", "♙", "Jugador"),
            ("dashboard", "⌘", "Predicción"),
            ("tree", "◇", "Árbol"),
            ("simulation", "◉", "Simulación"),
            ("report", "▣", "Reporte"),
        ]

        for page_name, icon, label in items:
            button = QPushButton(f"{icon}\n{label}")
            button.setObjectName("navButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda _, page=page_name: self.navigate_from_bar(page)
            )
            self.nav_buttons[page_name] = button
            layout.addWidget(button, 1)

        settings = QPushButton("⚙")
        settings.setObjectName("navButton")
        settings.setToolTip("Ayuda")
        settings.clicked.connect(self.open_help_dialog)
        settings.setFixedWidth(70)
        layout.addWidget(settings)

        return nav

    def navigate_from_bar(self, page_name):
        protected = {"dashboard", "tree", "simulation", "report"}

        if page_name in protected and not self.decision:
            QMessageBox.information(
                self,
                "Análisis pendiente",
                "Primero selecciona los equipos, configura el escenario y analiza un pateador."
            )
            return

        if page_name == "tree":
            self.open_tree()
            return

        if page_name == "simulation":
            self.prepare_simulation()
            return

        if page_name == "report":
            self.show_report()
            return

        self.go(page_name)

    def update_nav_state(self, active_page):
        if not hasattr(self, "nav_buttons"):
            return

        for page, button in self.nav_buttons.items():
            button.setProperty("active", page == active_page)
            button.style().unpolish(button)
            button.style().polish(button)

    def open_help_dialog(self):
        HelpDialog(self).exec()

    def go(self, page_name):
        page = self.pages[page_name]
        self.stack.setCurrentWidget(page)

        titles = {
            "welcome": "INICIO",
            "help": "GUÍA DE USO",
            "teams": "EQUIPOS",
            "mode": "TIPO DE ANÁLISIS",
            "conditions": "CONDICIONES",
            "selection": "PATEADOR Y ARQUERO",
            "dashboard": "PREDICCIÓN",
            "tree": "ÁRBOL INTERACTIVO",
            "simulation": "SIMULACIÓN",
            "report": "REPORTE FINAL",
        }
        self.page_indicator.setText(titles[page_name])

        self.topbar.setVisible(page_name != "welcome")
        self.bottom_nav.setVisible(page_name != "welcome")
        self.update_nav_state(page_name)

    def button(self, text, callback, secondary=False):
        b = QPushButton(text)
        if secondary:
            b.setObjectName("secondary")
        b.clicked.connect(callback)
        return b

    def build_welcome(self):
        w = QWidget()
        w.setObjectName("welcomePage")

        root = QHBoxLayout(w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Panel izquierdo: identidad visual
        left = QFrame()
        left.setObjectName("welcomeLeft")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(70, 70, 70, 70)

        left_layout.addStretch()

        title_1 = QLabel("PENALTY")
        title_1.setObjectName("heroTitle")
        title_1.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_1)

        title_2 = QLabel("VISION PRO")
        title_2.setObjectName("heroAccent")
        title_2.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_2)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background:#1e3847;border:none;")
        left_layout.addSpacing(14)
        left_layout.addWidget(line)

        brand_text = QLabel("PREDICCIÓN INTELIGENTE PARA TANDAS DE PENALES")
        brand_text.setObjectName("subtitle")
        brand_text.setAlignment(Qt.AlignCenter)
        brand_text.setWordWrap(True)
        left_layout.addSpacing(14)
        left_layout.addWidget(brand_text)

        left_layout.addStretch()

        small = QLabel("Diseñado para apoyar decisiones antes del disparo")
        small.setObjectName("muted")
        small.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(small)

        # Panel derecho: propuesta simple para entrenadores
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(95, 80, 95, 80)

        right_layout.addStretch()

        heading = QLabel("Antes del disparo,\nya tendrás una estrategia.")
        heading.setObjectName("heroTitle")
        heading.setWordWrap(True)
        right_layout.addWidget(heading)

        description = QLabel(
            "Conoce hacia dónde suele lanzar un jugador y recibe una recomendación "
            "clara para ayudar al arquero a decidir en una tanda de penales."
        )
        description.setObjectName("heroSubtitle")
        description.setWordWrap(True)
        description.setMaximumWidth(720)
        right_layout.addSpacing(18)
        right_layout.addWidget(description)

        right_layout.addSpacing(42)

        start_button = self.button(
            "COMENZAR ANÁLISIS   →",
            lambda: self.go("help")
        )
        start_button.setObjectName("primaryLarge")
        start_button.setMinimumWidth(350)
        start_button.setMinimumHeight(58)
        right_layout.addWidget(start_button, alignment=Qt.AlignLeft)

        right_layout.addSpacing(18)

        note = QLabel(
            "En pocos pasos: equipos, escenario, jugador, predicción y simulación."
        )
        note.setObjectName("muted")
        right_layout.addWidget(note)

        right_layout.addStretch()

        root.addWidget(left, 5)
        root.addWidget(right, 7)
        return w

    def build_help_page(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(55, 35, 55, 35)

        title = QLabel("¿CÓMO SE UTILIZA?")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Sigue estos pasos para preparar el análisis y recibir una recomendación clara."
        )
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        root.addSpacing(20)

        grid = QGridLayout()
        grid.setSpacing(18)

        items = [
            (
                "01", "Selecciona los equipos",
                "Escoge quién va a patear y quién tendrá al arquero."
            ),
            (
                "02", "Configura el partido",
                "Indica el estadio, el clima, la cancha, la fase y la presión."
            ),
            (
                "03", "Escoge jugador y arquero",
                "Selecciona a los protagonistas del penal."
            ),
            (
                "04", "Revisa la recomendación",
                "El sistema muestra hacia dónde suele lanzar el jugador."
            ),
            (
                "05", "Comprende la decisión",
                "El árbol explica paso a paso por qué se eligió esa zona."
            ),
            (
                "06", "Prueba el penal",
                "Elige una zona y observa si coincide con la predicción."
            ),
        ]

        for i, (number, heading, desc) in enumerate(items):
            box = QVBoxLayout()

            n = QLabel(number)
            n.setObjectName("metric")
            box.addWidget(n)

            h = QLabel(heading)
            h.setStyleSheet("font-size:18px;font-weight:850;")
            box.addWidget(h)

            d = QLabel(desc)
            d.setObjectName("muted")
            d.setWordWrap(True)
            box.addWidget(d)

            box.addStretch()
            grid.addWidget(Card(box), i // 3, i % 3)

        root.addLayout(grid, 1)

        trainer_note = QLabel(
            "La recomendación no reemplaza la decisión del entrenador: sirve como apoyo "
            "para preparar una estrategia antes del disparo."
        )
        trainer_note.setWordWrap(True)
        trainer_note.setObjectName("warning")
        root.addWidget(trainer_note)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(
            self.button(
                "CONTINUAR   →",
                lambda: self.go("teams")
            )
        )
        root.addLayout(row)
        return w

    def team_card(self, role):
        layout = QVBoxLayout()
        label = QLabel(role)
        label.setObjectName("section")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        image = ImageLabel((190, 190), "🛡️")
        layout.addWidget(image, alignment=Qt.AlignCenter)

        combo = QComboBox()
        equipos_permitidos = ["Argentina", "España"]

        if "equipo" in self.df.columns:
            equipos_csv = {
                str(equipo).strip()
                for equipo in self.df["equipo"].dropna().unique()
            }
            teams = [
                equipo for equipo in equipos_permitidos
                if equipo in equipos_csv
            ]
        else:
            teams = equipos_permitidos

        if not teams:
            teams = equipos_permitidos

        combo.addItems(teams)
        layout.addWidget(combo)

        return Card(layout, "majorCard"), image, combo

    def build_teams(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(55, 35, 55, 35)

        root.addWidget(QLabel("SELECCIÓN DE EQUIPOS", objectName="pageTitle"))
        sub = QLabel("Selecciona el equipo que ejecutará el penal y el equipo que defenderá.")
        sub.setObjectName("subtitle")
        root.addWidget(sub)
        root.addSpacing(25)

        row = QHBoxLayout()
        self.kicking_card, self.logo_kicking, self.team_kicking = self.team_card("EQUIPO QUE PATEA")
        self.defending_card, self.logo_defending, self.team_defending = self.team_card("EQUIPO QUE ATAJA")

        if self.team_defending.count() > 1:
            self.team_defending.setCurrentIndex(1)

        vs = QLabel("VS")
        vs.setAlignment(Qt.AlignCenter)
        vs.setObjectName("bigMetric")
        vs.setFixedWidth(120)

        row.addWidget(self.kicking_card, 1)
        row.addWidget(vs)
        row.addWidget(self.defending_card, 1)
        root.addLayout(row, 1)

        self.team_error = QLabel("")
        self.team_error.setObjectName("warning")
        self.team_error.setAlignment(Qt.AlignCenter)
        root.addWidget(self.team_error)

        self.team_kicking.currentTextChanged.connect(self.update_team_logos)
        self.team_defending.currentTextChanged.connect(self.update_team_logos)
        self.update_team_logos()

        nav = QHBoxLayout()
        nav.addWidget(self.button("←  GUÍA", lambda: self.go("help"), True))
        nav.addStretch()
        nav.addWidget(self.button("CONTINUAR   →", self.save_teams))
        root.addLayout(nav)
        return w

    def update_team_logos(self):
        a = self.team_kicking.currentText()
        b = self.team_defending.currentText()

        def team_logo(team):
            filename = LOGOS_EQUIPOS.get(team)
            if filename and (LOGOS_DIR / filename).exists():
                return LOGOS_DIR / filename
            return buscar_imagen(LOGOS_DIR, team)

        self.logo_kicking.load(team_logo(a))
        self.logo_defending.load(team_logo(b))

        if a and b and a == b:
            self.team_error.setText("⚠ No puedes seleccionar el mismo equipo en ambos lados.")
        else:
            self.team_error.setText("")

    def save_teams(self):
        a = self.team_kicking.currentText()
        b = self.team_defending.currentText()

        if not a or not b:
            QMessageBox.warning(self, "Equipos incompletos", "Selecciona ambos equipos.")
            return

        if a == b:
            QMessageBox.warning(
                self,
                "Selección inválida",
                "El equipo que patea y el equipo que ataja deben ser diferentes.",
            )
            return

        self.context["team_kicking"] = a
        self.context["team_defending"] = b
        self.go("mode")

    def build_mode_page(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(70, 45, 70, 45)
        root.setSpacing(24)

        root.addWidget(QLabel("¿A QUIÉN QUIERES AYUDAR?", objectName="pageTitle"))

        subtitle = QLabel(
            "Elige el objetivo del análisis. El sistema utilizará los mismos datos, "
            "pero dará una recomendación diferente."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(26)

        self.mode_keeper_button = QPushButton(
            "ESTRATEGIA PARA EL ARQUERO\n\n"
            "Predice hacia dónde es más probable que dispare el rival.\n\n"
            "El resultado recomienda hacia qué zona debe lanzarse el arquero."
        )
        self.mode_keeper_button.setObjectName("modeCard")
        self.mode_keeper_button.setCursor(Qt.PointingHandCursor)
        self.mode_keeper_button.clicked.connect(
            lambda: self.select_analysis_mode("arquero")
        )

        self.mode_kicker_button = QPushButton(
            "ESTRATEGIA PARA EL PATEADOR\n\n"
            "Analiza hacia dónde suele lanzarse el arquero rival.\n\n"
            "El resultado recomienda una zona con buena oportunidad de gol."
        )
        self.mode_kicker_button.setObjectName("modeCard")
        self.mode_kicker_button.setCursor(Qt.PointingHandCursor)
        self.mode_kicker_button.clicked.connect(
            lambda: self.select_analysis_mode("pateador")
        )

        cards.addWidget(self.mode_keeper_button, 1)
        cards.addWidget(self.mode_kicker_button, 1)
        root.addLayout(cards, 1)

        self.mode_explanation = QLabel(
            "Selecciona una de las dos opciones para continuar."
        )
        self.mode_explanation.setObjectName("warning")
        self.mode_explanation.setAlignment(Qt.AlignCenter)
        self.mode_explanation.setWordWrap(True)
        root.addWidget(self.mode_explanation)

        nav = QHBoxLayout()
        nav.addWidget(
            self.button("←  EQUIPOS", lambda: self.go("teams"), True)
        )
        nav.addStretch()

        self.mode_continue = self.button(
            "CONTINUAR   →",
            self.continue_from_mode
        )
        self.mode_continue.setEnabled(False)
        nav.addWidget(self.mode_continue)
        root.addLayout(nav)
        return w

    def select_analysis_mode(self, mode):
        self.context["analysis_mode"] = mode

        for button, active in (
            (self.mode_keeper_button, mode == "arquero"),
            (self.mode_kicker_button, mode == "pateador"),
        ):
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)

        if mode == "arquero":
            self.mode_explanation.setText(
                "Modo arquero: analizaremos al pateador rival para anticipar su disparo."
            )
        else:
            self.mode_explanation.setText(
                "Modo pateador: compararemos las zonas del jugador con la cobertura del arquero rival."
            )

        self.mode_continue.setEnabled(True)

    def continue_from_mode(self):
        if not self.context.get("analysis_mode"):
            QMessageBox.warning(
                self,
                "Selecciona un modo",
                "Debes indicar si deseas ayudar al arquero o al pateador."
            )
            return
        self.go("conditions")

    def build_conditions(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(34, 20, 34, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("ESTADIO Y CONDICIONES", objectName="pageTitle"))
        sub = QLabel(
            "El contexto del partido modifica la precisión del pateador, "
            "el riesgo de fallo y la ventaja del arquero."
        )
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()

        mode_text = (
            "OBJETIVO: AYUDAR AL ARQUERO"
            if self.context.get("analysis_mode") == "arquero"
            else "OBJETIVO: AYUDAR AL PATEADOR"
        )
        badge = QLabel(mode_text)
        badge.setStyleSheet(
            "color:#43ed8f;background:#0b2431;border:1px solid #1a6b48;"
            "border-radius:12px;padding:8px 14px;font-weight:800;"
        )
        header.addWidget(badge)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        stadium_layout = QVBoxLayout()
        stadium_layout.setContentsMargins(14, 12, 14, 12)
        stadium_layout.setSpacing(10)
        stadium_layout.addWidget(QLabel("ESTADIO SELECCIONADO", objectName="section"))

        self.stadium_image = CoverImageLabel((560, 300), "NO HAY IMAGEN DEL ESTADIO")
        stadium_layout.addWidget(self.stadium_image, alignment=Qt.AlignCenter)

        self.stadium = QComboBox()
        estadios = listar_estadios()
        if estadios:
            self.stadium.addItems(estadios)
        else:
            self.stadium.addItem("No hay estadios disponibles")
            self.stadium.setEnabled(False)
        stadium_layout.addWidget(self.stadium)

        stadium_hint = QLabel(
            "La fotografía seleccionada se utilizará como fondo "
            "durante la simulación interactiva."
        )
        stadium_hint.setObjectName("muted")
        stadium_hint.setWordWrap(True)
        stadium_hint.setAlignment(Qt.AlignCenter)
        stadium_layout.addWidget(stadium_hint)
        body.addWidget(Card(stadium_layout, "majorCard"), 5)

        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(8)
        form_layout.addWidget(QLabel("CONDICIONES DEL PARTIDO", objectName="section"))

        self.weather = QComboBox()
        self.weather.addItems(["Normal", "Lluvia", "Calor intenso", "Frío intenso"])
        self.pitch = QComboBox()
        self.pitch.addItems(["Seca", "Mojada", "Pesada / deteriorada"])
        self.ambient = QComboBox()
        self.ambient.addItems([
            "Neutral",
            "Público a favor del pateador",
            "Público a favor del arquero",
        ])
        self.noise = QComboBox()
        self.noise.addItems(["Bajo", "Medio", "Alto"])
        self.phase = QComboBox()
        self.phase.addItems(["Octavos", "Cuartos", "Semifinal", "Final"])
        self.pressure = QComboBox()
        self.pressure.addItems(["baja", "alta"])

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        controls = [
            ("Clima", self.weather),
            ("Estado de cancha", self.pitch),
            ("Ambiente", self.ambient),
            ("Ruido del público", self.noise),
            ("Fase del torneo", self.phase),
            ("Nivel de presión", self.pressure),
        ]

        for index, (text, control) in enumerate(controls):
            row = index // 2
            col = (index % 2) * 2
            label = QLabel(text)
            label.setStyleSheet("font-size:12px;font-weight:700;color:#a9bac4;")
            grid.addWidget(label, row * 2, col)
            grid.addWidget(control, row * 2 + 1, col)

        form_layout.addLayout(grid)

        self.deciding = QCheckBox("Penal decisivo / posibilidad de eliminación")
        form_layout.addWidget(self.deciding)

        help_layout = QVBoxLayout()
        help_layout.addWidget(QLabel("¿CÓMO AFECTAN?", objectName="section"))
        help_text = QLabel(
            "• Lluvia y cancha mojada: aumentan el riesgo de fallo.\n"
            "• Presión, ruido y penal decisivo: reducen la precisión.\n"
            "• Público a favor: beneficia al pateador o al arquero.\n"
            "• Cancha pesada: favorece ejecuciones más conservadoras."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color:#9fb0ba;font-size:12px;")
        help_layout.addWidget(help_text)
        help_card = Card(help_layout, "panel")
        help_card.setStyleSheet(
            "QFrame#panel{background:#06121b;border:1px solid #1d3745;"
            "border-radius:12px;padding:8px;}"
        )
        form_layout.addWidget(help_card)
        form_layout.addStretch()

        body.addWidget(Card(form_layout, "majorCard"), 5)
        root.addLayout(body, 1)

        self.stadium.currentTextChanged.connect(self.update_stadium_image)
        self.update_stadium_image()

        nav = QHBoxLayout()
        nav.addWidget(self.button("←  MODO", lambda: self.go("mode"), True))
        nav.addStretch()
        nav.addWidget(self.button("CONTINUAR   →", self.save_conditions))
        root.addLayout(nav)
        return w

    def update_stadium_image(self):
        ruta = buscar_imagen_estadio(self.stadium.currentText())
        encontrada = self.stadium_image.load(ruta)
        if not encontrada:
            self.stadium_image.setText("NO SE ENCONTRÓ LA IMAGEN DEL ESTADIO")

    def save_conditions(self):
        self.context.update({
            "stadium": self.stadium.currentText(),
            "weather": self.weather.currentText(),
            "pitch": self.pitch.currentText(),
            "ambient": self.ambient.currentText(),
            "noise": self.noise.currentText(),
            "phase": self.phase.currentText(),
            "pressure": self.pressure.currentText(),
            "deciding": self.deciding.isChecked(),
        })
        self.update_players()
        self.go("selection")

    def build_selection(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(34, 20, 34, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("PATEADOR Y ARQUERO", objectName="pageTitle"))
        sub = QLabel(
            "El pateador pertenece al equipo atacante y el arquero "
            "pertenece obligatoriamente al equipo defensor."
        )
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()

        teams = QLabel(
            f"{self.context.get('team_kicking', 'Atacante')}  VS  "
            f"{self.context.get('team_defending', 'Defensor')}"
        )
        teams.setStyleSheet(
            "color:white;background:#0b2431;border:1px solid #2a4b5d;"
            "border-radius:12px;padding:8px 16px;font-weight:900;"
        )
        header.addWidget(teams)

        sims = QLabel("2.000 SIMULACIONES")
        sims.setStyleSheet(
            "color:#43ed8f;background:#0b2431;border:1px solid #1a6b48;"
            "border-radius:12px;padding:8px 14px;font-weight:800;"
        )
        header.addWidget(sims)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        player_layout = QVBoxLayout()
        player_layout.setContentsMargins(14, 12, 14, 12)
        player_layout.setSpacing(10)
        player_layout.addWidget(QLabel("PATEADOR", objectName="section"))

        player_content = QHBoxLayout()
        player_content.setSpacing(16)
        self.player_image = ImageLabel((225, 285), "SIN IMAGEN")
        player_content.addWidget(self.player_image, alignment=Qt.AlignTop)

        player_side = QVBoxLayout()
        player_side.addWidget(QLabel("Selecciona al pateador"))
        self.player = QComboBox()
        player_side.addWidget(self.player)

        self.player_info = QLabel("")
        self.player_info.setWordWrap(True)
        self.player_info.setAlignment(Qt.AlignTop)
        self.player_info.setMinimumHeight(210)
        self.player_info.setStyleSheet(
            "font-size:14px;padding:14px;background:#050c13;"
            "border:1px solid #172d3a;border-radius:10px;"
        )
        player_side.addWidget(self.player_info, 1)
        player_content.addLayout(player_side, 1)
        player_layout.addLayout(player_content)
        body.addWidget(Card(player_layout, "majorCard"), 1)

        keeper_layout = QVBoxLayout()
        keeper_layout.setContentsMargins(14, 12, 14, 12)
        keeper_layout.setSpacing(10)
        keeper_layout.addWidget(QLabel("ARQUERO", objectName="section"))

        keeper_content = QHBoxLayout()
        keeper_content.setSpacing(16)
        self.keeper_image = ImageLabel((225, 285), "SIN IMAGEN")
        keeper_content.addWidget(self.keeper_image, alignment=Qt.AlignTop)

        keeper_side = QVBoxLayout()
        keeper_side.addWidget(QLabel("Selecciona al arquero"))
        self.keeper = QComboBox()
        keeper_side.addWidget(self.keeper)

        self.keeper_info = QLabel("")
        self.keeper_info.setWordWrap(True)
        self.keeper_info.setAlignment(Qt.AlignTop)
        self.keeper_info.setMinimumHeight(210)
        self.keeper_info.setStyleSheet(
            "font-size:14px;padding:14px;background:#050c13;"
            "border:1px solid #172d3a;border-radius:10px;"
        )
        keeper_side.addWidget(self.keeper_info, 1)
        keeper_content.addLayout(keeper_side, 1)
        keeper_layout.addLayout(keeper_content)
        body.addWidget(Card(keeper_layout, "majorCard"), 1)

        root.addLayout(body, 1)

        note = QLabel(
            "El sistema analizará al pateador, al arquero y las condiciones "
            "antes de ejecutar las 2.000 simulaciones."
        )
        note.setObjectName("muted")
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        root.addWidget(note)

        self.player.currentTextChanged.connect(self.update_player_card)
        self.keeper.currentTextChanged.connect(self.update_keeper_card)

        nav = QHBoxLayout()
        nav.addWidget(
            self.button("←  CONDICIONES", lambda: self.go("conditions"), True)
        )
        nav.addStretch()
        nav.addWidget(self.button("ANALIZAR PENAL   →", self.analyze))
        root.addLayout(nav)
        return w

    def update_players(self):
        self.player.clear()
        if self.df.empty:
            return

        team = self.context.get("team_kicking")
        if "equipo" in self.df.columns:
            names = (
                self.df.loc[self.df["equipo"].astype(str) == team, "jugador"]
                .dropna().astype(str).unique().tolist()
            )
        else:
            names = gp.listar_jugadores()

        if not names:
            names = gp.listar_jugadores()

        self.player.addItems(sorted(names))
        self.update_keepers()
        self.update_player_card(self.player.currentText())
        self.update_keeper_card(self.keeper.currentText())

    def _keeper_column(self, aliases):
        if self.df_keepers.empty:
            return None

        normalized = {
            clave_compacta(column): column
            for column in self.df_keepers.columns
        }

        for alias in aliases:
            key = clave_compacta(alias)
            if key in normalized:
                return normalized[key]

        return None

    def _keeper_value(self, row, aliases, default="-"):
        for alias in aliases:
            column = self._keeper_column([alias])
            if column and column in row.index:
                value = row.get(column)
                if pd.notna(value) and str(value).strip():
                    return value
        return default

    def update_keepers(self):
        """Muestra solamente arqueros del equipo que está defendiendo."""
        defending_team = self.context.get("team_defending", "")

        self.keeper.blockSignals(True)
        self.keeper.clear()

        names = []

        if not self.df_keepers.empty:
            name_col = self._keeper_column([
                "arquero", "nombre_arquero", "jugador", "nombre"
            ])
            team_col = self._keeper_column([
                "equipo", "equipo_arquero", "seleccion", "pais"
            ])

            if name_col:
                keeper_rows = self.df_keepers

                if team_col:
                    keeper_rows = keeper_rows[
                        keeper_rows[team_col].astype(str).map(clave_compacta)
                        == clave_compacta(defending_team)
                    ]

                names = (
                    keeper_rows[name_col]
                    .dropna()
                    .astype(str)
                    .drop_duplicates()
                    .tolist()
                )

        # Si el CSV no tiene datos, buscar por las carpetas de imágenes.
        if not names:
            names = listar_arqueros_por_equipo(defending_team)

        if not names:
            names = ARQUEROS_RESPALDO.get(defending_team, [])

        self.keeper.addItems(sorted(names))
        self.keeper.blockSignals(False)

        self.update_keeper_card(self.keeper.currentText())

    def update_keeper_card(self, name):
        self.keeper_image.load(
            buscar_imagen_persona(
                name,
                self.context.get("team_defending", ""),
                tipo="arqueros",
            )
        )

        if not name:
            self.keeper_info.setText(
                "No hay arqueros disponibles para el equipo defensor."
            )
            return

        if self.df_keepers.empty:
            self.keeper_info.setText(
                f"<b style='font-size:20px'>{name}</b><br><br>"
                f"Equipo: {self.context.get('team_defending', '-')}<br>"
                "Perfil disponible para el análisis.<br>"
                "El sistema utilizará su distribución de cobertura."
            )
            return

        name_col = self._keeper_column([
            "arquero", "nombre_arquero", "jugador", "nombre"
        ])

        if not name_col:
            self.keeper_info.setText(
                f"<b style='font-size:20px'>{name}</b><br><br>"
                "No se identificó la columna con el nombre del arquero."
            )
            return

        rows = self.df_keepers[
            self.df_keepers[name_col]
            .astype(str)
            .map(clave_compacta)
            == clave_compacta(name)
        ]

        if rows.empty:
            self.keeper_info.setText(
                f"<b style='font-size:20px'>{name}</b><br><br>"
                f"Equipo: {self.context.get('team_defending', '-')}<br>"
                "Perfil disponible para el análisis.<br>"
                "Cobertura estimada a partir de su zona fuerte."
            )
            return

        r = rows.iloc[0]

        equipo = self._keeper_value(
            r, ["equipo", "equipo_arquero", "seleccion", "pais"],
            self.context.get("team_defending", "-")
        )
        pie = self._keeper_value(
            r, ["pie_dominante", "pie", "pierna"]
        )
        penales = self._keeper_value(
            r, ["penales_analizados", "total_penales", "penales", "cantidad_penales"]
        )
        atajadas = self._keeper_value(
            r, ["atajadas", "total_atajadas", "penales_atajados"]
        )
        porcentaje = self._keeper_value(
            r, ["porcentaje_atajadas", "tasa_atajadas", "efectividad", "porcentaje_atajada"]
        )
        zona = self._keeper_value(
            r, ["zona_fuerte", "zona_favorita", "zona_mas_atajada", "zona_lanzamiento_arquero"]
        )
        reaccion = self._keeper_value(
            r, ["tiempo_reaccion", "reaccion", "tiempo_de_reaccion"]
        )

        if str(porcentaje) != "-" and "%" not in str(porcentaje):
            try:
                number = float(porcentaje)
                porcentaje = (
                    f"{number * 100:.1f}%"
                    if 0 <= number <= 1
                    else f"{number:.1f}%"
                )
            except (TypeError, ValueError):
                pass

        self.keeper_info.setText(
            f"<b style='font-size:20px'>{name}</b><br><br>"
            f"Equipo: {equipo}<br>"
            f"Pie dominante: {pie}<br>"
            f"Penales analizados: {penales}<br>"
            f"Atajadas: {atajadas}<br>"
            f"Porcentaje de atajadas: {porcentaje}<br>"
            f"Zona fuerte: {zona}<br>"
            f"Tiempo de reacción: {reaccion}"
        )

    def update_player_card(self, name):
        self.player_image.load(
            buscar_imagen_persona(
                name,
                self.context.get("team_kicking", ""),
                tipo="jugadores",
                pose="Parado",
            )
        )
        if not name or self.df.empty:
            return

        rows = self.df[
            self.df["jugador"].astype(str).str.lower() == name.lower()
        ]
        if rows.empty:
            self.player_info.setText(name)
            return

        r = rows.iloc[0]
        self.player_info.setText(
            f"<b style='font-size:20px'>{r.get('jugador', name)}</b><br><br>"
            f"Equipo: {r.get('equipo', '-')}<br>"
            f"Pie dominante: {r.get('pie_dominante', r.get('pie', '-'))}<br>"
            f"Posición: {r.get('posicion', '-')}<br>"
            f"Penales analizados: {r.get('total_penales', '-')}<br>"
            f"Zona histórica: {r.get('zona_favorita', '-')}"
        )

    def condition_effects(self):
        """Devuelve los ajustes producidos por el contexto del partido."""
        effects = {
            "miss_bonus": 0.0,
            "keeper_bonus": 0.0,
            "player_bonus": 0.0,
            "center_bias": 0.0,
            "low_bias": 0.0,
            "summary": [],
        }

        weather = self.context.get("weather", "Normal")
        pitch = self.context.get("pitch", "Seca")
        ambient = self.context.get("ambient", "Neutral")
        noise = self.context.get("noise", "Bajo")
        pressure = self.context.get("pressure", "baja")
        deciding = self.context.get("deciding", False)

        if weather == "Lluvia":
            effects["miss_bonus"] += 4.0
            effects["low_bias"] += 0.08
            effects["summary"].append("lluvia: más riesgo de fallo y tiros bajos")
        elif weather == "Calor intenso":
            effects["miss_bonus"] += 1.5
            effects["summary"].append("calor: ligera pérdida de precisión")
        elif weather == "Frío intenso":
            effects["miss_bonus"] += 2.0
            effects["summary"].append("frío: menor precisión")

        if pitch == "Mojada":
            effects["miss_bonus"] += 3.0
            effects["low_bias"] += 0.10
            effects["summary"].append("cancha mojada: balón más rápido")
        elif pitch == "Pesada / deteriorada":
            effects["miss_bonus"] += 4.0
            effects["center_bias"] += 0.08
            effects["summary"].append("cancha pesada: ejecución más conservadora")

        if ambient == "Público a favor del pateador":
            effects["player_bonus"] += 3.0
            effects["summary"].append("ambiente favorable al pateador")
        elif ambient == "Público a favor del arquero":
            effects["keeper_bonus"] += 3.0
            effects["miss_bonus"] += 1.0
            effects["summary"].append("ambiente favorable al arquero")

        if noise == "Medio":
            effects["miss_bonus"] += 1.0
        elif noise == "Alto":
            effects["miss_bonus"] += 2.5
            effects["keeper_bonus"] += 1.0
            effects["summary"].append("ruido alto: mayor tensión")

        if pressure == "alta":
            effects["miss_bonus"] += 4.0
            effects["keeper_bonus"] += 2.0
            effects["summary"].append("presión alta")

        if deciding:
            effects["miss_bonus"] += 3.0
            effects["keeper_bonus"] += 2.0
            effects["summary"].append("penal decisivo")

        return effects

    def adjusted_player_probabilities(self, probabilities):
        """
        Ajusta la distribución de disparos según las condiciones del partido.
        El total siempre vuelve a normalizarse al 100%.
        """
        effects = self.condition_effects()
        adjusted = {
            zone: max(0.01, float(value))
            for zone, value in probabilities.items()
        }

        if effects["low_bias"]:
            for zone in ("BI", "BC", "BD"):
                adjusted[zone] *= 1.0 + effects["low_bias"]

        if effects["center_bias"]:
            for zone in ("AC", "MC", "BC"):
                adjusted[zone] *= 1.0 + effects["center_bias"]

        total = sum(adjusted.values()) or 1.0
        return {
            zone: value * 100.0 / total
            for zone, value in adjusted.items()
        }

    def simulated_heatmap(self, probabilities, n=2000):
        """Genera el mapa de calor a partir de las simulaciones realizadas."""
        zones = list(probabilities.keys())
        weights = [float(probabilities[z]) for z in zones]
        results = random.choices(zones, weights=weights, k=n)
        counts = {zone: 0 for zone in zones}

        for zone in results:
            counts[zone] += 1

        return {
            zone: counts[zone] * 100.0 / n
            for zone in zones
        }

    def keeper_probabilities(self, keeper_name):
        """Obtiene las nueve probabilidades de movimiento/cobertura del arquero."""
        uniform = {zone: 100.0 / 9.0 for row in ZONAS for zone in row}

        if self.df_keepers.empty or not keeper_name:
            return uniform

        name_col = self._keeper_column([
            "arquero", "nombre_arquero", "jugador", "nombre"
        ])
        if not name_col:
            return uniform

        rows = self.df_keepers[
            self.df_keepers[name_col].astype(str).map(clave_compacta)
            == clave_compacta(keeper_name)
        ]
        if rows.empty:
            return uniform

        row = rows.iloc[0]
        values = {}

        aliases = {
            "AI": ["AI", "alto_izquierda", "arriba_izquierda"],
            "AC": ["AC", "alto_centro", "arriba_centro"],
            "AD": ["AD", "alto_derecha", "arriba_derecha"],
            "MI": ["MI", "medio_izquierda"],
            "MC": ["MC", "medio_centro"],
            "MD": ["MD", "medio_derecha"],
            "BI": ["BI", "bajo_izquierda", "abajo_izquierda"],
            "BC": ["BC", "bajo_centro", "abajo_centro"],
            "BD": ["BD", "bajo_derecha", "abajo_derecha"],
        }

        for zone, possible_names in aliases.items():
            column = self._keeper_column(possible_names)
            if column:
                try:
                    value = float(row.get(column, 0) or 0)
                except (TypeError, ValueError):
                    value = 0.0
                values[zone] = max(0.0, value)

        if not values or sum(values.values()) <= 0:
            strong_zone = str(
                self._keeper_value(
                    row,
                    ["zona_fuerte", "zona_favorita", "zona_mas_atajada"],
                    ""
                )
            ).upper().strip()

            values = uniform.copy()
            if strong_zone in values:
                values = {zone: 65.0 / 8.0 for zone in values}
                values[strong_zone] = 35.0
            return values

        total = sum(values.values())
        # Completar zonas que falten.
        for row_zones in ZONAS:
            for zone in row_zones:
                values.setdefault(zone, 0.0)

        return {
            zone: value * 100.0 / total
            for zone, value in values.items()
        }

    def recommend_for_kicker(self, player_probs, keeper_probs):
        """
        Combina:
        - capacidad/frecuencia histórica del pateador;
        - baja cobertura del arquero.
        """
        scores = {}
        max_player = max(player_probs.values()) or 1.0
        max_keeper = max(keeper_probs.values()) or 1.0

        for zone in player_probs:
            player_strength = float(player_probs[zone]) / max_player
            keeper_risk = float(keeper_probs.get(zone, 0.0)) / max_keeper

            # 65% habilidad/hábito del pateador + 35% evitar al arquero.
            scores[zone] = (
                0.65 * player_strength
                + 0.35 * (1.0 - keeper_risk)
            )

        best_zone = max(scores, key=scores.get)
        sorted_zones = sorted(scores, key=scores.get, reverse=True)
        second_zone = sorted_zones[1]

        return {
            "zona_lanzamiento": best_zone,
            "confianza_decision": (
                "alta"
                if scores[best_zone] - scores[second_zone] >= 0.12
                else "media"
            ),
            "recomendacion": (
                f"Conviene disparar a {NOMBRES[best_zone]} ({best_zone}). "
                f"Es una zona favorable para el pateador y presenta menor riesgo "
                f"de cobertura del arquero rival."
            ),
            "ruta": [
                "Analizar zonas del pateador",
                "Analizar cobertura del arquero",
                "Comparar ventaja por zona",
                f"Elegir {best_zone}",
            ],
            "scores": scores,
        }

    def weighted_zone(self, probabilities):
        zones = list(probabilities.keys())
        weights = [max(0.0, float(probabilities[z])) for z in zones]
        if sum(weights) <= 0:
            return random.choice(zones)
        return random.choices(zones, weights=weights, k=1)[0]

    def analyze(self):
        if not self.player.currentText():
            QMessageBox.warning(self, "Sin pateador", "Selecciona un pateador.")
            return

        if not self.keeper.currentText():
            QMessageBox.warning(self, "Sin arquero", "Selecciona un arquero.")
            return

        try:
            self.probs = gp.calcular_probabilidades(
                self.player.currentText(),
                presion=self.context["pressure"],
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error de análisis", str(exc))
            return

        self.context["player"] = self.player.currentText()
        self.context["keeper"] = self.keeper.currentText()

        self.raw_player_zone_probs = self.probs["probabilidades"]
        self.player_zone_probs = self.adjusted_player_probabilities(
            self.raw_player_zone_probs
        )
        self.keeper_zone_probs = self.keeper_probabilities(
            self.context["keeper"]
        )

        # La función del árbol recibe las probabilidades ya ajustadas.
        adjusted_result = dict(self.probs)
        adjusted_result["probabilidades"] = self.player_zone_probs

        if self.context.get("analysis_mode") == "pateador":
            self.decision = self.recommend_for_kicker(
                self.player_zone_probs,
                self.keeper_zone_probs,
            )
        else:
            self.decision = decidir_arquero(
                adjusted_result,
                presion=self.context["pressure"],
                decisivo=self.context["deciding"],
            )

        self.refresh_dashboard()
        self.go("dashboard")

    def build_dashboard(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(22, 14, 22, 18)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_box.addWidget(
            QLabel("DASHBOARD DE PREDICCIÓN", objectName="pageTitle")
        )

        self.dashboard_explanation = QLabel(
            "Primero se ejecutan 2.000 simulaciones. Después se genera "
            "el mapa de calor y la recomendación."
        )
        self.dashboard_explanation.setObjectName("subtitle")
        self.dashboard_explanation.setWordWrap(True)
        title_box.addWidget(self.dashboard_explanation)

        header.addLayout(title_box, 1)
        header.addStretch()

        self.dashboard_context = QLabel("")
        self.dashboard_context.setObjectName("subtitle")
        self.dashboard_context.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.dashboard_context.setMinimumWidth(230)
        header.addWidget(self.dashboard_context)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(14)

        # ---------------- MAPA DE CALOR ----------------
        heat_layout = QVBoxLayout()
        heat_layout.setContentsMargins(12, 10, 12, 10)
        heat_layout.setSpacing(8)

        heat_title = QLabel("MAPA DE CALOR DE LAS 2.000 SIMULACIONES")
        heat_title.setObjectName("section")
        heat_layout.addWidget(heat_title)

        self.heat_waiting = QLabel(
            "AÚN NO SE HAN EJECUTADO LAS SIMULACIONES\n\n"
            "El mapa aparecerá cuando el sistema complete las 2.000 "
            "ejecuciones del escenario seleccionado."
        )
        self.heat_waiting.setAlignment(Qt.AlignCenter)
        self.heat_waiting.setWordWrap(True)
        self.heat_waiting.setStyleSheet(
            "font-size:16px;color:#8aa0ad;padding:28px;"
            "background:#050c13;border:1px dashed #29495a;"
            "border-radius:12px;"
        )
        heat_layout.addWidget(self.heat_waiting, 1)

        self.heatmap = GoalHeatmap()
        self.heatmap.setMinimumHeight(360)
        self.heatmap.hide()
        heat_layout.addWidget(self.heatmap, 1)

        self.heat_legend = QLabel(
            "Rojo: más repetida · Amarillo: media · Verde/Azul: menos repetida"
        )
        self.heat_legend.setObjectName("muted")
        self.heat_legend.setAlignment(Qt.AlignCenter)
        self.heat_legend.setWordWrap(True)
        self.heat_legend.hide()
        heat_layout.addWidget(self.heat_legend)

        content.addWidget(Card(heat_layout, "majorCard"), 2)

        # ---------------- RESUMEN DEL ANÁLISIS ----------------
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        objective_box = QVBoxLayout()
        objective_box.setSpacing(6)
        objective_box.addWidget(QLabel("OBJETIVO DEL ANÁLISIS", objectName="section"))

        self.analysis_objective = QLabel("")
        self.analysis_objective.setWordWrap(True)
        self.analysis_objective.setAlignment(Qt.AlignTop)
        self.analysis_objective.setStyleSheet(
            "font-size:14px;font-weight:700;padding:12px;"
            "background:#06131d;border-radius:10px;"
        )
        objective_box.addWidget(self.analysis_objective)
        right_layout.addWidget(Card(objective_box, "panel"))

        recommendation_box = QVBoxLayout()
        recommendation_box.setSpacing(6)
        recommendation_box.addWidget(QLabel("RECOMENDACIÓN", objectName="section"))

        self.recommendation = QLabel(
            "La recomendación aparecerá después de las simulaciones."
        )
        self.recommendation.setWordWrap(True)
        self.recommendation.setAlignment(Qt.AlignTop)
        self.recommendation.setMinimumHeight(112)
        self.recommendation.setStyleSheet(
            "font-size:14px;padding:12px;background:#050c13;"
            "border:1px solid #172d3a;border-radius:10px;"
        )
        recommendation_box.addWidget(self.recommendation)
        right_layout.addWidget(Card(recommendation_box, "panel"))

        confidence_box = QHBoxLayout()
        confidence_box.setContentsMargins(12, 7, 12, 7)
        confidence_label = QLabel("CONFIANZA")
        confidence_label.setStyleSheet(
            "font-size:12px;font-weight:800;color:#9fb0ba;"
        )
        confidence_box.addWidget(confidence_label)
        confidence_box.addStretch()

        self.confidence = QLabel("PENDIENTE")
        self.confidence.setStyleSheet(
            "font-size:24px;font-weight:900;color:#43ed8f;"
        )
        confidence_box.addWidget(self.confidence)
        right_layout.addWidget(Card(confidence_box, "panel"))

        conditions_box = QVBoxLayout()
        conditions_box.setSpacing(6)
        conditions_box.addWidget(
            QLabel("CONDICIONES APLICADAS", objectName="section")
        )

        self.condition_result = QLabel("")
        self.condition_result.setWordWrap(True)
        self.condition_result.setAlignment(Qt.AlignTop)
        self.condition_result.setMinimumHeight(76)
        self.condition_result.setStyleSheet(
            "font-size:12px;color:#9fb0ba;padding:10px;"
            "background:#06121b;border-radius:10px;"
        )
        conditions_box.addWidget(self.condition_result)
        right_layout.addWidget(Card(conditions_box, "panel"))

        results_box = QVBoxLayout()
        results_box.setSpacing(6)
        results_box.addWidget(
            QLabel("RESULTADO DE LAS SIMULACIONES", objectName="section")
        )

        self.sim_summary = QLabel("Todavía no hay resultados.")
        self.sim_summary.setWordWrap(True)
        self.sim_summary.setAlignment(Qt.AlignTop)
        self.sim_summary.setMinimumHeight(86)
        self.sim_summary.setStyleSheet(
            "font-size:13px;padding:11px;background:#050c13;"
            "border-radius:10px;"
        )
        results_box.addWidget(self.sim_summary)
        right_layout.addWidget(Card(results_box, "panel"))

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        right_layout.addWidget(self.progress)

        self.sim_button = self.button(
            "EJECUTAR 2.000 SIMULACIONES",
            self.run_monte_carlo
        )
        self.sim_button.setMinimumHeight(50)
        right_layout.addWidget(self.sim_button)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setWidget(right_container)
        right_scroll.setMinimumWidth(410)
        right_scroll.setMaximumWidth(520)

        content.addWidget(right_scroll, 1)
        root.addLayout(content, 1)

        nav = QHBoxLayout()
        nav.addWidget(
            self.button(
                "←  CAMBIAR JUGADOR",
                lambda: self.go("selection"),
                True
            )
        )
        nav.addStretch()

        self.tree_button = self.button(
            "VER CÓMO SE TOMÓ LA DECISIÓN   →",
            self.open_tree
        )
        self.tree_button.setEnabled(False)
        nav.addWidget(self.tree_button)
        root.addLayout(nav)
        return w

    def refresh_dashboard(self):
        mode = self.context.get("analysis_mode", "arquero")

        self.dashboard_context.setText(
            f"{self.context['team_kicking']} vs {self.context['team_defending']}\n"
            f"{self.context['phase']} · Presión {self.context['pressure']}"
        )

        self.heatmap.hide()
        self.heat_legend.hide()
        self.heat_waiting.show()
        self.tree_button.setEnabled(False)

        if mode == "arquero":
            objective = (
                "Se analizará dónde suele disparar el rival para recomendar "
                "hacia dónde debe lanzarse el arquero."
            )
        else:
            objective = (
                "Se compararán las zonas fuertes del pateador con las zonas "
                "que cubre el arquero rival."
            )

        self.analysis_objective.setText(objective)

        effects = self.condition_effects()
        summary = (
            " · ".join(effects["summary"])
            if effects["summary"]
            else "Condiciones neutrales: no se aplican penalizaciones."
        )

        self.recommendation.setText(
            "<b>Recomendación pendiente</b><br><br>"
            "Ejecuta las 2.000 simulaciones para obtener una zona final."
        )
        self.confidence.setText("PENDIENTE")
        self.condition_result.setText(
            f"<b>Condiciones que se aplicarán:</b><br>{summary}"
        )
        self.sim_summary.setText(
            "El mapa de calor contará cuántas veces apareció cada zona "
            "durante las 2.000 simulaciones."
        )

    def run_monte_carlo(self):
        self.sim_button.setEnabled(False)
        self.progress.show()
        self.sim_summary.setText("Procesando simulaciones en paralelo…")

        self.worker = Worker(
            self.context["player"],
            self.context["keeper"],
            SIMULACIONES_PREDETERMINADAS,
            self.context["pressure"],
            self.context["deciding"],
        )
        self.worker.listo.connect(self.monte_carlo_done)
        self.worker.error.connect(self.monte_carlo_error)
        self.worker.start()

    def monte_carlo_done(self, result):
        self.progress.hide()
        self.sim_button.setEnabled(True)
        self.sim_result = result

        # El mapa se genera desde las 2.000 zonas simuladas.
        self.simulated_zone_probs = self.simulated_heatmap(
            self.player_zone_probs,
            SIMULACIONES_PREDETERMINADAS,
        )

        mode = self.context.get("analysis_mode", "arquero")
        zone = self.decision["zona_lanzamiento"]

        if mode == "arquero":
            heat_values = self.simulated_zone_probs
            heading = "RECOMENDACIÓN PARA EL ARQUERO"
            action = "Lanzarse a"
            explanation = (
                "El mapa muestra dónde terminaron los disparos en las "
                "2.000 simulaciones. La recomendación señala la zona más "
                "conveniente para intentar anticipar al rival."
            )
        else:
            score_values = self.decision.get("scores", {})
            max_score = max(score_values.values()) or 1.0
            heat_values = {
                z: score_values.get(z, 0.0) * 100.0 / max_score
                for z in self.player_zone_probs
            }
            heading = "RECOMENDACIÓN PARA EL PATEADOR"
            action = "Disparar a"
            explanation = (
                "El mapa combina la capacidad del pateador con las zonas "
                "menos cubiertas por el arquero rival."
            )

        self.heatmap.set_data(heat_values, zone)
        self.heat_waiting.hide()
        self.heatmap.show()
        self.heat_legend.show()

        self.recommendation.setText(
            f"<h3>{heading}</h3>"
            f"<h2>{action}</h2>"
            f"<h1 style='color:#55f39a'>"
            f"{NOMBRES.get(zone, zone)} ({zone})</h1>"
            f"<p>{self.decision['recomendacion']}</p>"
            f"<p style='color:#8aa0ad'>{explanation}</p>"
        )
        self.confidence.setText(
            self.decision["confianza_decision"].upper()
        )

        r = result["resultados"]
        effects = self.condition_effects()
        adjusted_miss = min(
            100.0,
            float(r["fallado"]) + effects["miss_bonus"]
        )
        adjusted_goal = max(
            0.0,
            float(r["gol"]) - effects["miss_bonus"] * 0.65
        )
        adjusted_save = max(
            0.0,
            100.0 - adjusted_goal - adjusted_miss
        )

        self.sim_summary.setText(
            f"<b>Resultado general de 2.000 simulaciones</b><br><br>"
            f"Gol: <b>{adjusted_goal:.1f}%</b><br>"
            f"Atajada: <b>{adjusted_save:.1f}%</b><br>"
            f"Fallo: <b>{adjusted_miss:.1f}%</b>"
        )

        self.tree_button.setEnabled(True)

    def monte_carlo_error(self, message):
        self.progress.hide()
        self.sim_button.setEnabled(True)
        QMessageBox.critical(self, "Error de simulación", message)

    def build_tree_page(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(26, 18, 26, 22)
        root.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("ÁRBOL DE DECISIÓN", objectName="pageTitle"))
        sub = QLabel(
            "El árbol usa los resultados del grafo y de las simulaciones "
            "para escoger una acción."
        )
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        title_box.addWidget(sub)
        root.addLayout(title_box)

        content = QHBoxLayout()
        content.setSpacing(16)

        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(12, 10, 12, 10)
        tree_layout.addWidget(QLabel("RECORRIDO DEL ÁRBOL", objectName="section"))

        self.interactive_tree = InteractiveTree()
        tree_layout.addWidget(self.interactive_tree, 1)
        content.addWidget(Card(tree_layout, "majorCard"), 3)

        explanation = QVBoxLayout()
        explanation.setContentsMargins(12, 10, 12, 10)
        explanation.setSpacing(10)
        explanation.addWidget(QLabel("EXPLICACIÓN", objectName="section"))

        explanation_text = QLabel(
            "Haz clic en una pregunta del árbol para conocer por qué "
            "esa condición es importante."
        )
        explanation_text.setWordWrap(True)
        explanation_text.setStyleSheet(
            "font-size:14px;padding:12px;background:#06131d;border-radius:10px;"
        )
        explanation.addWidget(explanation_text)

        self.interactive_tree.info.setParent(None)
        self.interactive_tree.info = explanation_text

        explanation.addWidget(QLabel("RUTA REAL UTILIZADA", objectName="section"))

        self.tree_route = QLabel("")
        self.tree_route.setWordWrap(True)
        self.tree_route.setStyleSheet(
            "font-size:14px;padding:14px;background:#050c13;"
            "border:1px solid #172d3a;border-radius:10px;"
        )
        explanation.addWidget(self.tree_route)

        note = QLabel(
            "La ruta muestra las preguntas respondidas antes de producir "
            "la recomendación."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        explanation.addWidget(note)
        explanation.addStretch()

        content.addWidget(Card(explanation, "majorCard"), 2)
        root.addLayout(content, 1)

        nav = QHBoxLayout()
        nav.addWidget(
            self.button("←  PREDICCIÓN", lambda: self.go("dashboard"), True)
        )
        nav.addStretch()
        nav.addWidget(
            self.button("PROBAR LA ESTRATEGIA   →", self.prepare_simulation)
        )
        root.addLayout(nav)
        return w

    def open_tree(self):
        route = self.decision.get("ruta", [])
        self.interactive_tree.set_path(route)
        self.tree_route.setText("  →  ".join(route))
        self.go("tree")

    def build_simulation_page(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(20, 14, 20, 18)
        root.setSpacing(10)

        head = QHBoxLayout()
        head.addWidget(
            QLabel("SIMULACIÓN INTERACTIVA", objectName="pageTitle")
        )
        head.addStretch()

        self.sim_prediction_label = QLabel("")
        self.sim_prediction_label.setObjectName("subtitle")
        self.sim_prediction_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.sim_prediction_label.setWordWrap(True)
        self.sim_prediction_label.setMaximumWidth(470)
        head.addWidget(self.sim_prediction_label)
        root.addLayout(head)

        instruction = QLabel(
            "Haz clic directamente en una de las nueve zonas del arco."
        )
        instruction.setObjectName("warning")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setWordWrap(True)
        root.addWidget(instruction)

        body = QHBoxLayout()
        body.setSpacing(14)

        # ---------------- CAMPO ----------------
        field_layout = QVBoxLayout()
        field_layout.setContentsMargins(5, 5, 5, 5)

        self.sim_field = SimulationField()
        self.sim_field.zone_selected.connect(self.manual_shot)
        field_layout.addWidget(self.sim_field)

        field_card = Card(field_layout, "majorCard")
        field_card.setStyleSheet(
            "QFrame#majorCard{background:#050d14;"
            "border:1px solid #203a49;border-radius:16px;padding:4px;}"
        )
        body.addWidget(field_card, 3)

        # ---------------- PANEL DE RESULTADO ----------------
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(9)

        outcome_layout = QVBoxLayout()
        outcome_layout.setSpacing(4)
        outcome_layout.addWidget(QLabel("RESULTADO", objectName="section"))

        self.sim_outcome = QLabel("—")
        self.sim_outcome.setAlignment(Qt.AlignCenter)
        self.sim_outcome.setMinimumHeight(66)
        self.sim_outcome.setStyleSheet(
            "font-size:39px;font-weight:900;color:#8aa0ad;"
            "background:#050c13;border-radius:10px;"
        )
        outcome_layout.addWidget(self.sim_outcome)

        self.sim_outcome_text = QLabel(
            "Selecciona una zona para comenzar."
        )
        self.sim_outcome_text.setAlignment(Qt.AlignCenter)
        self.sim_outcome_text.setWordWrap(True)
        self.sim_outcome_text.setObjectName("muted")
        outcome_layout.addWidget(self.sim_outcome_text)

        panel_layout.addWidget(Card(outcome_layout, "panel"))

        detail_layout = QVBoxLayout()
        detail_layout.setSpacing(5)
        detail_layout.addWidget(
            QLabel("DETALLE DE LA JUGADA", objectName="section")
        )

        self.sim_zone_detail = QLabel("Zona elegida: —")
        self.sim_zone_detail.setWordWrap(True)
        self.sim_zone_detail.setStyleSheet("font-size:12px;")
        detail_layout.addWidget(self.sim_zone_detail)

        self.sim_frequency_detail = QLabel("Movimiento rival: —")
        self.sim_frequency_detail.setWordWrap(True)
        self.sim_frequency_detail.setStyleSheet("font-size:12px;")
        detail_layout.addWidget(self.sim_frequency_detail)

        self.sim_rank_detail = QLabel("Ranking: —")
        self.sim_rank_detail.setWordWrap(True)
        self.sim_rank_detail.setStyleSheet("font-size:12px;")
        detail_layout.addWidget(self.sim_rank_detail)

        panel_layout.addWidget(Card(detail_layout, "panel"))

        probability_layout = QVBoxLayout()
        probability_layout.setSpacing(6)
        probability_layout.addWidget(
            QLabel("PROBABILIDAD CALCULADA", objectName="section")
        )

        self.sim_goal_detail = QLabel("Gol: —")
        self.sim_goal_detail.setStyleSheet(
            "font-size:16px;font-weight:800;color:#55f39a;"
        )
        probability_layout.addWidget(self.sim_goal_detail)

        self.sim_save_detail = QLabel("Atajada: —")
        self.sim_save_detail.setStyleSheet(
            "font-size:16px;font-weight:800;color:#48c6ff;"
        )
        probability_layout.addWidget(self.sim_save_detail)

        self.sim_miss_detail = QLabel("Fallo: —")
        self.sim_miss_detail.setStyleSheet(
            "font-size:16px;font-weight:800;color:#ffca56;"
        )
        probability_layout.addWidget(self.sim_miss_detail)

        self.sim_probability_bar = QProgressBar()
        self.sim_probability_bar.setRange(0, 100)
        self.sim_probability_bar.setValue(0)
        self.sim_probability_bar.setTextVisible(False)
        probability_layout.addWidget(self.sim_probability_bar)

        panel_layout.addWidget(Card(probability_layout, "panel"))

        tree_layout = QVBoxLayout()
        tree_layout.setSpacing(5)
        tree_layout.addWidget(
            QLabel("COMPARACIÓN CON LA RECOMENDACIÓN", objectName="section")
        )

        self.sim_tree_match = QLabel(
            "Todavía no se ha comparado la jugada con la recomendación."
        )
        self.sim_tree_match.setWordWrap(True)
        self.sim_tree_match.setAlignment(Qt.AlignTop)
        self.sim_tree_match.setMinimumHeight(74)
        self.sim_tree_match.setStyleSheet(
            "font-size:13px;color:#9fb0ba;padding:8px;"
        )
        tree_layout.addWidget(self.sim_tree_match)

        panel_layout.addWidget(Card(tree_layout, "panel"))
        panel_layout.addStretch()

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        side_scroll.setWidget(panel_widget)
        side_scroll.setMinimumWidth(340)
        side_scroll.setMaximumWidth(430)

        body.addWidget(side_scroll, 1)
        root.addLayout(body, 1)

        self.manual_result = QLabel("")
        self.manual_result.hide()

        nav = QHBoxLayout()
        nav.addWidget(
            self.button("←  ÁRBOL", lambda: self.go("tree"), True)
        )
        nav.addStretch()
        nav.addWidget(
            self.button(
                "REPETIR PENAL",
                self.reset_simulation_view,
                True
            )
        )
        nav.addWidget(
            self.button("VER REPORTE   →", self.show_report)
        )
        root.addLayout(nav)
        return w

    def reset_simulation_view(self):
        self.sim_field.animation_group.stop()
        self.sim_field.reset_positions()
        self.sim_field.goal_overlay.selected_zone = None
        self.sim_field.goal_overlay.update()

        self.sim_outcome.setText("—")
        self.sim_outcome.setStyleSheet(
            "font-size:39px;font-weight:900;color:#8aa0ad;"
            "background:#050c13;border-radius:10px;"
        )
        self.sim_outcome_text.setText(
            "Selecciona una zona para comenzar."
        )
        self.sim_zone_detail.setText("Zona elegida: —")
        self.sim_frequency_detail.setText("Movimiento rival: —")
        self.sim_rank_detail.setText("Ranking: —")
        self.sim_goal_detail.setText("Gol: —")
        self.sim_save_detail.setText("Atajada: —")
        self.sim_miss_detail.setText("Fallo: —")
        self.sim_probability_bar.setValue(0)
        self.sim_tree_match.setStyleSheet(
            "font-size:13px;color:#9fb0ba;padding:8px;"
        )
        self.sim_tree_match.setText(
            "Todavía no se ha comparado la jugada con la recomendación."
        )

    def prepare_simulation(self):
        mode = self.context.get("analysis_mode", "arquero")
        recommended_zone = self.decision["zona_lanzamiento"]

        if mode == "arquero":
            self.sim_prediction_label.setText(
                f"Recomendación: lanzar al arquero a "
                f"{NOMBRES.get(recommended_zone, recommended_zone)} "
                f"({recommended_zone})"
            )
            instruction = (
                "Haz clic en la zona hacia la que deseas lanzar al arquero. "
                "El pateador ejecutará su disparo según su historial."
            )
            displayed_probs = self.player_zone_probs
        else:
            self.sim_prediction_label.setText(
                f"Recomendación: disparar a "
                f"{NOMBRES.get(recommended_zone, recommended_zone)} "
                f"({recommended_zone})"
            )
            instruction = (
                "Haz clic en la zona donde deseas disparar. "
                "El arquero se lanzará según su historial."
            )
            displayed_probs = self.player_zone_probs

        # Actualizar la instrucción amarilla.
        instruction_labels = self.pages["simulation"].findChildren(QLabel)
        for label in instruction_labels:
            if "Haz clic" in label.text():
                label.setText(instruction)
                break

        self.sim_field.set_assets(
            self.context["player"],
            self.context["keeper"],
            self.context["stadium"],
            self.context["team_kicking"],
            self.context["team_defending"],
        )
        self.sim_field.set_probabilities(
            displayed_probs,
            recommended_zone,
        )
        self.reset_simulation_view()
        self.go("simulation")

    def manual_shot(self, chosen_zone):
        mode = self.context.get("analysis_mode", "arquero")
        recommended_zone = self.decision["zona_lanzamiento"]

        if mode == "arquero":
            # El usuario elige dónde se lanza el arquero.
            keeper_zone = chosen_zone
            distribution = getattr(
                self,
                "simulated_zone_probs",
                self.player_zone_probs
            )
            shot_zone = self.weighted_zone(distribution)
            shot_probability = float(distribution.get(shot_zone, 0.0))
            same_zone = keeper_zone == shot_zone

            effects = self.condition_effects()
            miss_probability = 7.0 + effects["miss_bonus"]
            save_probability = (
                min(78.0, 58.0 + effects["keeper_bonus"])
                if same_zone else 0.0
            )
            goal_probability = max(
                0.0,
                100.0 - save_probability - miss_probability
            )

            roll = random.random() * 100
            if same_zone and roll < save_probability:
                outcome = "ATAJADA"
            elif roll < save_probability + miss_probability:
                outcome = "FALLADO"
            else:
                outcome = "GOL"

            selected_label = (
                f"Zona elegida por el arquero: "
                f"{NOMBRES[keeper_zone]} ({keeper_zone})"
            )
            action_detail = (
                f"El pateador disparó a {NOMBRES[shot_zone]} ({shot_zone})."
            )
            most_likely = max(
                self.player_zone_probs,
                key=self.player_zone_probs.get
            )
            comparison = (
                "✓ El arquero adivinó la zona del disparo."
                if same_zone
                else (
                    f"El arquero se lanzó a otra zona. En esta jugada simulada "
                    f"el pateador fue a {shot_zone}; la zona más probable era "
                    f"{most_likely}. Una probabilidad alta no significa que "
                    f"siempre ocurrirá."
                )
            )
            animation_shot = shot_zone
            animation_keeper = keeper_zone
            historical_value = shot_probability
            rank_probs = self.player_zone_probs

            self.context["manual_keeper_zone"] = keeper_zone
            self.context["manual_shot_zone"] = shot_zone

        else:
            # El usuario elige dónde dispara el pateador.
            shot_zone = chosen_zone
            keeper_zone = self.weighted_zone(self.keeper_zone_probs)
            shot_probability = float(self.player_zone_probs.get(shot_zone, 0.0))
            keeper_probability = float(
                self.keeper_zone_probs.get(keeper_zone, 0.0)
            )
            same_zone = shot_zone == keeper_zone

            max_player = max(self.player_zone_probs.values()) or 1.0
            player_strength = shot_probability / max_player

            effects = self.condition_effects()
            miss_probability = max(
                4.0,
                15.0 - 9.0 * player_strength
                + effects["miss_bonus"]
                - effects["player_bonus"]
            )

            save_probability = (
                min(
                    78.0,
                    42.0
                    + keeper_probability * 0.55
                    + effects["keeper_bonus"]
                )
                if same_zone else 0.0
            )
            goal_probability = max(
                0.0,
                100.0 - save_probability - miss_probability
            )

            roll = random.random() * 100
            if same_zone and roll < save_probability:
                outcome = "ATAJADA"
            elif roll < save_probability + miss_probability:
                outcome = "FALLADO"
            else:
                outcome = "GOL"

            selected_label = (
                f"Zona elegida por el pateador: "
                f"{NOMBRES[shot_zone]} ({shot_zone})"
            )
            action_detail = (
                f"El arquero se lanzó a "
                f"{NOMBRES[keeper_zone]} ({keeper_zone})."
            )
            comparison = (
                "El arquero cubrió la misma zona."
                if same_zone
                else "✓ El disparo evitó la zona elegida por el arquero."
            )
            animation_shot = shot_zone
            animation_keeper = keeper_zone
            historical_value = shot_probability
            rank_probs = self.player_zone_probs

            self.context["manual_shot_zone"] = shot_zone
            self.context["manual_keeper_zone"] = keeper_zone

        ranking = sorted(
            rank_probs.items(),
            key=lambda item: item[1],
            reverse=True
        )
        rank = next(
            i + 1 for i, (zone, _) in enumerate(ranking)
            if zone == shot_zone
        )

        self.context["manual_zone"] = shot_zone
        self.context["manual_outcome"] = outcome
        self.context["manual_goal_probability"] = goal_probability
        self.context["manual_save_probability"] = save_probability
        self.context["manual_miss_probability"] = miss_probability

        outcome_colors = {
            "GOL": "#55f39a",
            "ATAJADA": "#48c6ff",
            "FALLADO": "#ff5c69",
        }
        outcome_texts = {
            "GOL": "La pelota entró.",
            "ATAJADA": "El arquero detuvo el disparo.",
            "FALLADO": "El disparo no entró al arco.",
        }

        self.sim_outcome.setText(outcome)
        self.sim_outcome.setStyleSheet(
            f"font-size:44px;font-weight:900;"
            f"color:{outcome_colors[outcome]};"
        )
        self.sim_outcome_text.setText(outcome_texts[outcome])
        self.sim_zone_detail.setText(selected_label)
        self.sim_frequency_detail.setText(
            f"{action_detail}\nFrecuencia histórica del disparo: "
            f"{historical_value:.1f}%"
        )
        self.sim_rank_detail.setText(f"Ranking de la zona: {rank}/9")
        self.sim_goal_detail.setText(f"Gol: {goal_probability:.1f}%")
        self.sim_save_detail.setText(
            f"Atajada: {save_probability:.1f}%"
        )
        self.sim_miss_detail.setText(
            f"Fallo: {miss_probability:.1f}%"
        )
        self.sim_probability_bar.setValue(round(goal_probability))

        if (
            (mode == "arquero" and chosen_zone == recommended_zone)
            or (mode == "pateador" and shot_zone == recommended_zone)
        ):
            self.sim_tree_match.setStyleSheet(
                "font-size:16px;font-weight:800;color:#55f39a;"
            )
            self.sim_tree_match.setText(
                f"✓ Seguiste la recomendación del sistema.\n{comparison}"
            )
        else:
            self.sim_tree_match.setStyleSheet(
                "font-size:16px;font-weight:800;color:#ffca56;"
            )
            self.sim_tree_match.setText(
                f"No seguiste la recomendación principal.\n{comparison}"
            )

        self.sim_field.play(
            animation_shot,
            animation_keeper,
            outcome
        )

    def build_report(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(28, 18, 28, 22)
        root.setSpacing(12)

        root.addWidget(QLabel("REPORTE FINAL", objectName="pageTitle"))

        subtitle = QLabel(
            "Resumen del escenario, la recomendación y la prueba interactiva."
        )
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        body = QWidget()
        self.report_layout = QGridLayout(body)
        self.report_layout.setContentsMargins(8, 8, 8, 8)
        self.report_layout.setHorizontalSpacing(16)
        self.report_layout.setVerticalSpacing(16)

        self.report_match = QLabel("")
        self.report_match.setWordWrap(True)
        self.report_prediction = QLabel("")
        self.report_prediction.setWordWrap(True)
        self.report_probabilities = QLabel("")
        self.report_probabilities.setWordWrap(True)
        self.report_simulation = QLabel("")
        self.report_simulation.setWordWrap(True)

        cards = [
            ("PARTIDO Y ESCENARIO", self.report_match, 0, 0),
            ("RECOMENDACIÓN", self.report_prediction, 0, 1),
            ("RESULTADOS DEL ANÁLISIS", self.report_probabilities, 1, 0),
            ("PRUEBA INTERACTIVA", self.report_simulation, 1, 1),
        ]

        for title, label, row, col in cards:
            layout = QVBoxLayout()
            layout.addWidget(QLabel(title, objectName="section"))
            label.setStyleSheet("font-size:14px;padding:8px;")
            layout.addWidget(label)
            layout.addStretch()
            self.report_layout.addWidget(Card(layout, "majorCard"), row, col)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        nav = QHBoxLayout()
        nav.addWidget(
            self.button("←  SIMULACIÓN", lambda: self.go("simulation"), True)
        )
        nav.addStretch()
        nav.addWidget(self.button("NUEVO ANÁLISIS", lambda: self.go("teams")))
        root.addLayout(nav)
        return w

    def show_report(self):
        probs = getattr(self, "simulated_zone_probs", self.player_zone_probs)
        zone = self.decision["zona_lanzamiento"]
        best = sorted(
            probs.items(),
            key=lambda item: item[1],
            reverse=True
        )[:3]

        mode_name = (
            "Estrategia para el arquero"
            if self.context.get("analysis_mode") == "arquero"
            else "Estrategia para el pateador"
        )

        self.report_match.setText(
            f"<h2>{self.context['team_kicking']} vs "
            f"{self.context['team_defending']}</h2>"
            f"<b>Tipo de análisis:</b> {mode_name}<br>"
            f"<b>Estadio:</b> {self.context['stadium']}<br>"
            f"<b>Clima:</b> {self.context['weather']}<br>"
            f"<b>Cancha:</b> {self.context['pitch']}<br>"
            f"<b>Fase:</b> {self.context['phase']}<br>"
            f"<b>Presión:</b> {self.context['pressure']}<br>"
            f"<b>Penal decisivo:</b> "
            f"{'Sí' if self.context['deciding'] else 'No'}"
        )

        self.report_prediction.setText(
            f"<h2 style='color:#55f39a'>"
            f"{NOMBRES.get(zone, zone)} ({zone})</h2>"
            f"<b>Pateador:</b> {self.context['player']}<br>"
            f"<b>Arquero:</b> {self.context['keeper']}<br>"
            f"<b>Confianza:</b> {self.decision['confianza_decision']}<br><br>"
            f"{self.decision['recomendacion']}"
        )

        simulation_results = ""
        if self.sim_result:
            r = self.sim_result["resultados"]
            simulation_results = (
                f"<b>Simulaciones:</b> {SIMULACIONES_PREDETERMINADAS:,}<br>"
                f"<b>Gol:</b> {r['gol']:.1f}%<br>"
                f"<b>Atajada:</b> {r['atajada']:.1f}%<br>"
                f"<b>Fallo:</b> {r['fallado']:.1f}%<br><br>"
            )

        zones_text = "<br>".join(
            f"{index + 1}. {NOMBRES[zone_name]}: {value:.1f}%"
            for index, (zone_name, value) in enumerate(best)
        )

        self.report_probabilities.setText(
            simulation_results
            + "<b>Tres zonas más repetidas:</b><br>"
            + zones_text
            + "<br><br><b>Cómo se tomó la decisión:</b><br>"
            + " → ".join(self.decision["ruta"])
        )

        if self.context.get("manual_zone"):
            shot_zone = self.context.get(
                "manual_shot_zone",
                self.context["manual_zone"]
            )
            keeper_zone = self.context.get("manual_keeper_zone", "-")

            self.report_simulation.setText(
                f"<h2>{self.context['manual_outcome']}</h2>"
                f"<b>Zona del disparo:</b> "
                f"{NOMBRES.get(shot_zone, shot_zone)} ({shot_zone})<br>"
                f"<b>Zona del arquero:</b> "
                f"{NOMBRES.get(keeper_zone, keeper_zone)} ({keeper_zone})<br>"
                f"<b>Probabilidad de gol:</b> "
                f"{self.context.get('manual_goal_probability', 0):.1f}%<br>"
                f"<b>Probabilidad de atajada:</b> "
                f"{self.context.get('manual_save_probability', 0):.1f}%<br>"
                f"<b>Probabilidad de fallo:</b> "
                f"{self.context.get('manual_miss_probability', 0):.1f}%"
            )
        else:
            self.report_simulation.setText(
                "Todavía no se realizó una prueba interactiva."
            )

        self.go("report")


def main():
    mp.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("Penalty Vision Pro")
    app.setStyle("Fusion")

    window = PenaltyVisionApp()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()