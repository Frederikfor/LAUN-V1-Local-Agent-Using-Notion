"""
Registro simple de métricas: cuántas veces el agente encontró un candidato
en memoria (hit) vs. cuántas veces no encontró nada (miss). Persiste en un
archivo local — no necesita vivir en Notion, es un dato de desarrollo, no
de negocio.
"""

import json
import os

ARCHIVO_METRICAS = "metricas.json"


def _cargar() -> dict:
    if not os.path.exists(ARCHIVO_METRICAS):
        return {"hits": 0, "misses": 0}
    with open(ARCHIVO_METRICAS, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar(datos: dict) -> None:
    with open(ARCHIVO_METRICAS, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def registrar_hit() -> None:
    datos = _cargar()
    datos["hits"] += 1
    _guardar(datos)


def registrar_miss() -> None:
    datos = _cargar()
    datos["misses"] += 1
    _guardar(datos)


def reporte() -> str:
    datos = _cargar()
    total = datos["hits"] + datos["misses"]
    if total == 0:
        return "Todavía no hay datos suficientes para calcular el cache hit rate."
    porcentaje = (datos["hits"] / total) * 100
    return (
        f"Cache hit rate: {porcentaje:.1f}% "
        f"({datos['hits']} hits / {total} consultas totales)"
    )


if __name__ == "__main__":
    print(reporte())