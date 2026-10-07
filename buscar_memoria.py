"""
Función de lectura: busca en la memoria de Notion el concepto más parecido
a una consulta nueva, usando coincidencia de palabras clave con stemming
(NLTK). Si el concepto encontrado tiene más de un contexto guardado
(ej. "Color" en Diseño gráfico Y en Teoría musical), lo marca como
ambiguo — la resolución de esa ambigüedad (preguntarle al usuario cuál
contexto aplica) es responsabilidad del agente que llama a esta función,
no de la búsqueda en sí.
"""

import re
import json
from nltk.stem.snowball import SnowballStemmer

from notion_utils import obtener_todas_las_filas, extraer_texto, extraer_tags

_stemmer = SnowballStemmer("spanish")

STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "en", "un", "una", "y", "o",
    "que", "es", "como", "cómo", "para", "por", "se", "con", "a", "su",
}


def _palabras_clave(texto: str) -> set[str]:
    """Convierte un texto en un set de raíces (stems) de palabras clave,
    ignorando stopwords y puntuación."""
    palabras = re.findall(r"[a-záéíóúñ0-9]+", texto.lower())
    contenido = [p for p in palabras if p not in STOPWORDS and len(p) > 2]
    return {_stemmer.stem(p) for p in contenido}


def _parsear_contextos(fila: dict) -> list[dict]:
    """Extrae la lista de contextos (JSON) guardada en la columna Resumen.
    Si el campo está vacío o corrupto, devuelve una lista vacía en vez
    de fallar — un concepto sin contextos legibles simplemente no compite
    por la mejor coincidencia."""
    resumen_raw = extraer_texto(fila, "Resumen")
    if not resumen_raw:
        return []
    try:
        return json.loads(resumen_raw)
    except json.JSONDecodeError:
        return []


def buscar_en_memoria(consulta: str, umbral_minimo: int = 3, debug: bool = False) -> dict | None:
    """Busca el concepto más parecido a la consulta.

    Returns:
        None si no hay nada suficientemente parecido, o un dict:
        {
            "concepto": str,
            "contextos": list[dict],   # todos los contextos guardados
            "ambiguo": bool,           # True si hay más de un contexto
            "tags": list[str],
            "coincidencias": int,
        }
    """
    palabras_consulta = _palabras_clave(consulta)
    filas = obtener_todas_las_filas()

    mejor_fila = None
    mejor_contextos: list[dict] = []
    mejor_puntaje = 0

    for fila in filas:
        concepto = extraer_texto(fila, "Pregunta")
        contextos = _parsear_contextos(fila)

        palabras_nombre = _palabras_clave(concepto)
        texto_contenido = " ".join(
            f"{c.get('contexto', '')} {c.get('definicion', '')}" for c in contextos
        )
        palabras_contenido = _palabras_clave(texto_contenido)

        # Coincidir con el NOMBRE del concepto pesa más que coincidir con
        # el contenido de sus definiciones: si alguien pregunta "¿qué es
        # el color?", eso debe encontrar el concepto "Color" aunque la
        # pregunta no comparta ninguna otra palabra con las definiciones.
        puntaje = 3 * len(palabras_consulta & palabras_nombre) + len(palabras_consulta & palabras_contenido)

        if debug:
            print(f"[debug] '{concepto}' -> coincidencias ponderadas: {puntaje}")

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_fila = fila
            mejor_contextos = contextos

    if mejor_fila is None or mejor_puntaje < umbral_minimo:
        return None

    return {
        "concepto": extraer_texto(mejor_fila, "Pregunta"),
        "contextos": mejor_contextos,
        "ambiguo": len(mejor_contextos) > 1,
        "tags": extraer_tags(mejor_fila),
        "coincidencias": mejor_puntaje,
    }


if __name__ == "__main__":
    resultado = buscar_en_memoria("¿qué es el color?", debug=True)

    if resultado is None:
        print("❌ No se encontró nada suficientemente parecido en la memoria.")
    else:
        print(f"\n✅ Concepto encontrado: '{resultado['concepto']}'")
        if resultado["ambiguo"]:
            print("⚠️  Ambiguo: hay más de un contexto guardado para este concepto.")
        for c in resultado["contextos"]:
            print(f"   [{c['contexto']}] {c['definicion']} (fuente: {c['fuente']}, confianza: {c['confianza']})")