# PREGUNTAS_ML — Bot de respuestas de preguntas de Mercado Libre

Asistente que ayuda a responder las preguntas de los compradores en ML.
Pensado en etapas. **Hoy está hecho hasta la Fase 1b** (sugiere, Matías revisa/edita y envía).
La **Etapa 2 (automático) está PENDIENTE** — spec abajo.

---

## Estado actual (HECHO)

### Fase 1a — MVP (traer / mostrar / responder a mano)
- **Tabla `ml_preguntas`** (migración `005`): espejo de las preguntas de ML.
- **Job `job_sincronizar_preguntas`** (scheduler, cada 3 min, `app.py`): trae las `UNANSWERED`
  de `GET /questions/search?seller_id=...&status=UNANSWERED`, hace upsert, y marca como
  ANSWERED las que ya no figuran.
- **Página `/preguntas`** (`templates/preguntas.html`): lista con contexto, tabs
  (sin responder / respondidas / todas), botón Sincronizar.
- **Responder a mano:** `POST /preguntas/<id>/responder` → `POST /answers` a ML.
- **Badge rojo** en el menú (`preguntas_pendientes_count` en el context processor `app.py:57`).
- Contexto por pregunta, **todo desde la publicación (no de la BD)**: SKU (`SELLER_SKU`),
  precio, **stock (available_quantity de la publi)**, tipo (Catálogo / Listado general),
  **cuotas**, **tiempo atrasado** ("hace 2d 3h") y **historial** del mismo comprador en la
  misma publi (`GET /questions/search?item=...`).

### Fase 1b — Sugerencia con IA + reglas + aprendizaje
- **`_sugerir_respuesta()` (`app.py`)** con Claude (`claude-sonnet-4-5`). El prompt combina:
  - **Reglas** (editables) — ver abajo.
  - **Condiciones de envío** según la Z del SKU: **con Z → ME1**, **sin Z → Flex**.
  - **Conocimiento de producto:** reusa `CATALOGO_INFO` del bot de WhatsApp
    (`from whatsapp_bp import CATALOGO_INFO`): resortes, densidad, altura, tela, soporte,
    fórmula de altura del conjunto, etc.
  - **Contexto de la publi** + **few-shot** de respuestas confirmadas.
- La sugerencia se genera en el sync al entrar una pregunta nueva; botón **Regenerar**.
- **Si el bot no sabe** (le falta el dato) → devuelve `[SIN_RESPUESTA]` y la sugerencia
  queda **en blanco** (no inventa). Matías la responde y eso queda como ejemplo.
- **Aprendizaje:** tabla `preguntas_ejemplos` — cada respuesta enviada se guarda como
  `(pregunta → respuesta)` y se usa como few-shot. El bot copia el estilo/criterio de Matías.
- **Reglas editables** en `/preguntas/reglas` → `configuracion.preguntas_reglas` (JSON,
  leído en vivo, sin reinicio). Campos: `saludo`, `cierre`, `tono`, `prohibido[]`,
  `envio_me1`, `envio_flex`.
  - Saludo: "Hola, gracias por contactarnos."
  - Cierre: "Cualquier consulta, estamos a tu disposición, Matías de MercadoMuebles."
  - Estilo: respuesta **de corrido** (un solo bloque, sin párrafos/saltos), muy concisa,
    **solo lo preguntado**, sin preámbulos.
  - Prohibido: dirección exacta, teléfono, email, links/redes, vender fuera de ML, etc.
  - Ubicación (respuesta fija): "Estamos en Floresta, CABA de lunes a viernes de 8 a 12 y 14 a 16.30hs."

### Archivos / objetos clave
- `app.py`: helpers `_preguntas_search`, `_pregunta_item_ctx`, `_pregunta_historial`,
  `_humanizar_atraso`, `_preguntas_reglas`, `_sugerir_respuesta`, `_sync_preguntas`,
  `_responder_pregunta_ml`, `job_sincronizar_preguntas`; rutas `/preguntas`,
  `/preguntas/<id>/responder`, `/preguntas/sync`, `/preguntas/<id>/regenerar`, `/preguntas/reglas`.
- Templates: `preguntas.html`, `preguntas_reglas.html`.
- Tablas: `ml_preguntas`, `preguntas_ejemplos`. Config: `configuracion.preguntas_reglas`.
- Migraciones: `005_ml_preguntas.sql`, `006_preguntas_1b.sql`.

---

## ETAPA 2 — Respuesta automática (PENDIENTE)

**Objetivo:** que el bot **responda solo** las preguntas que sabe con alta confianza, y
deje **únicamente las dudosas/sensibles** para que las responda Matías (como hoy).

### Cómo funcionaría
1. **Score de confianza:** además de la respuesta, el modelo devuelve una confianza
   (ej. JSON `{respuesta, confianza: alta|media|baja, motivo}`), o se usa el
   `[SIN_RESPUESTA]` ya existente como piso. Umbral configurable.
2. **Gate de auto-respuesta:** en el job de sync, después de generar la sugerencia, si
   `modo_automatico = ON` **y** confianza ≥ umbral **y** la pregunta **no es sensible** →
   postear la respuesta a ML automáticamente (`_responder_pregunta_ml`), marcar respondida
   y registrar `auto_respondida = 1`.
3. **A humano (cola actual)** si: confianza < umbral, `[SIN_RESPUESTA]`, o pregunta sensible.
4. **Nunca auto-responder (forzar revisión humana):**
   - Reclamos, devoluciones, garantías en curso, quejas/post-venta.
   - Negociación de precio / pedidos de descuento.
   - Cualquier cosa que roce las "prohibidas" (datos de contacto, fuera de ML).
   - Preguntas ambiguas o con varias sub-preguntas.
   - Lista configurable de keywords/temas que fuerzan revisión.
5. **Activación gradual (seguridad):**
   - Toggle global on/off (`configuracion.preguntas_auto`).
   - **Modo sombra primero (recomendado):** el bot marca cuáles *habría* respondido solo,
     pero igual las deja para Matías, para **medir el acierto** antes de soltarlo.
   - **Métrica de acierto:** % de sugeridas que Matías envió **sin editar**
     (comparar `respuesta_sugerida` vs `respuesta_final`). Habilitar el auto cuando el
     acierto histórico supere un umbral (ej. ≥ 90%).
   - **Auditoría:** log de respuestas automáticas (texto, confianza, fecha) para revisar
     y poder frenar si algo sale mal.

### Prerrequisitos para arrancar Etapa 2
- Volumen razonable de respuestas confirmadas en `preguntas_ejemplos` (que el few-shot sea bueno).
- Validar el **% de acierto** (modo sombra) antes de activar el automático.

### Decisiones a definir cuando se retome
- Umbral de confianza y cómo se obtiene (modelo lo declara vs se infiere).
- Lista de temas que SIEMPRE van a humano.
- ¿Arrancar en modo sombra? (recomendado sí).
- Qué métricas mostrar en la UI (acierto, % auto, % a humano).

### Cambios técnicos previstos
- `ml_preguntas`: columnas `auto_respondida`, `confianza`, (opcional) tabla de auditoría.
- `_sugerir_respuesta`: devolver también confianza (o función nueva `_evaluar_confianza`).
- `job_sincronizar_preguntas`: aplicar el gate y, si corresponde, auto-responder.
- Config: `preguntas_auto` (on/off + umbral + temas-a-humano), editable en `/preguntas/reglas`.
- UI: indicador de modo (sombra/activo) y métrica de acierto.
