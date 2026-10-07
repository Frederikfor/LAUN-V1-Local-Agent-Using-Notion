
# Bitácora de desarrollo — Agente con memoria en Notion

Registro de problemas encontrados durante el desarrollo, su causa raíz y la solución aplicada. El objetivo no es solo documentar qué se arregló, sino **por qué pasó**, para no repetir el mismo error en otro proyecto.

---

### 001 — Code Runner ejecutaba solo texto seleccionado, no el archivo completo

**Síntoma:** `NameError: name 'NOTION_TOKEN' is not defined`, ejecutando un archivo llamado `tempCodeRunnerFile.py` en vez del script real.
**Causa raíz:** la extensión Code Runner de VS Code ejecuta solo el texto seleccionado en el editor (si había algo resaltado sin querer), copiándolo a un archivo temporal.
**Solución:** correr el script completo desde la terminal integrada (`python archivo.py`) en vez de depender del botón "Run" de Code Runner.
**Aprendizaje:** cuando el nombre del archivo en el traceback no es el que esperabas, esa es la pista — no el mensaje de error en sí.

---

### 002 — `ModuleNotFoundError` a pesar de haber instalado la librería

**Síntoma:** `ModuleNotFoundError: No module named 'notion_client'` / `'requests'`, después de correr `pip install`.
**Causa raíz:** Windows tenía más de un intérprete de Python accesible; `pip install` instaló la librería en uno distinto al que `python` usaba para ejecutar el script.
**Solución:** usar siempre `python -m pip install <paquete>`, que garantiza instalar para el mismo intérprete que se va a usar para correr el código.
**Aprendizaje:** en Windows, `pip` y `python -m pip` no son intercambiables cuando hay múltiples instalaciones. Diagnosticar con `python -m pip show <paquete>` antes de asumir que "ya está instalado".

---

### 003 — `KeyError: 'properties'` al leer una database de Notion

**Síntoma:** la conexión a Notion funcionaba, pero al intentar leer las columnas de la database, fallaba con `KeyError: 'properties'`.
**Causa raíz:** cambio real en la API de Notion (versión 2025-09-03): las columnas de una database ya no viven en el objeto `database`, sino en un objeto hijo llamado `data_source`. Una database puede tener uno o más data sources.
**Solución:** flujo de dos pasos — `databases.retrieve()` para obtener la lista de `data_sources`, y luego una petición GET a `/v1/data_sources/{id}` para obtener las columnas reales.
**Aprendizaje:** cuando una librería o API de terceros cambia de versión, el error no siempre es del código propio — vale la pena buscar "breaking changes" de la API antes de asumir un bug propio.

---

### 004 — Notion rechaza valores nuevos en una columna tipo Select

**Síntoma (anticipado, evitado antes de que ocurriera):** escribir un valor en una columna `select` que no existe como opción predefinida causa error.
**Causa raíz:** a diferencia de `multi_select`, una columna `select` en Notion no crea opciones nuevas automáticamente vía API.
**Solución:** crear manualmente las opciones (`Alta`, `Media`, `Baja`) en Notion antes de escribir desde el script.
**Aprendizaje:** cada tipo de propiedad de Notion tiene su propio contrato de escritura — no asumir que todas se comportan igual.

---

### 005 — `ValueError` por falta de `NOTION_DATA_SOURCE_ID`

**Síntoma:** el script de escritura fallaba porque faltaba una variable de entorno.
**Causa raíz:** al agregar la función de escritura, se introdujo una nueva dependencia (`data_source_id`, ver bug 003) que no se había agregado al `.env` existente.
**Solución:** agregar la variable faltante al `.env`.
**Aprendizaje:** cuando el diseño evoluciona (bug 003), hay que revisar qué otras partes del proyecto asumen el diseño viejo.

---

### 006 — Búsqueda por palabras clave no detecta variantes morfológicas

