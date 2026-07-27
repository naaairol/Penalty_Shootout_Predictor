from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

# --- RUTAS BASE Y CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent

POSIBLES_CSV = [
    BASE_DIR / "penales_jugadores.csv",
    BASE_DIR / "datos" / "penales_jugadores.csv",
]
CSV_PATH = next((ruta for ruta in POSIBLES_CSV if ruta.exists()), POSIBLES_CSV[0])
ARQUEROS_CSV_PATH = BASE_DIR / "penales_arqueros.csv"
SIMULACIONES_PREDETERMINADAS = 2000

QSS_PATH = BASE_DIR / "estilos" / "estilos.qss"

# --- RUTAS DE MULTIMEDIA ---
IMG_DIR = BASE_DIR / "imagenes"
LOGOS_DIR = IMG_DIR / "logos"
PLAYERS_DIR = IMG_DIR / "Imagenes jugadores"
KEEPERS_DIR = IMG_DIR / "Imagenes arqueros"
STADIUMS_DIR = IMG_DIR / "estadios"
SIM_DIR = IMG_DIR / "simulacion"

HOME = Path.home()
ONEDRIVE = Path(os.environ.get("OneDrive", HOME / "OneDrive"))

EXTERNAL_IMAGE_ROOTS = [
    HOME / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes jugadores",
    HOME / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes arqueros",
    ONEDRIVE / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes jugadores",
    ONEDRIVE / "Documents" / "Tercer Semestre" / "EDA" / "Imagenes arqueros",
]

# --- ESTRUCTURAS DE DATOS ---
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
    "España": "espana.png",
}

ARQUEROS_RESPALDO = {
    "Argentina": ["Emiliano Martínez"],
    "España": ["David Raya", "Joan García", "Unai Simón"],
}


# --- FUNCIONES DE ESTILO Y TEXTO ---
def cargar_estilo() -> str:
    """Carga la hoja de estilo desde el archivo externo .qss."""
    if QSS_PATH.exists():
        try:
            return QSS_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error al cargar archivo de estilos: {e}")
    return ""


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


# --- BÚSQUEDA Y MANEJO DE IMÁGENES ---
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
    """Busca el archivo de imagen de un estadio en imagenes/estadios."""
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