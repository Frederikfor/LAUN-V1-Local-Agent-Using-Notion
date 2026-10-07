"""
Función de escritura (upsert): guarda o actualiza un concepto en la
memoria de Notion. Cada concepto puede tener varios "contextos" (ej.
"Color" en Diseño gráfico vs. en Teoría musical), almacenados como una
lista de objetos JSON dentro de la columna Resumen. Nunca se sobrescribe
un contexto existente con datos de otro contexto distinto.
"""

import json
from datetime import date
import requests

from notion_utils import (
    HEADERS,
    NOTION_DATA_SOURCE_ID,
    buscar_concepto_exacto,
    extraer_texto,
    extraer_tags,
)


def guardar_entrada(
    concepto: str,
    contexto: str,
    definicion: str,
    confianza: str = "Media",
    fuente: str = "agente",
) -> dict:
    """Guarda o actualiza un concepto en la memoria.

    Args:
        concepto: nombre del concepto, ej. "Color".
        contexto: dominio/contexto de esta definición, ej. "Diseño gráfico".
        definicion: la definición o resumen para ese contexto.
        confianza: "Alta", "Media" o "Baja" — qué tan seguro está el agente.
        fuente: "agente" (auto-interpretado) o "usuario" (afirmado
                explícitamente por el usuario). Distinguir esto permite
                en el futuro confiar más en lo que el usuario dijo directo.

    Comportamiento:
        - Si el concepto no existe: crea una fila nueva con un solo contexto.
        - Si el concepto existe y el contexto es nuevo: agrega el bloque
          sin tocar los contextos anteriores.
        - Si el concepto y el contexto ya existen: actualiza SOLO ese
          bloque (la definición se considera corregida/mejorada).
    """
    fila_existente = buscar_concepto_exacto(concepto)
    hoy = date.today().isoformat()

    nuevo_bloque = {
        "contexto": contexto,
        "definicion": definicion,
        "confianza": confianza,
        "fuente": fuente,
        "actualizado": hoy,
    }

    if fila_existente is None:
        contextos = [nuevo_bloque]
        tags = [contexto]
        page_id = None
    else:
        page_id = fila_existente["id"]
        resumen_actual = extraer_texto(fila_existente, "Resumen")
        try:
            contextos = json.loads(resumen_actual) if resumen_actual else []
        except json.JSONDecodeError:
            contextos = []

        reemplazado = False
        for bloque in contextos:
            if bloque.get("contexto", "").strip().lower() == contexto.strip().lower():
                bloque.update(nuevo_bloque)
                reemplazado = True
                break
        if not reemplazado:
            contextos.append(nuevo_bloque)

        tags = extraer_tags(fila_existente)
        if contexto not in tags:
            tags.append(contexto)

    properties = {
        "Pregunta": {"title": [{"text": {"content": concepto}}]},
        "Resumen": {"rich_text": [{"text": {"content": json.dumps(contextos, ensure_ascii=False)}}]},
        "Tags": {"multi_select": [{"name": t} for t in tags]},
        "Fecha": {"date": {"start": hoy}},
    }

    if page_id is None:
        respuesta = requests.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json={
                "parent": {"type": "data_source_id", "data_source_id": NOTION_DATA_SOURCE_ID},
                "properties": properties,
            },
        )
        accion = "creado"
    else:
        respuesta = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=HEADERS,
            json={"properties": properties},
        )
        accion = "actualizado"

    if respuesta.status_code != 200:
        print(f"❌ Error al guardar '{concepto}'.")
        print(f"   Detalle: {respuesta.json()}")
        respuesta.raise_for_status()

    print(f"✅ Concepto '{concepto}' {accion} (contexto: '{contexto}').")
    return respuesta.json()


if __name__ == "__main__":
    # Prueba: dos contextos distintos para el mismo concepto ("Color"),
    # exactamente el caso de ambigüedad que motivó este rediseño.
    guardar_entrada(
        concepto="Color",
        contexto="Diseño gráfico",
        definicion="El color es la percepción visual producida por la longitud de onda de la luz reflejada.",
        confianza="Alta",
        fuente="agente",
    )
    guardar_entrada(
        concepto="Color",
        contexto="Teoría musical",
        definicion="El color se refiere al timbre distintivo de un instrumento o voz.",
        confianza="Media",
        fuente="agente",
    )