**Síntoma:** una pregunta sobre "autenticación" no encontraba una entrada guardada sobre "cómo se autentica", a pesar de tratar del mismo tema.
**Causa raíz:** la comparación era por coincidencia exacta de palabras (strings). `"autentica"` y `"autenticación"` son la misma raíz semántica pero strings distintos, así que no contaban como coincidencia.
**Solución:** aplicar *stemming* (reducción a raíz de la palabra) con `NLTK` (`SnowballStemmer` en español) antes de comparar.
**Aprendizaje:** esto no fue un bug de código — fue el sistema funcionando exactamente como se diseñó, revelando un límite real del diseño simple de v1. Es la señal esperada de "cuándo migrar a algo más sofisticado" que anticipamos desde el plan del proyecto (ver sección de Metodología: Lean/MVP). Documentado aquí como evidencia de que el enfoque incremental está funcionando como se esperaba.

---

### 007 — Preguntas cortas sobre un concepto no alcanzaban el umbral de coincidencias

**Síntoma:** la pregunta `"¿qué es el color?"` no encontraba el concepto "Color" ya guardado, a pesar de nombrarlo directamente.
**Causa raíz:** el umbral de coincidencias exigía 2 palabras en común, pero una pregunta corta y natural sobre un concepto de una sola palabra, tras quitar stopwords, solo deja esa una palabra de contenido real. El diseño anterior no distinguía entre "coincidir con el nombre del concepto" (señal fuerte) y "coincidir con una palabra suelta dentro de una definición" (señal débil).
**Solución:** ponderar el puntaje — coincidencias con el nombre del concepto valen 3 puntos, coincidencias con el contenido de las definiciones valen 1 punto. Esto permite que preguntas directas y cortas ("¿qué es X?") encuentren el concepto de inmediato, sin abrir la puerta a falsos positivos por palabras sueltas.
**Aprendizaje:** no todas las coincidencias de palabras valen lo mismo. Cuando el diseño distingue *qué tipo* de coincidencia es (nombre del concepto vs. contenido de apoyo), el sistema se vuelve más preciso sin volverse más complicado de usar.
**Estado:** ✅ verificado — "¿qué es el color?" ahora encuentra el concepto "Color" con puntaje 4 (3 por nombre + 1 por contenido), y detecta correctamente que tiene 2 contextos ambiguos.

---

### 008 — Modelo pequeño fallaba el filtro de calidad (JSON inválido y juicio incorrecto)

**Síntoma:** `qwen2.5:1.5b` generaba JSON con coma sobrante antes del `}`, y decidía guardar un saludo casual como si fuera conocimiento reutilizable.
**Causa raíz:** dos problemas distintos — (1) el modelo mezcla la sintaxis de un dict de Python (coma final válida) con JSON estricto (inválida); (2) instrucciones abstractas ("no guardes conversación casual") no eran suficientes para que un modelo de 1.5B generalizara bien el criterio.
**Solución:** (1) limpiar comas sobrantes con una expresión regular antes de parsear; (2) agregar ejemplos concretos (few-shot) al prompt de sistema, mostrando un caso correcto de guardar y dos de no guardar.
**Aprendizaje:** los modelos pequeños generalizan peor a partir de reglas abstractas que los modelos grandes, pero responden muy bien a ejemplos concretos. Cuando un modelo chico "no entiende" una instrucción, antes de descartarlo vale la pena intentar few-shot prompting — suele cerrar buena parte de la brecha sin cambiar de modelo.
**Estado:** ✅ verificado con 3 casos de prueba (2 propuestos + 1 agregado por iniciativa propia durante las pruebas).

Cuando aparezca un bug nuevo, documentarlo con esta plantilla:

```
### 0XX — Título corto del problema
**Síntoma:** qué se observó (el error o comportamiento inesperado).
**Causa raíz:** por qué pasó, no solo "qué se arregló".
**Solución:** qué cambio concreto se hizo.
**Aprendizaje:** qué se puede aplicar a futuros proyectos.
```

---

### 009 — Cache hit rate falso positivo por filas basura en Notion

