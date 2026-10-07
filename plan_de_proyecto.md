
# Agente con memoria persistente en Notion

## Problema

Los agentes basados en LLM (modelos de lenguaje) gratuitos o de uso general tienen memoria limitada al contexto de una sola conversación. Al cerrar la sesión, todo el conocimiento generado o discutido se pierde. Esto obliga a repetir explicaciones, volver a investigar lo mismo, y le impide al agente "crecer" con el uso — cada conversación empieza de cero, sin importar cuánto se haya interactuado con él antes.

## Solución planteada

Construir un agente en Python que use **Notion como memoria externa persistente**. Antes de procesar una pregunta desde cero, el agente consulta primero su base de conocimiento en Notion. Si encuentra algo suficientemente parecido, lo reutiliza. Si no, procesa la pregunta normalmente y, si el contenido generado pasa un filtro de calidad, lo guarda en Notion como conocimiento nuevo para el futuro.

## Método esperado de funcionamiento

1. El usuario le hace una pregunta o consulta al agente.
2. El agente busca en la base de Notion si ya existe una entrada suficientemente parecida (v1: coincidencia ponderada de palabras clave, con más peso al nombre del concepto que al contenido de sus definiciones).
3. **Si encuentra una coincidencia candidata:** no se responde directo con ella. Se le pasa esa memoria al LLM como contexto adicional, junto con la pregunta original. El propio LLM decide si esa información realmente responde lo que se preguntó (ej. una definición guardada de "Color" no responde "¿cuáles son los colores primarios?", aunque comparta la palabra clave). Si sirve, la usa —ahorrando reprocesamiento—; si no sirve, la descarta y sigue al paso 4 como si no hubiera habido coincidencia.
4. **Si no hay coincidencia (o la coincidencia no sirvió):** procesa la pregunta con el LLM (y herramientas externas si aplica) desde cero.
5. El agente se autoevalúa: ¿esta respuesta contiene conocimiento reutilizable en el futuro? Si sí, genera un resumen destilado y tags.
6. Si pasa el filtro de calidad, el agente escribe una fila nueva en Notion con: pregunta, resumen, tags, nivel de confianza y fecha.
7. Con el tiempo, la base de Notion crece y el porcentaje de "hits" debería aumentar — esa métrica (cache hit rate) es la evidencia de que el agente efectivamente "aprende" con el uso.

## Metodología

Desarrollo iterativo tipo **Lean/MVP**: se construye primero la versión más simple que permite medir algo real (búsqueda por texto, sin embeddings), se valida que funciona de punta a punta, y solo se añade complejidad (búsqueda semántica, vector store) cuando los datos reales demuestran que la versión simple no es suficiente. Se aplican principios de control de calidad en el origen (Poka-Yoke): el filtro de calidad evita que se contamine la memoria con información irrelevante o de baja confianza, en vez de intentar limpiarla después.

## Delimitación de la solución

**Incluye:**

- Un agente en Python que consulta y escribe en una base de datos de Notion vía su API oficial.
- Búsqueda de coincidencias por palabras clave (texto), sin embeddings en la v1.
- Un filtro de calidad automático simple para decidir qué se guarda.
- Métrica de cache hit rate para medir efectividad.

**No incluye (fuera de alcance en esta fase):**

- Búsqueda semántica con embeddings o base de datos vectorial (queda como paso futuro).
- Interfaz gráfica de usuario (se usa consola/scripts de Python).
- Autenticación multiusuario u OAuth (es una integración interna, de un solo usuario/workspace).
- Ingesta de documentos externos (PDFs, páginas web) como fuente de conocimiento — la memoria se alimenta únicamente de las interacciones del propio agente.

## Planteamiento de opciones de solución

