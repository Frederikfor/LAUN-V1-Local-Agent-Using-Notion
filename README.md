# LAUN — Local Agent Using Notion

Agente conversacional que corre sobre un modelo de lenguaje local (**Qwen2.5 1.5B**, vía **Ollama**) y usa **Notion como memoria externa persistente**, para que el conocimiento sobreviva entre sesiones sin depender de servicios de pago ni de reentrenar el modelo.

En términos de arquitectura: es un **RAG básico con memoria auto-alimentada y recuperación léxica** (palabras clave + stemming, no embeddings), diseñado deliberadamente así para poder migrar a búsqueda semántica más adelante solo si los datos reales lo justifican (metodología Lean/MVP).

> **Resumen de una línea (para CV/portfolio):**
> *Built a local RAG-style agent in Python using Qwen via Ollama, with Notion as persistent memory. The agent decides what to remember, storing context-specific definitions to avoid ambiguity across domains.*

---

## 1. Objetivo del proyecto

Los agentes basados en LLM gratuitos o locales tienen memoria limitada al contexto de una sola conversación: al cerrar la sesión, todo lo discutido se pierde. Este proyecto construye un agente que:

1. Antes de responder desde cero, **consulta su memoria en Notion**.
2. Si encuentra algo parecido, se lo pasa al LLM como contexto y **el propio LLM decide si realmente sirve** para responder la pregunta actual (no se responde directo con la memoria encontrada).
3. Si la respuesta generada contiene conocimiento reutilizable, un **filtro de calidad** decide si vale la pena guardarla.
4. Con el tiempo, la base de Notion crece y el **cache hit rate** (métrica medida) debería subir — esa es la evidencia de que el agente "aprende" con el uso.

La meta final es un MVP de punta a punta que demuestre, con métricas reales, que la memoria externa mejora las respuestas de un modelo pequeño y gratuito con el tiempo.

**Fuera de alcance (deliberadamente, por ahora):** embeddings/base vectorial, interfaz gráfica, autenticación multiusuario/OAuth, ingesta de documentos externos (PDFs, webs).

---

## 2. Cómo funciona (flujo end-to-end)

```
Usuario → agente.py
             │
             ├─ 1. buscar_memoria.py: ¿hay un concepto parecido en Notion?
             │      (coincidencia de palabras clave con stemming, puntaje
             │       ponderado: nombre del concepto pesa 3x, contenido 1x)
             │
             ├─ 2a. Si hay candidato → se pasa como contexto al LLM junto
             │       con la pregunta. El LLM decide si de verdad aplica;
             │       si no aplica, lo ignora en silencio (evita falsos
             │       positivos, ej. "Color" en diseño vs. en música).
             ├─ 2b. Si no hay candidato → el LLM responde desde cero.
             │
             ├─ 3. filtro_calidad.py: ¿esta interacción contiene
             │       conocimiento general reutilizable? (few-shot prompt,
             │       temperatura 0.0, salida JSON estricta)
             │
             ├─ 4. Si sí → guardar_memoria.py hace upsert en Notion:
             │       crea el concepto si no existe, o agrega/actualiza
             │       solo el bloque de contexto correspondiente (nunca
             │       sobrescribe contextos distintos del mismo concepto).
             │
             └─ 5. metricas.py registra hit/miss → cache hit rate.
```

### Esquema de datos en Notion

| Columna    | Tipo           | Contenido |
|------------|----------------|-----------|
| `Pregunta` | title          | Nombre del **concepto** (ej. `"Color"`), no una pregunta completa. |
| `Resumen`  | rich_text      | Lista JSON de bloques, uno por contexto/dominio: `[{"contexto": "Diseño gráfico", "definicion": "...", "confianza": "Alta", "fuente": "agente", "actualizado": "2026-09-19"}]` |
| `Tags`     | multi_select   | Dominios/contextos ya conocidos para ese concepto (permite saber si ya existe un contexto sin parsear todo `Resumen`). |
| `Fecha`    | date           | Última vez que se tocó la fila. |

