"""
Funciones compartidas de acceso a Notion, usadas tanto por guardar_memoria.py
como por buscar_memoria.py. Centralizar esto evita duplicar lógica de
conexión y extracción de datos en cada script nuevo.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATA_SOURCE_ID = os.getenv("NOTION_DATA_SOURCE_ID")
NOTION_VERSION = "2025-09-03"

if not NOTION_TOKEN or not NOTION_DATA_SOURCE_ID:
    raise ValueError("Falta NOTION_TOKEN o NOTION_DATA_SOURCE_ID en tu archivo .env.")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def obtener_todas_las_filas() -> list[dict]:
    """Trae todas las filas del data source, manejando paginación."""
    filas = []
    payload = {}
    while True:
        respuesta = requests.post(
            f"https://api.notion.com/v1/data_sources/{NOTION_DATA_SOURCE_ID}/query",
            headers=HEADERS,
            json=payload,
        )
        respuesta.raise_for_status()
        data = respuesta.json()
        filas.extend(data["results"])
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return filas


def extraer_texto(fila: dict, propiedad: str) -> str:
    """Extrae el texto plano de una propiedad tipo title o rich_text."""
    prop = fila.get("properties", {}).get(propiedad, {})
    tipo = prop.get("type")
    contenido = prop.get(tipo, [])
    if not isinstance(contenido, list):
        return ""
    return "".join(bloque["plain_text"] for bloque in contenido)


def extraer_tags(fila: dict) -> list[str]:
    """Extrae los nombres de la columna Tags (multi_select) de una fila."""
    tags_prop = fila.get("properties", {}).get("Tags", {}).get("multi_select", [])
    return [t["name"] for t in tags_prop]


def buscar_concepto_exacto(nombre_concepto: str) -> dict | None:
    """Busca una fila cuyo título (columna Pregunta/Concepto) coincida
    exactamente con el nombre dado, sin distinguir mayúsculas/minúsculas.
    Se usa para decidir si un concepto ya existe antes de crear una fila
    duplicada (lógica de upsert)."""
    nombre_normalizado = nombre_concepto.strip().lower()
    for fila in obtener_todas_las_filas():
        titulo = extraer_texto(fila, "Pregunta").strip().lower()
        if titulo == nombre_normalizado:
            return fila
    return None