| Decisión                  | Opción A                              | Opción B                               | Opción C                                                   |
| -------------------------- | -------------------------------------- | --------------------------------------- | ----------------------------------------------------------- |
| Qué se cachea             | Solo pregunta → respuesta literal     | Conocimiento destilado (resumen + tags) | —                                                          |
| Autenticación con Notion  | Token de integración interna          | OAuth (integración pública)           | —                                                          |
| Búsqueda de coincidencias | Coincidencia de palabras clave (texto) | Coincidencia por tags                   | Embeddings/búsqueda semántica                             |
| Control de qué se guarda  | Automático sin filtro                 | Aprobación manual del usuario          | Automático con filtro de calidad (autoevaluación del LLM) |

## Solución elegida y justificación

- **Conocimiento destilado**, no pregunta-respuesta literal: es más robusto ante variaciones en cómo se formula una pregunta, y permite que el agente acumule *insights*, no solo respuestas textuales.
- **Token de integración interna**: es un proyecto de un solo usuario/workspace; OAuth agregaría complejidad de autenticación (flujo de redirección, refresh tokens) sin aportar valor real en este alcance.
- **Búsqueda por palabras clave (v1)**: evita construir infraestructura de embeddings antes de tener evidencia de que la búsqueda simple no es suficiente. La estructura de datos en Notion queda diseñada para migrar a embeddings sin rehacer el esquema.
- **Filtro de calidad automático**: guardar todo sin criterio contamina la memoria con ruido; pedir aprobación manual en cada entrada no escala. Un filtro automático (el propio LLM decide si vale la pena recordar) es el punto intermedio correcto para este alcance.

## Planteamiento de elaboración

### Fase previa

- Definición del problema y alcance.
- Investigación de la API de Notion (incluyendo el cambio de arquitectura de septiembre 2025: databases vs. data sources).
- Toma de decisiones de arquitectura (tabla de opciones arriba).

### Fase inicial

- Creación de la integración interna en Notion y obtención del token.
- Creación de la database con el esquema definido (Pregunta, Resumen, Tags, Confianza, Fecha).
- Configuración del entorno de desarrollo en Python (dependencias, variables de entorno).
- Prueba de conexión (smoke test) end-to-end.

### Fase de desarrollo

- Función de escritura (`guardar_entrada`): crea filas nuevas en Notion con el esquema definido.
- Función de lectura (`buscar_en_memoria`): consulta todas las filas y compara por palabras clave.
- Filtro de calidad: prompt de autoevaluación que decide si una respuesta debe guardarse, y genera resumen + tags.
- Loop principal del agente: integra lectura → procesamiento condicional → escritura.
- Instrumentación de métricas: conteo de hits vs. misses (cache hit rate).

### Conclusión

- MVP funcional demostrable de punta a punta.
- Documentación del proyecto (README con arquitectura, instrucciones de instalación, capturas o demo).
- Publicación del código en GitHub con `.gitignore` para proteger credenciales.

### Posibles siguientes pasos

- Migrar la búsqueda de palabras clave a embeddings + base vectorial (Chroma/FAISS) para mayor precisión semántica.
- Agregar una interfaz simple (Streamlit) en vez de consola.
- Permitir que el usuario revise/edite manualmente las entradas de Notion como control de calidad adicional.
- Desplegar el agente como un servicio accesible (API o bot de Telegram/Slack).
- Agregar ingesta de documentos externos como fuente adicional de conocimiento inicial (fusionar con el proyecto de RAG).
- Soporte offline mediante un patrón de cola de sincronización ("outbox pattern"): encolar escrituras localmente cuando no hay internet y reintentarlas al recuperar conexión. Evaluado y diferido deliberadamente — la lectura de memoria seguiría requiriendo una réplica local sincronizada bidireccionalmente con Notion, lo cual introduce complejidad de reconciliación de conflictos que no se justifica para el alcance actual del proyecto.

## Refinamiento post-MVP: desambiguación de conceptos y versionado ligero

Durante el desarrollo se identificó un riesgo real en el diseño original: la búsqueda por palabras clave no distingue **dominios/contextos** distintos para un mismo término (ej. "color" en diseño gráfico vs. "color" en teoría musical), generando falsos positivos de alta confianza. Además, se identificó la necesidad de no sobrescribir conocimiento previo cuando aparece información nueva o conflictiva sobre el mismo concepto.

