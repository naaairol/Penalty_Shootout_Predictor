from __future__ import annotations

import multiprocessing as mp
import random
import sys

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget
)

import grafo_penales as gp
from arbol_arquero import decidir_arquero
from simulador import (
    ajustar_probabilidades_condiciones,
    calcular_efectos_condiciones,
    reconstruir_resultado_probabilidades,
)

# Importaciones de los nuevos módulos modularizados
from utilidades import (
    CSV_PATH, ARQUEROS_CSV_PATH, POSIBLES_CSV, SIMULACIONES_PREDETERMINADAS,
    ZONAS, NOMBRES, LOGOS_EQUIPOS, LOGOS_DIR, ARQUEROS_RESPALDO,
    cargar_estilo, clave_compacta, buscar_imagen, buscar_imagen_persona,
    buscar_imagen_estadio, listar_arqueros_por_equipo, listar_estadios
)
from hilo_simulacion import Worker
from componentes import (
    Card, HelpDialog, ImageLabel, CoverImageLabel,
    GoalHeatmap, SimulationField
)


class PenaltyVisionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Penalty Shootout Predictor")
        self.resize(1500, 900)

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

        brand = QLabel("PENALTY SHOOTOUT PREDICTOR")
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
        accent = QLabel("SHOOTOUT PREDICTOR")
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
        protected = {"dashboard", "simulation", "report"}

        if page_name in protected and not self.decision:
            QMessageBox.information(
                self,
                "Análisis pendiente",
                "Primero selecciona los equipos, configura el escenario y analiza un pateador."
            )
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

        left = QFrame()
        left.setObjectName("welcomeLeft")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(70, 70, 70, 70)

        left_layout.addStretch()

        title_1 = QLabel("PENALTY")
        title_1.setObjectName("heroTitle")
        title_1.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_1)

        title_2 = QLabel("SHOOTOUT PREDICTOR")
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
                "05", "Prueba el penal",
                "Elige una zona y observa si coincide con la predicción."
            ),
            (
                "06", "Revisa el reporte",
                "Consulta el escenario, la recomendación y el resultado de la simulación."
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
        """Muestra solamente arqueros del equipo que está defenderá."""
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
        return calcular_efectos_condiciones(
            clima=self.context.get("weather", "Normal"),
            cancha=self.context.get("pitch", "Seca"),
            ambiente=self.context.get("ambient", "Neutral"),
            ruido=self.context.get("noise", "Bajo"),
            fase=self.context.get("phase", "Octavos"),
            presion=self.context.get("pressure", "baja"),
            decisivo=self.context.get("deciding", False),
        )

    def adjusted_player_probabilities(self, probabilities):
        """Aplica clima, cancha y contexto a las probabilidades por zona."""
        return ajustar_probabilidades_condiciones(
            probabilities,
            self.condition_effects(),
        )

    def simulated_heatmap(self, probabilities, n=2000):
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
        for row_zones in ZONAS:
            for zone in row_zones:
                values.setdefault(zone, 0.0)

        return {
            zone: value * 100.0 / total
            for zone, value in values.items()
        }

    def recommend_for_kicker(self, player_probs, keeper_probs):
        scores = {}
        max_player = max(player_probs.values()) or 1.0
        max_keeper = max(keeper_probs.values()) or 1.0

        for zone in player_probs:
            player_strength = float(player_probs[zone]) / max_player
            keeper_risk = float(keeper_probs.get(zone, 0.0)) / max_keeper

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

        # Aplicar lluvia, cancha, ruido, fase, presión y penal decisivo.
        self.player_zone_probs = self.adjusted_player_probabilities(
            self.raw_player_zone_probs
        )

        # Recalcular zona favorita, segunda zona y confianza después
        # de aplicar las condiciones. Así la decisión usa los datos ajustados.
        adjusted_result = reconstruir_resultado_probabilidades(
            self.probs,
            self.player_zone_probs,
        )
        self.adjusted_probs = adjusted_result

        self.keeper_zone_probs = self.keeper_probabilities(
            self.context["keeper"]
        )

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

        self.simulation_button = self.button(
            "PROBAR LA ESTRATEGIA   →",
            self.prepare_simulation
        )
        self.simulation_button.setEnabled(False)
        nav.addWidget(self.simulation_button)
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
        self.simulation_button.setEnabled(False)

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
            jugador=self.context["player"],
            arquero=self.context["keeper"],
            n=SIMULACIONES_PREDETERMINADAS,
            presion=self.context["pressure"],
            decisivo=self.context["deciding"],
            clima=self.context.get("weather", "Normal"),
            cancha=self.context.get("pitch", "Seca"),
            ambiente=self.context.get("ambient", "Neutral"),
            ruido=self.context.get("noise", "Bajo"),
            fase=self.context.get("phase", "Octavos"),
        )
        self.worker.listo.connect(self.monte_carlo_done)
        self.worker.error.connect(self.monte_carlo_error)
        self.worker.start()

    def monte_carlo_done(self, result):
        self.progress.hide()
        self.sim_button.setEnabled(True)
        self.sim_result = result

        # Este mapa proviene de las simulaciones multiproceso reales.
        # Ya incluye lluvia, cancha, ruido, fase, presión y penal decisivo.
        self.simulated_zone_probs = result.get(
            "probabilidades_simuladas",
            self.player_zone_probs,
        )

        mode = self.context.get("analysis_mode", "arquero")
        zone = self.decision["zona_lanzamiento"]

        if mode == "arquero":
            heat_values = self.simulated_zone_probs
            heading = "RECOMENDACIÓN PARA EL ARQUERO"
            action = "Lanzarse a"
            explanation = (
                "El mapa muestra las zonas reales de los disparos que no "
                "salieron fuera durante las 2.000 simulaciones. Todas las "
                "condiciones seleccionadas fueron aplicadas dentro del "
                "multiprocesamiento."
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
                "menos cubiertas por el arquero rival. Las probabilidades "
                "del pateador ya incluyen las condiciones del partido."
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

        # No se vuelven a sumar bonos aquí. Los resultados ya fueron
        # calculados con las condiciones dentro de simulador.py.
        r = result["resultados"]

        self.sim_summary.setText(
            f"<b>Resultado general de "
            f"{result['n_simulaciones']:,} simulaciones</b><br><br>"
            f"Gol: <b>{float(r['gol']):.1f}%</b><br>"
            f"Atajada: <b>{float(r['atajada']):.1f}%</b><br>"
            f"Fallo: <b>{float(r['fallado']):.1f}%</b>"
        )

        effects = result.get("efectos_condiciones", {})
        summary = effects.get("summary", [])
        self.condition_result.setText(
            "<b>Condiciones aplicadas dentro de la simulación:</b><br>"
            + (" · ".join(summary) if summary else "Condiciones neutrales")
        )

        self.simulation_button.setEnabled(True)

    def monte_carlo_error(self, message):
        self.progress.hide()
        self.sim_button.setEnabled(True)
        QMessageBox.critical(self, "Error de simulación", message)

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
            self.button("←  PREDICCIÓN", lambda: self.go("dashboard"), True)
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
        """Ejecuta una jugada interactiva según el modo seleccionado.

        En modo arquero, el usuario elige hacia dónde se lanza el arquero y
        el disparo del pateador se sortea con su distribución de probabilidades.
        En modo pateador, el usuario elige la zona del disparo y el movimiento
        del arquero se sortea con su perfil de cobertura.

        La recomendación representa la mejor decisión estadística, pero no
        garantiza que una jugada individual termine en atajada o gol.
        """
        mode = self.context.get("analysis_mode", "arquero")
        recommended_zone = self.decision["zona_lanzamiento"]
        effects = self.condition_effects()

        if mode == "arquero":
            # El usuario decide a qué zona se lanza el arquero.
            keeper_zone = chosen_zone

            # El pateador no está obligado a disparar a la zona predicha.
            # La zona real se sortea utilizando sus probabilidades ajustadas.
            distribution = getattr(
                self,
                "simulated_zone_probs",
                self.player_zone_probs,
            )
            shot_zone = self.weighted_zone(distribution)
            shot_probability = float(distribution.get(shot_zone, 0.0))
            same_zone = keeper_zone == shot_zone

            # Las condiciones aumentan o reducen el riesgo de fallo.
            miss_probability = 7.0 + effects["miss_bonus"]
            miss_probability -= effects["player_bonus"]
            miss_probability = min(45.0, max(2.0, miss_probability))

            if same_zone:
                # El arquero acertó exactamente la zona del disparo.
                save_probability = min(
                    78.0,
                    58.0 + effects["keeper_bonus"],
                )
            else:
                # Aunque no acierte la zona, conserva una pequeña posibilidad
                # de atajar por reflejos o reacción.
                save_probability = min(
                    12.0,
                    max(3.0, 5.0 + effects["keeper_bonus"] * 0.25),
                )

            # Evita que la suma de probabilidades supere el 100 %.
            save_probability = min(
                save_probability,
                max(0.0, 100.0 - miss_probability),
            )
            goal_probability = max(
                0.0,
                100.0 - save_probability - miss_probability,
            )

            roll = random.random() * 100
            if roll < miss_probability:
                outcome = "FALLADO"
            elif roll < miss_probability + save_probability:
                outcome = "ATAJADA"
            else:
                outcome = "GOL"

            selected_label = (
                f"Zona elegida por el arquero: "
                f"{NOMBRES[keeper_zone]} ({keeper_zone})"
            )
            action_detail = (
                f"El pateador disparó a "
                f"{NOMBRES[shot_zone]} ({shot_zone})."
            )

            prediction_hit = recommended_zone == shot_zone
            followed_recommendation = keeper_zone == recommended_zone

            if same_zone:
                comparison = (
                    "✓ El arquero cubrió la misma zona del disparo. "
                    "La decisión coincidió con la jugada simulada."
                )
            elif followed_recommendation:
                comparison = (
                    f"Seguiste la mejor recomendación estadística, pero en "
                    f"esta jugada el pateador disparó a "
                    f"{NOMBRES[shot_zone]} ({shot_zone}). La predicción indica "
                    f"la zona más conveniente para cubrir, pero no garantiza "
                    f"el resultado de un solo penal."
                )
            elif prediction_hit:
                comparison = (
                    f"La predicción sí anticipó el disparo en "
                    f"{NOMBRES[recommended_zone]} ({recommended_zone}), pero "
                    f"el arquero eligió {NOMBRES[keeper_zone]} ({keeper_zone})."
                )
            else:
                comparison = (
                    f"El arquero eligió {NOMBRES[keeper_zone]} ({keeper_zone}) "
                    f"y el pateador disparó a "
                    f"{NOMBRES[shot_zone]} ({shot_zone})."
                )

            animation_shot = shot_zone
            animation_keeper = keeper_zone
            estimated_value = shot_probability
            rank_probs = distribution

            self.context["manual_keeper_zone"] = keeper_zone
            self.context["manual_shot_zone"] = shot_zone

        else:
            # El usuario decide hacia dónde dispara el pateador.
            shot_zone = chosen_zone
            keeper_zone = self.weighted_zone(self.keeper_zone_probs)
            shot_probability = float(
                self.player_zone_probs.get(shot_zone, 0.0)
            )
            keeper_probability = float(
                self.keeper_zone_probs.get(keeper_zone, 0.0)
            )
            same_zone = shot_zone == keeper_zone

            max_player = max(self.player_zone_probs.values()) or 1.0
            player_strength = shot_probability / max_player

            miss_probability = (
                15.0
                - 9.0 * player_strength
                + effects["miss_bonus"]
                - effects["player_bonus"]
            )
            miss_probability = min(45.0, max(4.0, miss_probability))

            if same_zone:
                save_probability = min(
                    78.0,
                    42.0
                    + keeper_probability * 0.55
                    + effects["keeper_bonus"],
                )
            else:
                # El arquero aún puede reaccionar aunque haya elegido otra zona.
                save_probability = min(
                    12.0,
                    max(3.0, 4.0 + effects["keeper_bonus"] * 0.25),
                )

            save_probability = min(
                save_probability,
                max(0.0, 100.0 - miss_probability),
            )
            goal_probability = max(
                0.0,
                100.0 - save_probability - miss_probability,
            )

            roll = random.random() * 100
            if roll < miss_probability:
                outcome = "FALLADO"
            elif roll < miss_probability + save_probability:
                outcome = "ATAJADA"
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

            followed_recommendation = shot_zone == recommended_zone

            if same_zone:
                comparison = (
                    "El arquero cubrió la misma zona del disparo."
                )
            elif followed_recommendation:
                comparison = (
                    "✓ El disparo siguió la recomendación y evitó la zona "
                    "elegida por el arquero en esta jugada."
                )
            else:
                comparison = (
                    "El disparo evitó la zona del arquero, aunque no siguió "
                    "la recomendación principal del sistema."
                )

            animation_shot = shot_zone
            animation_keeper = keeper_zone
            estimated_value = shot_probability
            rank_probs = self.player_zone_probs

            self.context["manual_shot_zone"] = shot_zone
            self.context["manual_keeper_zone"] = keeper_zone

        ranking = sorted(
            rank_probs.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        rank = next(
            i + 1
            for i, (zone, _) in enumerate(ranking)
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
            f"{action_detail}\n"
            f"Probabilidad estimada de esa zona: {estimated_value:.1f}%"
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

        followed_system = (
            mode == "arquero" and chosen_zone == recommended_zone
        ) or (
            mode == "pateador" and shot_zone == recommended_zone
        )

        if followed_system:
            self.sim_tree_match.setStyleSheet(
                "font-size:16px;font-weight:800;color:#55f39a;"
            )
            self.sim_tree_match.setText(
                "✓ Seguiste la recomendación estadística del sistema.\n"
                f"{comparison}"
            )
        else:
            self.sim_tree_match.setStyleSheet(
                "font-size:16px;font-weight:800;color:#ffca56;"
            )
            self.sim_tree_match.setText(
                "No seguiste la recomendación principal.\n"
                f"{comparison}"
            )

        self.sim_field.play(
            animation_shot,
            animation_keeper,
            outcome,
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
    app.setApplicationName("Penalty Shootout Predictor")
    app.setStyle("Fusion")

    estilo = cargar_estilo()
    app.setStyleSheet(estilo)

    window = PenaltyVisionApp()
    window.showMaximized()
    sys.exit(app.exec())