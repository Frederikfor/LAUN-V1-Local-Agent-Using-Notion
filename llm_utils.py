"""
Módulo compartido para hablar con un modelo local vía Ollama.
Centraliza la conexión igual que notion_utils.py centraliza Notion —
si mañana cambias de modelo o de proveedor (Claude, OpenAI), solo tocas
este archivo, nada más en el proyecto se entera del cambio.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_URL = "http://localhost:11434/api/chat"


def llamar_llm(prompt: str, system: str | None = None, temperatura: float = 0.3) -> str:
    """Envía un prompt al modelo local y devuelve su respuesta como texto.

    Args:
        prompt: el mensaje del usuario/instrucción.
        system: instrucción de sistema opcional (rol, reglas, formato esperado).
        temperatura: qué tan creativo/aleatorio es el modelo (0 = más
                     determinista, útil cuando esperamos JSON estructurado).

    Returns:
        El texto de la respuesta del modelo.
    """
    mensajes = []
    if system:
        mensajes.append({"role": "system", "content": system})
    mensajes.append({"role": "user", "content": prompt})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": mensajes,
        "stream": False,
        "options": {"temperature": temperatura},
    }

    try:
        respuesta = requests.post(OLLAMA_URL, json=payload, timeout=60)
        respuesta.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "No se pudo conectar con Ollama. ¿Está corriendo? "
            "Verifica con: ollama list"
        )

    data = respuesta.json()
    return data["message"]["content"]


if __name__ == "__main__":
    # Smoke test: confirma que Ollama responde antes de construir nada encima.
    print(f"Probando conexión con el modelo: {OLLAMA_MODEL}")
    respuesta = llamar_llm("Responde solo con la palabra: listo")
    print(f"✅ Respuesta del modelo: {respuesta}")