**Decisión adoptada (alcance intermedio, sin agregar una segunda database):**

- El campo `Pregunta` (título) pasa a representar el **nombre del concepto** (ej. "Color"), no una pregunta completa.
- El campo `Resumen` almacena una **lista de objetos JSON**, uno por cada contexto/dominio conocido para ese concepto, con esta forma:
  ```json
  [
    {
      "contexto": "Diseño gráfico",
      "definicion": "...",
      "fuente": "agente",
      "actualizado": "2026-09-19"
    }
  ]
  ```

  El campo `fuente` distingue si la definición fue interpretada automáticamente por el agente (`"agente"`) o afirmada directamente por el usuario (`"usuario"`) — esta distinción permite, en el futuro, dar más peso a lo que el usuario confirmó explícitamente. Se eligió JSON en vez de texto libre con separadores porque es parseable de forma determinística (`json.loads`/`json.dumps`), sin depender de expresiones regulares frágiles. El JSON nunca se expone directamente al usuario en la conversación — el agente siempre lo traduce a lenguaje natural al responder.
- El campo `Tags` (multi_select) se reutiliza para listar los **dominios ya conocidos** para ese concepto — permite verificar rápidamente si ya existe un contexto sin tener que parsear todo el texto de `Resumen`.
- El campo `Fecha` refleja la última vez que se tocó la fila (se agregó o actualizó cualquier bloque).
- **Diferido a una fase futura:** cuando el agente detecte definiciones que se contraponen dentro del mismo contexto, o contextos ambiguos para un mismo escenario, debe señalarlo y consultar con el usuario antes de purgar o resolver el conflicto automáticamente — no se auto-resuelve en silencio.

Esta decisión evita construir un esquema relacional de dos tablas (Conceptos + Historial) antes de tener evidencia de que se necesita ese nivel de rigor, siguiendo el mismo principio Lean aplicado al resto del proyecto.

| Archivo                               | Propósito                                                                                                | Dependencias                                       | Variables de entorno usadas                                         |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------- |
| `.env`                              | Almacena credenciales y IDs sensibles, nunca se sube a control de versiones.                              | —                                                 | `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `NOTION_DATA_SOURCE_ID` |
| `.gitignore`                        | Evita que`.env` y archivos temporales se suban a GitHub.                                                | —                                                 | —                                                                  |
| `test_notion_connection.py`         | Smoke test: valida que el token y los IDs son correctos y que la integración tiene acceso a la database. | `notion-client`, `python-dotenv`, `requests` | `NOTION_TOKEN`, `NOTION_DATABASE_ID`                            |
| `guardar_memoria.py`                | Función de escritura: crea una fila nueva en Notion con conocimiento destilado.                          | `requests`, `python-dotenv`                    | `NOTION_TOKEN`, `NOTION_DATA_SOURCE_ID`                         |
| `buscar_memoria.py`                 | Función de lectura: busca coincidencias por palabras clave contra las filas existentes.                  | `requests`, `python-dotenv`                    | `NOTION_TOKEN`, `NOTION_DATA_SOURCE_ID`                         |
| `filtro_calidad.py` *(pendiente)* | Prompt de autoevaluación: decide si una respuesta vale la pena guardar, genera resumen y tags.           | Cliente del LLM elegido (Claude/OpenAI)            | Clave API del LLM                                                   |
| `agente.py` *(pendiente)*         | Loop principal: conecta lectura, procesamiento condicional, filtro de calidad y escritura.                | Todos los anteriores                               | Todas las anteriores                                                |
| `metricas.py` *(pendiente)*       | Registra y reporta el cache hit rate (hits vs. misses).                                                   | —                                                 | —                                                                  |
| `requirements.txt` *(pendiente)*  | Lista de dependencias del proyecto para instalación reproducible.                                        | —                                                 | —                                                                  |
| `README.md` *(pendiente)*         | Documentación del proyecto: arquitectura, instalación, uso, capturas/demo.                              | —                                                 | —                                                                  |
