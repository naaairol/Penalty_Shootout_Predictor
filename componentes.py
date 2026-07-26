from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, QParallelAnimationGroup, QRect, Signal, Qt
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget, QGraphicsBlurEffect
)

from utilidades import (
    ZONAS, NOMBRES, STADIUMS_DIR, SIM_DIR,
    buscar_imagen, buscar_imagen_persona, buscar_imagen_estadio
)


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
    def __init__(self, size=(170, 170), fallback="SIN IMAGEN", transparent=False):
        super().__init__()
        self.setFixedSize(*size)
        self.setAlignment(Qt.AlignCenter)
        self.fallback = fallback
        self.transparent = transparent

        self.setProperty("transparent", transparent)
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
    def __init__(self, size=(590, 330), fallback="IMAGEN DEL ESTADIO"):
        super().__init__()
        self.setFixedSize(*size)
        self.setAlignment(Qt.AlignCenter)
        self.fallback = fallback
        self.original = QPixmap()
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
        self.background.setObjectName("simFieldBackground")

        self.background_blur = QGraphicsBlurEffect(self)
        self.background_blur.setBlurRadius(11)
        self.background.setGraphicsEffect(self.background_blur)

        self.dark_overlay = QLabel(self)
        self.dark_overlay.setObjectName("simDarkOverlay")
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
        self.result.setObjectName("simResult")
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
        self.result.setProperty("outcome", outcome)
        self.result.style().unpolish(self.result)
        self.result.style().polish(self.result)
        self.result.setText(outcome)