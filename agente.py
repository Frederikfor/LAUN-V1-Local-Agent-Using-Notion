"""
Loop principal del agente: conecta búsqueda en memoria, validación de esa
memoria por el LLM (usarla solo si de verdad responde la pregunta), el
filtro de calidad para decidir qué guardar, y el registro de métricas.

Este es el archivo que uniría todas las piezas construidas hasta ahora:
notion_utils, buscar_memoria, guardar_memoria, filtro_calidad, llm_utils
y metricas.
"""

from datetime import datetime

from buscar_memoria import buscar_en_memoria
from guardar_memoria import guardar_entrada
from filtro_calidad import evaluar_para_memoria
from llm_utils import llamar_llm
import metricas


SYSTEM_PROMPT_AGENTE = """Eres un asistente honesto y calibrado.

Regla de oro: es mucho mejor decir "no tengo información confiable sobre
esto" cuando no tengas evidencia clara, que inventar una respuesta que
suene segura pero sea falsa. Afirmar algo incorrecto con confianza es el
peor resultado posible. Admitir que no sabes algo es un resultado bueno
y aceptable. Responder correctamente con evidencia real es el mejor
resultado.

No tienes acceso a internet ni a herramientas externas — solo a tu
conocimiento entrenado y a los datos verificados que se te den
explícitamente en el mensaje (como la fecha/hora actual, cuando aplique).
Si te preguntan algo que requiere información en tiempo real que no se
te dio explícitamente, dilo claramente en vez de adivinar.

Importante: esta regla de calibración aplica SOLO cuando te preguntan
directamente por un hecho verificable (fechas, datos, eventos, etc.).
Si el usuario comparte una opinión, preferencia, o algo sobre sí mismo
(no una pregunta), simplemente reconócelo de forma natural y conversacional
— no apliques la duda ni pidas evidencia sobre afirmaciones que la persona
hace sobre su propia vida o gustos.
"""


def _fecha_hora_actual() -> str:
    """Devuelve la fecha y hora reales del sistema, en español, para
    inyectarlas como hecho verificado en cada consulta. El LLM local no
    tiene reloj propio ni acceso a internet — sin esto, adivina (alucina)
    la fecha en vez de admitir que no la sabe."""
    ahora = datetime.now()
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    return f"{dias[ahora.weekday()]} {ahora.strftime('%d/%m/%Y, %H:%M')}"


def responder(pregunta: str) -> str:
    """Genera una respuesta a la pregunta, usando memoria previa cuando
    aplica, y decide si vale la pena recordar esta interacción."""
    contexto_temporal = f"[Dato verificado: hoy es {_fecha_hora_actual()}]\n\n"
    candidato = buscar_en_memoria(pregunta)

    if candidato is None:
        metricas.registrar_miss()
        respuesta = llamar_llm(contexto_temporal + pregunta, system=SYSTEM_PROMPT_AGENTE)
    else:
        metricas.registrar_hit()
        contexto_texto = "\n".join(
            f"- [{c['contexto']}] {c['definicion']}" for c in candidato["contextos"]
        )
        prompt = (
            f"{contexto_temporal}"
            f"Tengo esta información previamente guardada sobre "
            f"'{candidato['concepto']}':\n{contexto_texto}\n\n"
            f"Pregunta actual del usuario: {pregunta}\n\n"
            "Si la información de arriba responde bien la pregunta, úsala "
            "para responder de forma natural. Si NO aplica a lo que se "
            "pregunta (por ejemplo, es una definición pero la pregunta pide "
            "otra cosa, como una lista o un proceso), ignórala por completo "
            "y responde con tu propio conocimiento, sin mencionar que había "
            "información guardada que no servía."
        )
        respuesta = llamar_llm(prompt, system=SYSTEM_PROMPT_AGENTE)

    # Filtro de calidad: decide si esta interacción vale la pena recordar
    resultado_filtro = evaluar_para_memoria(pregunta, respuesta)
    if resultado_filtro:
        guardar_entrada(
            concepto=resultado_filtro["concepto"],
            contexto=resultado_filtro["contexto"],
            definicion=resultado_filtro["definicion"],
            confianza=resultado_filtro["confianza"],
            fuente="agente",
        )

    return respuesta


if __name__ == "__main__":
    print("Agente con memoria en Notion — escribe 'salir' para terminar.\n")

    while True:
        pregunta = input("Tú: ").strip()
        if pregunta.lower() in {"salir", "exit", "quit"}:
            break
        if not pregunta:
            continue

        respuesta = responder(pregunta)
        print(f"Agente: {respuesta}\n")

    print("\n" + metricas.reporte())