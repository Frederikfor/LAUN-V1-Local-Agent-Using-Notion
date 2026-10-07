"""
Smoke test: verifica que la conexión con Notion funciona antes de construir
el resto del agente. Si esto falla, el problema está en el token, el
database ID, o en que la página no está compartida con la integración.
"""

import os
import requests
from dotenv import load_dotenv
from notion_client import Client

NOTION_VERSION = "2025-09-03"

# Carga las variables de entorno desde el archivo .env
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_TOKEN or not NOTION_DATABASE_ID:
    raise ValueError(
        "Falta NOTION_TOKEN o NOTION_DATABASE_ID en tu archivo .env. "
        "Revisa que el archivo .env esté en la misma carpeta que este script."
    )

# Inicializa el cliente de Notion con tu token
notion = Client(auth=NOTION_TOKEN)

def probar_conexion():
    """Intenta leer la estructura de la database para confirmar que
    el token y el ID son correctos, y que la integración tiene acceso.

    Desde la versión 2025-09-03 de la API de Notion, las columnas
    (properties) ya no viven directo en la database: hay que obtener
    primero el 'data source' hijo de la database, y leer las columnas
    desde ahí."""
    try:
        database = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
    except Exception as e:
        print("❌ Error al conectar con Notion.")
        print(f"   Detalle: {e}")
        print("\nRevisa esto:")
        print("  1. ¿El NOTION_DATABASE_ID es correcto (sin el ?v=...)?")
        print("  2. ¿Agregaste tu integración en 'Add connections' de esa página?")
        print("  3. ¿El token empieza con 'secret_' o 'ntn_' y está completo?")
        return

    titulo = database.get("title", [{}])
    nombre_db = titulo[0]["plain_text"] if titulo else "(sin título)"

    print("✅ Conexión exitosa con Notion.")
    print(f"   Database encontrada: '{nombre_db}'")

    # Paso 2: obtener el data source hijo de esta database
    data_sources = database.get("data_sources", [])
    if not data_sources:
        print("⚠️  Esta database no tiene data sources visibles todavía.")
        print("   Prueba agregar al menos una fila/entrada manualmente en Notion y vuelve a correr el script.")
        return

    data_source_id = data_sources[0]["id"]

    respuesta = requests.get(
        f"https://api.notion.com/v1/data_sources/{data_source_id}",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
        },
    )
    respuesta.raise_for_status()
    data_source = respuesta.json()

    print(f"\n   Data source ID (guárdalo, lo necesitarás luego): {data_source_id}")
    print("\n   Columnas (properties) detectadas:")
    for nombre_propiedad, detalles in data_source["properties"].items():
        print(f"     - {nombre_propiedad} ({detalles['type']})")


if __name__ == "__main__":
    probar_conexion()