**Síntoma:** dos preguntas completamente nuevas se registraron como "hit" (100% cache hit rate), cuando deberían haber sido "miss".
**Causa raíz:** filas de prueba de sesiones anteriores (con nombres como `"hola?"` y `"a"`) seguían existiendo en la database de Notion. Una de las preguntas nuevas empezaba con "Hola", lo que generó una coincidencia exacta de nombre contra la fila basura `"hola?"`.
**Solución:** limpieza manual de datos — borrar filas de prueba de Notion antes de correr pruebas reales del agente completo.
**Aprendizaje:** un sistema de memoria es tan confiable como los datos que contiene. Antes de medir cualquier métrica (cache hit rate, precisión, etc.), hay que asegurarse de que el dataset esté limpio de artefactos de pruebas anteriores — si no, la métrica miente.

---

### 010 — El agente alucinó la fecha y hora actuales

**Síntoma:** ante la pregunta "¿qué día es hoy?", el modelo respondió con una fecha y hora inventadas, con total seguridad.
**Causa raíz:** un LLM (más aún uno pequeño y local, sin acceso a internet) no tiene ninguna forma de saber la fecha/hora real — cuando no sabe algo, tiende a generar una respuesta plausible en vez de admitir que no lo sabe (alucinación).
**Solución:** inyectar la fecha/hora real del sistema (obtenida con `datetime.now()` en Python, dato 100% determinístico) como contexto verificado en cada prompt, para que el modelo nunca tenga que adivinarla.
**Aprendizaje:** cualquier dato que el programa YA conoce con certeza (fecha, hora, resultados de cálculos, datos de una base de datos) se le debe dar al LLM explícitamente — nunca asumir que "ya lo sabe" o dejar que lo infiera. Un LLM no tiene reloj, ni calculadora confiable, ni acceso a la realidad fuera de lo que se le da como contexto.

---

### 011 (limitación conocida, no resuelta) — El filtro de calidad valida "reutilizable", no "verdadero"

**Síntoma:** el agente guardó en Notion la definición "una semana... termina el día viernes" — información objetivamente incorrecta (una semana tiene 7 días y termina en domingo) — como si fuera un hecho confiable.
**Causa raíz:** el filtro de calidad (`filtro_calidad.py`) solo evalúa si una respuesta es *reutilizable* (tema general, no conversación casual). Nunca evalúa si es *correcta*. Peor aún: el mismo modelo que alucinó la respuesta es el que decide si vale la pena guardarla — no hay una verificación independiente.
**Por qué NO se resuelve ahora:** verificar la veracidad de una afirmación de forma automática es un problema de investigación abierto en IA (requeriría, como mínimo, contrastar contra una fuente externa confiable — búsqueda web, una base de conocimiento verificada, etc.), y añadirlo ahora sería complejidad desproporcionada para el alcance de este MVP.
**Mitigación parcial ya existente:** el campo `fuente` (`"agente"` vs `"usuario"`) permite, en el futuro, dar menos peso o revisar con más cuidado el conocimiento que el propio agente generó sin confirmación humana, distinto de lo que el usuario afirmó directamente.
**Aprendizaje / riesgo documentado:** cualquier sistema de memoria auto-alimentada por un LLM sin verificación externa puede acumular errores con el tiempo, y esos errores se ven tan "confiables" como los datos correctos una vez guardados. Es un riesgo real de este tipo de arquitectura, no un defecto de implementación — vale la pena mencionarlo explícitamente en cualquier presentación del proyecto (muestra criterio, no descuido).

---

### 012 — El modelo afirmó tener acceso a internet (no lo tiene)

