# Sistema Cannon — Handoff de Sesión

## Stack técnico
- **Backend**: Python/Flask + MySQL, VPS Hostinger São Paulo (`72.61.134.243`)
- **DB**: `inventario_cannon` (user: `cannon`, pass: `Sistema@32267845`)
- **Servicio**: `cannon.service` (gunicorn, 3 workers), venv en `/home/cannon/app/venv`
- **App principal**: `/home/cannon/app/app.py` (~10.500 líneas)
- **Templates**: `/home/cannon/app/templates/`
- **Config**: `/home/cannon/app/config/.env`
- **Repo**: https://github.com/manudz86/sistema-mercadomuebles
- **Deploy**: git push local → git pull en VPS + `sudo systemctl restart cannon`
- **SSH**: solo por llave (no contraseña), o terminal web Hostinger

## Sistemas
- **Sistema admin** (sistema.mercadomuebles.com.ar): `app.py`
- **Tienda pública** (mercadomuebles.com.ar): `tienda_bp.py` (blueprint Flask)

---

## TODO / Pendiente conocido
- Cargar stock y bajar stock: triggers de ML para compacs (`CCO*_DEP`) **no implementados aún** (solo está en auto-import y cancelar/eliminar venta)
- Transferir stock: trigger implementado pero no probado en producción

---

## Lo implementado en esta sesión (resumen)

### Auto-import ML
- Scheduler APScheduler cada 60s, función `job_auto_importar_ml()`
- Importa órdenes nuevas, mapea SKUs, agrega PLATINO automático, calcula flete
- `_importar_orden_automatica(orden, access_token)` → devuelve `(bool, items_bd)`
- **Compacs**: `CCO*` se mapea a `CCO*_DEP` o `CCO*_FULL` según `logistic_type`:
  - `self_service` / `cross_docking` → `_DEP`, método envío Delega/Colecta
  - `fulfillment` → `_FULL`, método envío Full, ML gestiona stock solo
- **Billing info**: usa endpoint `/orders/{id}/billing_info` con estructura `additional_info` (array `{type, value}`)
- **Importe**: `importe_total` = `total_amount` (solo productos), `importe_abonado` = `pago_mp` = `paid_amount` (incluye flete)
- **Popup ventas nuevas**: queda hasta que el usuario cierra con ✕, recarga al cerrar

### Actualización ML tras cambios de stock
- Función principal: `actualizar_publicaciones_ml_con_progreso(skus_base_afectados)`
  - Guarda progreso en tabla `configuracion` clave `ml_progress` (JSON)
  - Muestra modal de progreso en tiempo real via polling `/ventas/ml-progress`
  - Maneja `_aplica_logica_z` para Z (solo sommiers y colchones ≥ 140)
  - Excluye almohadas puras y compacs FULL
- **Compac DEP**: función `actualizar_stock_compac_dep_ml(sku_dep, cantidad, token)`
  - Busca MLAs via `/users/{user_id}/items/search?seller_sku=CCO140`
  - Obtiene `user_product_id` de cada MLA
  - Actualiza stock `selling_address` via `PUT /user-products/{up_id}/stock/type/selling_address`
  - Requiere header `x-version` del GET previo; maneja 409 con reintento
  - Salta MLAs que son solo `meli_facility` (FULL)
- Triggers implementados en: `cargar_stock` (JSON), `bajar_stock_guardar`, `cancelar_venta`, `eliminar_venta`, `transferir_stock_guardar`, `job_auto_importar_ml`, webhook tienda `tienda_bp.py`

### Fecha de despacho (observaciones)
- Para `cross_docking`, `xd_drop_off`, `self_service`: consulta `/shipments/{id}/sla`
- Campo `expected_date` = fecha límite de despacho
- Fallback a lógica de hora de corte si SLA falla

### Etiquetas ML (ZPL/PDF)
- Ruta individual: `GET /ventas/activas/<id>/etiqueta-ml?formato=pdf|zpl`
- Ruta masiva: `POST /ventas/etiquetas-ml-masivo`
- ZPL: ML devuelve ZIP → se descomprime y entrega `.zpl`
- **Multiplicación sommiers en ZPL**:
  - SKU `S*` ancho 80/90/100/140/150 → 3 copias
  - SKU `S*` ancho 160/180/200 → 4 copias
  - Colchones/almohadas → 1 copia
- Botón ZPL se pone verde al descargar (persiste en `localStorage`)
- Botones PDF/ZPL aparecen en columna Entrega para ventas ML con Colecta/Flex/Delega

### Fixes aplicados
- `costo_flete = float(request.form.get('costo_flete') or 0)` (evita ValueError con string vacío)
- `_aplica_logica_z`: detecta ancho correctamente de SKUs como `CPR8020` (evitaba activar Z en < 140)
- `_ml_progress_save`: usaba `SELECT id FROM configuracion` pero la PK es `clave`; ahora usa `INSERT ... ON DUPLICATE KEY UPDATE`
- `job_auto_importar_ml`: usaba `actualizar_publicaciones_ml` (vieja, skipea compacs); ahora usa `actualizar_publicaciones_ml_con_progreso`
- `_importar_orden_automatica`: `return False` → `return False, []` (evitaba TypeError en job)
- Porcentajes ML (`cargar_stock_ml.html`): todas las rutas que renderizan el template ahora leen `porcentajes` de BD en vez de defaults hardcodeados

---

## Estructura BD relevante

```sql
-- Stock compac
productos_base: sku (CCO80_DEP, CCO80_FULL, etc.), stock_actual, stock_full

-- Mapeo SKU → MLA (no tiene compacs, se buscan en ML por seller_sku)
sku_mla_mapeo: sku, mla_id, activo

-- Progreso actualización ML (compartido entre workers gunicorn)
configuracion: clave='ml_progress', valor=JSON

-- Auto-import log
auto_import_log: id=1, ventas_nuevas, ultima_ejecucion
```

---

## Metodología de trabajo
- Manu trabaja desde Windows CMD, accede al VPS por SSH/terminal Hostinger
- Prefiere respuestas en **español**, **concisas**
- Prefiere **archivos completos** listos para deployar, no fragmentos
- Siempre hacer `ast.parse` y validación Jinja2 antes de entregar archivos
- Outputs en `/mnt/user-data/outputs/` con `present_files`
- Cuando hay un bug: **primero identificar la causa raíz** antes de tocar código
- No cambiar más de lo estrictamente necesario para no romper cosas que funcionan
- Ante cualquier duda sobre algo no documentado acá, buscar en el transcript de la conversación anterior
