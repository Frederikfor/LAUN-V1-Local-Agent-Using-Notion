"""
Filtro de calidad: decide si una interacción (pregunta + respuesta) contiene
conocimiento reutilizable que vale la pena guardar en la memoria de Notion,
y si es así, la destila a la estructura que guardar_memoria.py necesita.

Este es el control de calidad en el origen (Poka-Yoke) que evita que la
memoria se contamine con conversaciones triviales o de baja confianza.
"""

import json
import re

from llm_utils import llamar_llm

SYSTEM_PROMPT = """Eres un filtro de calidad para una memoria de un agente de IA.

Tu única tarea es decidir si una interacción (pregunta + respuesta) contiene
conocimiento GENERAL y REUTILIZABLE en el futuro (una definición, un
concepto, un hecho estable) — NO conversación casual, NO saludos, NO
algo específico de un momento puntual que no se repetirá.

Responde UNICAMENTE con un objeto JSON válido (sin coma después del
último campo), sin explicaciones, sin markdown, sin texto antes o después.

Ejemplo 1 — SI vale la pena guardar:
Pregunta: "¿Cómo se autentica una integración interna de Notion?"
Respuesta: "Se usa un token estático, no OAuth."
Salida:
{"guardar": true, "concepto": "Autenticacion Notion", "contexto": "APIs", "definicion": "Las integraciones internas de Notion usan un token estatico en vez de OAuth.", "confianza": "Alta"}

Ejemplo 2 — NO vale la pena guardar (saludo/conversación casual):
Pregunta: "hola, ¿cómo estás?"
Respuesta: "¡Muy bien, gracias! ¿En qué te puedo ayudar hoy?"
Salida:
{"guardar": false}

Ejemplo 3 — NO vale la pena guardar (algo puntual, no reutilizable):
Pregunta: "recuérdame comprar leche hoy"
Respuesta: "Listo, anotado."
Salida:
{"guardar": false}

Ejemplo 4 — NO vale la pena guardar (el agente hablando sobre sí mismo, sus reglas o su propio comportamiento, no conocimiento del mundo):
Pregunta: "¿qué haces cuando no sabes algo?"
Respuesta: "Prefiero admitir que no sé algo antes que inventar una respuesta."
Salida:
{"guardar": false}

Ahora evalúa la siguiente interacción con el mismo criterio.
"""


def _extraer_json(texto: str) -> dict | None:
    """Intenta extraer un objeto JSON de la respuesta del modelo, incluso
    si viene envuelto en markdown, con texto alrededor, o con comas
    sobrantes antes de un '}' o ']' — un error común de modelos pequeños
    que mezclan la sintaxis de un dict de Python con JSON estricto."""
    texto = texto.strip()
    texto = re.sub(r"^```(json)?|```$", "", texto, flags=re.MULTILINE).strip()
    texto = re.sub(r",\s*([}\]])", r"\1", texto)

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def evaluar_para_memoria(pregunta: str, respuesta: str) -> dict | None:
    """Evalúa si una interacción vale la pena guardar en la memoria.

    Returns:
        None si no vale la pena guardar, o un dict con
        {"concepto", "contexto", "definicion", "confianza"} listo para
        pasarle a guardar_entrada() de guardar_memoria.py.
    """
    prompt = f"Pregunta del usuario: {pregunta}\n\nRespuesta del agente: {respuesta}"

    salida_cruda = llamar_llm(prompt, system=SYSTEM_PROMPT, temperatura=0.0)
    resultado = _extraer_json(salida_cruda)

    if resultado is None:
        print(f"⚠️  El filtro no devolvió JSON válido. Salida cruda:\n{salida_cruda}")
        return None

    if not resultado.get("guardar", False):
        return None

    campos_requeridos = {"concepto", "contexto", "definicion", "confianza"}
    if not campos_requeridos.issubset(resultado.keys()):
        print(f"⚠️  El filtro devolvió JSON incompleto: {resultado}")
        return None

    return {
        "concepto": resultado["concepto"],
        "contexto": resultado["contexto"],
        "definicion": resultado["definicion"],
        "confianza": resultado["confianza"],
    }


if __name__ == "__main__":
    print("--- Caso 1: debería guardar (conocimiento reutilizable) ---")
    resultado = evaluar_para_memoria(
        pregunta="¿Cómo se autentica una integración interna de Notion?",
        respuesta="Se usa un token estático (Internal Integration Secret), no OAuth. "
                  "El token va en el header Authorization: Bearer.",
    )
    print(resultado)

    print("\n--- Caso 2: NO debería guardar (conversación casual) ---")
    resultado = evaluar_para_memoria(
        pregunta="hola, ¿cómo estás?",
        respuesta="¡Muy bien, gracias! ¿En qué te puedo ayudar hoy?",
    )
    print(resultado)