**Síntoma:** al preguntarle directamente, `qwen2.5:1.5b` afirmó que podía buscar en internet para dar mejores respuestas.
**Causa raíz:** el modelo fue entrenado con textos sobre "asistentes de IA", muchos de los cuales sí tienen navegación web. Sin verdadera autoconciencia de su configuración actual, completa el patrón esperado ("soy un asistente, los asistentes buscan en internet") en vez de reportar su capacidad real.
**Solución:** se agregó al system prompt una aclaración explícita de que el agente NO tiene acceso a internet ni herramientas externas, y que debe decirlo claramente en vez de asumir capacidades que no tiene.
**Aprendizaje:** un LLM nunca es una fuente confiable sobre sus propias capacidades o limitaciones — eso lo define la configuración real del sistema (qué herramientas están conectadas), no lo que el modelo "cree" o dice sobre sí mismo. Cualquier restricción real debe declararse explícitamente en el prompt, nunca asumirse implícita.

---

### 013 — Latencia notablemente mayor que usar Ollama directo

**Síntoma:** el agente se siente más lento que chatear directo con `ollama run qwen2.5:1.5b`.
**Causa raíz:** no es un bug — cada turno de `agente.py` hace DOS llamadas al LLM (una para la respuesta, otra silenciosa para el filtro de calidad), el doble de trabajo que una conversación simple.
**Decisión:** aceptado como trade-off consciente del diseño para esta fase. Optimizaciones futuras posibles: saltar el filtro de calidad en mensajes triviales/cortos, o evaluar en paralelo en vez de secuencial.

---

### 014 — Calibración de confianza para reducir alucinaciones

**Contexto:** no es un bug encontrado, sino una mejora propuesta por el usuario durante las pruebas: instruir al modelo explícitamente a preferir decir "no lo sé" antes que inventar, penalizando fuerte las afirmaciones falsas con apariencia de seguridad.
**Implementación:** se agregó un system prompt de "calibración de confianza" a todas las respuestas del agente (no solo al filtro de calidad), aplicando el mismo principio que ya usábamos para el filtro: instrucciones abstractas + ejemplo del criterio de penalización.
**Aprendizaje:** esta es una técnica real y documentada en la literatura de IA (calibrated confidence prompting) para reducir alucinaciones a bajo costo. No la elimina por completo en un modelo de 1.5B, pero mejora el comportamiento promedio de forma medible y gratuita.

---

### 015 — La calibración de confianza se sobre-aplicó a declaraciones personales

**Síntoma:** ante "me gusta usar camisetas negras y tenis blancos" (una afirmación, no una pregunta), el agente respondió dudando de si "él" tenía camisetas — confundiendo el sujeto de la oración y aplicando la regla de "admite que no sabes" donde no correspondía.
**Causa raíz:** la instrucción de calibración (hallazgo 014) no distinguía entre "me preguntan un hecho verificable" y "el usuario comparte algo sobre sí mismo". El modelo aplicó la regla de forma demasiado literal/amplia.
**Solución:** se agregó una aclaración explícita al system prompt: la calibración aplica solo a hechos verificables que se le preguntan directamente, no a opiniones o datos personales que el usuario comparte sobre sí mismo.
**Aprendizaje:** cada instrucción que se agrega a un prompt puede tener efectos secundarios no previstos en otros tipos de interacción. Después de agregar una regla nueva, hay que probarla contra varios tipos de mensaje (preguntas, afirmaciones, opiniones), no solo el caso que la motivó.

---

### 016 — El filtro guardó al agente hablando de sí mismo como si fuera conocimiento general

**Síntoma:** se guardó el concepto "Respuesta de IA" a partir de una pregunta sobre el comportamiento del propio agente — técnicamente "reutilizable" pero sin valor real como memoria (es el agente citando su propia instrucción de sistema).
**Causa raíz:** el criterio del filtro ("conocimiento general reutilizable") no distinguía entre conocimiento sobre el mundo y contenido auto-referencial sobre el propio agente/sus reglas.
**Solución:** se agregó un cuarto ejemplo (few-shot) al filtro de calidad mostrando explícitamente este caso como "no guardar".
**Aprendizaje:** el criterio de un filtro casi nunca queda completo a la primera — se refina con casos reales que el diseño original no anticipó, siguiendo el mismo patrón de mejora iterativa que ya se usó en la búsqueda (hallazgos 006 y 007).