El campo `fuente` (`"agente"` vs `"usuario"`) distingue si la definición fue auto-interpretada o afirmada directamente por el usuario — pensado para, en el futuro, confiar más en lo que el usuario confirmó explícitamente. El JSON nunca se expone al usuario tal cual; el agente siempre lo traduce a lenguaje natural.

---

## 3. Estructura del código

| Archivo | Rol | Estado |
|---|---|---|
| `notion_utils.py` | Acceso compartido a la API de Notion: leer todas las filas (con paginación), extraer texto/tags, buscar un concepto exacto. | ✅ Completo |
| `buscar_memoria.py` | Búsqueda por palabras clave con stemming (NLTK `SnowballStemmer` español). Detecta ambigüedad (un concepto con &gt;1 contexto). | ✅ Completo |
| `guardar_memoria.py` | Upsert en Notion: crea el concepto si no existe; si existe, agrega o actualiza solo el bloque de contexto correspondiente. | ✅ Completo |
| `filtro_calidad.py` | Few-shot prompt que decide si una interacción vale la pena guardar y la destila a `{concepto, contexto, definicion, confianza}`. Parser tolerante a JSON mal formado (comas sobrantes, markdown). | ✅ Completo |
| `llm_utils.py` | Cliente del LLM local vía Ollama (`qwen2.5:1.5b` por defecto, configurable con `OLLAMA_MODEL`). Único punto de contacto con el modelo — si se cambia de proveedor (Claude/OpenAI), solo se toca este archivo. | ✅ Completo |
| `agente.py` | Loop principal: conecta búsqueda → validación por el LLM → filtro de calidad → escritura → métricas. Incluye system prompt de calibración de confianza (prefiere decir "no sé" antes que alucinar) e inyección de fecha/hora real del sistema. | ✅ Completo, pero **sin memoria de corto plazo** (ver sección 5) |
| `metricas.py` | Registra hits/misses en `metricas.json` local y calcula el cache hit rate. | ✅ Completo |
| `test_notion_connection.py` | Smoke test: valida token/IDs y lista las columnas reales detectadas en Notion. | ✅ Completo |
| `bitacora.md` | 16 hallazgos reales documentados (bugs, limitaciones de diseño, decisiones), cada uno con causa raíz y aprendizaje. | ✅ Vivo — se sigue agregando |
| `plan_de_proyecto.md` | Documento de planeación original (problema, alcance, opciones evaluadas, roadmap). | ✅ Referencia |
| `requirements.txt` | — | ❌ No existe todavía |

---

## 4. Instalación y uso

### Prerrequisitos

