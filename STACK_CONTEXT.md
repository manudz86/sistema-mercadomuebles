# ⚙️ STACK_CONTEXT — Contexto de Trabajo: Sistema Cannon

Contexto para trabajar eficientemente en el sistema. Leer antes de cualquier tarea.

---

## 🏗️ Stack & Infraestructura

- **Backend:** Python / Flask
- **Base de datos:** MySQL — `inventario_cannon`
- **Servidor:** VPS Hostinger — `72.61.134.243` — path: `/home/cannon/app/`
- **Process manager:** Gunicorn — servicio: `cannon`
- **Archivos principales:**
  - `app.py` (~12.400 líneas) — panel admin, sistema interno
  - `tienda_bp.py` — tienda web pública (blueprint Flask separado)
- **URLs:**
  - Admin: `sistema.mercadomuebles.com.ar`
  - Tienda: `mercadomuebles.com.ar`

---

## 🚀 Deploy

### Sistema (app.py)
- Deploy via `deploy_vps.bat`: git push local → git pull en VPS → restart Gunicorn
- Manu guarda el archivo localmente y ejecuta el .bat — todo automático

### Tienda (tienda_bp.py + templates)
- Deploy via SCP directo al VPS
- Comando desde la carpeta donde están los archivos:
  ```
  scp tienda_bp.py root@72.61.134.243:/home/cannon/app/tienda_bp.py
  ```
- Templates se copian igual por SCP
- `tienda_bp.py` **no está en git**

---

## 💳 Integraciones de Pago (Tienda Web)

Todas las integraciones de pago son exclusivas de `tienda_bp.py`.

| Método | Para qué | Estado |
|--------|----------|--------|
| **MercadoPago Checkout Bricks** | Pago con cuenta MP y sin cuenta (tarjeta) | ✅ Integrado, feature-flagged via tabla `configuracion` |
| **Payway (Decidir)** | 3 cuotas MiPyME | ✅ Integrado — pendiente activación MiPyME por Payway support |
| **GetNet (Santander/GeoPagos)** | 6 cuotas MiPyME | ✅ Integrado en tienda web y sistema (webhook) |

**Pendiente:** Ajuste en cómo se guardan datos de GetNet en ventas activas (sistema).

---

## 🔗 Otras Integraciones

| Integración | Dónde | Estado |
|-------------|-------|--------|
| **MercadoLibre** | app.py — OAuth, publicaciones, órdenes, auto-import | ✅ |
| **Zipnova** | app.py (cotizador envíos sistema) + tienda_bp.py (cotización y creación envío post-pago) | ✅ |
| **WhatsApp (Meta)** | app.py — plantillas aprobadas | ✅ |
| **GA4** | tienda_bp.py — eventos `purchase`, `add_to_cart` | ✅ |
| **APScheduler** | app.py — 3 jobs: auto-import ML (120s), cancelaciones ML (10min), completar notas MP (10min) | ✅ |

---

## 📋 Convenciones de Trabajo

### Cómo se trabaja en este proyecto

1. **Manu pasa archivos completos** — nunca fragmentos sueltos para editar
2. **Claude modifica estrictamente lo necesario** — sin refactors no pedidos, sin cambiar nombres, sin reorganizar
3. **Después de cada modificación, Claude rechecquea** que no se haya borrado ni roto nada anterior en el archivo
4. **Claude devuelve el archivo completo modificado** — listo para deploy

### Convenciones de código en app.py

- Queries DB via helpers: `query_db()`, `query_one()`, `execute_db()`
- Conexión: `get_db_connection()`
- Feature flags en tabla `configuracion` (key/value)
- Decoradores de acceso: `@login_required`, `@admin_required`, `@vendedor_required`, `@agencia_only`
- Schedulers iniciados en `iniciar_scheduler()`
- Progress de ML compartido entre workers via `configuracion` table (`_ml_progress_get/save`)
- SKU normalization via `normalizar_sku_ml()` + dict `SKU_MAP`

### Convenciones en tienda_bp.py

- Conexión DB propia: `get_db()`
- SDK MP: `get_mp_sdk()`
- Context processors: `inject_nl_popup_desc()`, `inject_now()`
- Stock real via `_get_stock_real()` y `get_stock_disponible_sku()`
- Cuotas configuradas desde tabla `configuracion` (coeficientes 3c/6c)

---

## 🗄️ Tablas Clave

Ver `DB_MAP.md` para mapa completo. Tablas más tocadas:

- `ventas` — cabecera de ventas (28 funciones escriben, 27 leen)
- `items_venta` — detalle de productos por venta
- `productos_base` — stock, precios, dimensiones de productos individuales
- `productos_compuestos` — sommiers (productos armados)
- `componentes` — relación compuesto ↔ base
- `configuracion` — feature flags, tokens, coeficientes, demoras
- `pedidos_pendientes` — checkout pre-webhook

---

## 📍 Estado Actual / Pendientes

- **GetNet en ventas activas:** falta ajustar cómo se muestran/guardan los datos de transacciones GetNet en el panel de ventas activas del sistema
- **Payway MiPyME:** integración completa, pendiente activación por parte de Payway support
- **tienda_bp.py en git:** no está versionado — solo deploy por SCP

---

## 🤖 Bots & Scripts Externos

| Bot | Archivo | Cómo corre | Descripción |
|-----|---------|------------|-------------|
| **Bot WhatsApp** | `.py` propio | On demand / webhook | Recibe consultas y deriva a 2 teléfonos si se necesita atención humana |
| **Bot de Precios** | `.py` propio | On demand (manual) | No corre solo — se ejecuta cuando se necesita |
| **Bot de Competencia** | `.py` propio | Automático via Scheduler | Monitoreo periódico de competidores |
| **Bot de Scrapeo** | `.bat` en PC local + `.py` en VPS | Semi-automático | El .bat corre en la PC de Manu, scrapea competidores (publicaciones distintas a las del bot de competencia), sube un `.csv` automáticamente al VPS, y un `.py` en el sistema analiza los datos y los muestra en la sección correspondiente |

---

## 🔍 Cómo encontrar cosas

- **Ver endpoints:** `SYSTEM_MAP.md` → sección "Rutas HTTP"
- **Ver qué toca una tabla:** `DB_MAP.md` → buscar nombre de tabla
- **Ver helpers disponibles:** `SYSTEM_MAP.md` → sección "Helpers"
- **Número de línea de una función:** ambos mapas incluyen `(L####)`
- **Los mapas se regeneran** con `scripts/generar_mapas.py` — no editar a mano