1. **Python 3.12+**
2. **[Ollama](https://ollama.com/)** instalado y corriendo localmente, con el modelo descargado:
   ```bash
   ollama pull qwen2.5:1.5b
   ```
3. Una **integración interna de Notion** (token estático, no OAuth) con acceso a una database con las columnas `Pregunta` (title), `Resumen` (rich_text), `Tags` (multi_select) y `Fecha` (date).

### Dependencias de Python

No hay `requirements.txt` todavía (ver sección 5). Instalar manualmente:

```bash
python -m pip install requests python-dotenv nltk notion-client
```

> En Windows, si hay más de un intérprete de Python instalado, usar siempre `python -m pip install` (no `pip install` suelto) — ver hallazgo 002 en `bitacora.md`.

### Variables de entorno (`.env`, nunca se sube a git)

```env
NOTION_TOKEN=secret_xxx o ntn_xxx
NOTION_DATABASE_ID=...
NOTION_DATA_SOURCE_ID=...
OLLAMA_MODEL=qwen2.5:1.5b   # opcional, este es el default
```

### Pasos

```bash
# 1. Smoke test: confirma que el token y los IDs funcionan, y lista las
#    columnas detectadas (de aquí sale el NOTION_DATA_SOURCE_ID real)
python test_notion_connection.py

# 2. Correr el agente interactivo
python agente.py
```

Dentro del chat, escribir `salir` (o `exit`/`quit`) termina la sesión e imprime el reporte de cache hit rate.

### Pruebas manuales de cada pieza por separado

Cada módulo tiene un bloque `if __name__ == "__main__":` ejecutable como prueba rápida independiente:

```bash
python buscar_memoria.py      # prueba de búsqueda con debug de puntajes
python guardar_memoria.py     # prueba de upsert con dos contextos distintos
python filtro_calidad.py      # prueba del filtro con un caso "sí" y uno "no"
python llm_utils.py           # smoke test de conexión con Ollama
python metricas.py            # imprime el cache hit rate actual
```

No hay suite de tests automatizada (pytest) — la validación actual es manual, vía estos bloques.

---

## 5. Estado actual, pendientes y visión — guía para cualquier agente que continúe este proyecto

Esta sección existe para que **cualquier agente de IA** (Claude Code, u otro, en esta máquina o en otra) que abra este repo entienda de inmediato dónde está el proyecto, sin tener que inferirlo del código.

### Qué está hecho (verificado, funcionando)

- Pipeline completo de lectura → validación por LLM → filtro de calidad → escritura → métricas (descrito en la sección 2), funcionando de punta a punta.
- Upsert con desambiguación por contexto/dominio (un mismo concepto puede tener varias definiciones según el dominio, sin pisarse).
- Calibración de confianza en el system prompt (prefiere "no sé" antes que alucinar), con cuidado de no sobre-aplicarse a afirmaciones personales del usuario (hallazgos 014 y 015).
- Inyección de fecha/hora real del sistema para evitar que el LLM la invente (hallazgo 010).
- 16 hallazgos de desarrollo documentados en `bitacora.md`, cada uno con causa raíz — **leer ese archivo antes de "redescubrir" un bug ya resuelto**.

### Qué falta / qué NO está implementado todavía

- **Memoria de corto plazo (historial de la conversación activa):** el loop en `agente.py` (función `responder()`) procesa cada pregunta de forma aislada — no recibe los turnos anteriores de la misma sesión. Si se quiere que el agente no "olvide" lo dicho un turno antes dentro de la misma conversación, hay que agregarlo explícitamente (ej. acumular una lista de mensajes y pasarla a `llamar_llm`).
- **Clasificador de intención** (pregunta vs. afirmación vs. charla casual) antes de decidir qué hacer con el mensaje — pensado para reducir tanto errores de juicio del filtro de calidad como llamadas innecesarias al LLM.
- **`evaluacion.py` con un golden set** (~40 preguntas fijas) para medir de forma repetible: tasa de alucinación, tasa de JSON válido del filtro, y cache hit rate real, variando temperatura (0.0 / 0.3 / 0.7) y `num_ctx` de Ollama una variable a la vez.
- **Parámetros de Ollama configurables por llamada** en `llm_utils.llamar_llm` — hoy solo `temperatura` es parámetro; `num_ctx` (tamaño de contexto, default bajo en Ollama y puede estar truncando el prompt en silencio), `num_predict`, y `keep_alive` no son configurables aún y probablemente importan más que la temperatura para la latencia y la calidad.
- `requirements.txt` reproducible.
- Limpieza de datos de prueba viejos en la database de Notion antes de medir métricas reales (ver hallazgo 009 — filas basura contaminan el cache hit rate).

### Qué se quiere lograr (visión, en orden de prioridad)

1. Cerrar el MVP con evidencia medible: construir `evaluacion.py` + golden set, y reportar cache hit rate / tasa de alucinación reales (hoy `metricas.json` solo tiene conteos crudos de hits/misses, sin un benchmark fijo detrás).
2. Clasificador de intención como siguiente mejora de precisión/costo.
3. Ajuste de parámetros de Ollama (temperatura por tipo de tarea, `num_ctx`, `num_predict`, `keep_alive`) usando el golden set como vara de medir — **cambiar una sola variable a la vez**.
4. Diferido a futuro, solo si el golden set demuestra que la búsqueda léxica no basta: migrar `buscar_memoria.py` a embeddings + base vectorial (Chroma/FAISS). El esquema de Notion ya está diseñado para soportar ese cambio sin rehacerse.
5. Diferido a futuro: interfaz simple (Streamlit), despliegue como servicio/bot, ingesta de documentos externos, revisión manual de entradas en Notion como control de calidad adicional, patrón outbox para soporte offline (evaluado y diferido deliberadamente — ver `plan_de_proyecto.md`).

### Limitaciones conocidas (riesgos reales de la arquitectura, no bugs por corregir)

- **El filtro de calidad valida "reutilizable", no "verdadero"** (hallazgo 011): el mismo modelo que puede alucinar una respuesta es el que decide si vale la pena guardarla, sin verificación externa independiente. Un sistema de memoria auto-alimentada por un LLM sin verificación externa puede acumular errores con el tiempo, y esos errores se ven tan "confiables" en Notion como los datos correctos. No se resuelve en este alcance (requeriría contrastar contra una fuente externa confiable) — es una limitación de diseño documentada a propósito, no una omisión.
- **Latencia ~2x** respecto a usar Ollama directo, porque cada turno hace dos llamadas al LLM (respuesta + filtro de calidad) — trade-off aceptado conscientemente (hallazgo 013).
- La búsqueda léxica con stemming no captura sinónimos reales (solo variantes morfológicas de la misma raíz) — es la limitación esperada de la v1 que motivaría la migración a embeddings (punto 4 de la visión).

### Cómo validar que un cambio funciona

1. `ollama list` debe mostrar `qwen2.5:1.5b` (o el modelo configurado en `OLLAMA_MODEL`) corriendo/disponible.
2. `python test_notion_connection.py` debe imprimir `✅ Conexión exitosa` y listar las columnas esperadas (`Pregunta`, `Resumen`, `Tags`, `Fecha`).
3. Antes de medir cualquier métrica, verificar que la database de Notion no tenga filas basura de pruebas anteriores (hallazgo 009).
4. Para un cambio en búsqueda/filtro/guardado: correr el bloque `__main__` del archivo modificado primero (prueba aislada, rápida) antes de probar el loop completo.
5. Para un cambio en el comportamiento conversacional (prompts, calibración, etc.): correr `python agente.py` y probar manualmente al menos tres tipos de mensaje — una pregunta factual, una afirmación personal del usuario, y charla casual — porque cambios de prompt han tenido efectos secundarios no previstos entre estos tres casos antes (hallazgos 015 y 016).
6. Al terminar una sesión de `agente.py`, revisar que el reporte de cache hit rate impreso tenga sentido con lo que se probó (si todo fue preguntas nuevas, debería ser 0% hits; si se repitió una pregunta ya guardada, debería contar como hit).
7. Revisar `bitacora.md` antes de reportar un bug como nuevo — varios comportamientos "raros" ya están documentados como hallazgos con su causa raíz.

---

## 6. Bitácora de desarrollo

`bitacora.md` registra 16 hallazgos reales del desarrollo (bugs, limitaciones de diseño, decisiones de arquitectura), cada uno con síntoma, causa raíz, solución y aprendizaje — pensado para no repetir el mismo error en otro proyecto, y como evidencia de proceso de depuración real más allá de "conectar APIs".

## 7. Documentación adicional

- `plan_de_proyecto.md` — planeación completa: problema, alcance, opciones de solución evaluadas y por qué se eligieron, roadmap por fases.
- `Documentation.txt` — referencia rápida de la estructura JSON que espera cada tipo de columna de Notion (title, rich_text, multi_select, select, date).
