# 🔧 CONFIG_MAP — Tabla `configuracion`

Generado automáticamente por `scripts/generar_config_map.py` el 2026-05-21 12:39. **No editar a mano.**

Total: **28 keys** en la tabla.

Para cada key se muestra el valor actual (truncado si es sensible), dónde se **lee** y dónde se **escribe** en el código.

---

### `auto_import_activo`

**Valor actual:** `1`

**✏️ Escribe:**
- `app.py:L13785` → `execute_db("UPDATE configuracion SET valor = %s WHERE clave = 'auto_import_activo'",`
- `app.py:L13788` → `execute_db("INSERT INTO configuracion (clave, valor) VALUES ('auto_import_activo', %s)",`

**👁️ Lee:**
- `app.py:L1520` → `row_ai = query_db("SELECT valor FROM configuracion WHERE clave = 'auto_import_activo' LIMIT 1")`
- `app.py:L13644` → `row = query_db("SELECT valor FROM configuracion WHERE clave = 'auto_import_activo' LIMIT 1")`
- `app.py:L13783` → `existe = query_db("SELECT valor FROM configuracion WHERE clave = 'auto_import_activo' LIMIT 1")`

---

### `cco100_precio_cannon`

**Valor actual:** `183000`

**👁️ Lee:**
- `app.py:L14953` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15372` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15860` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L16148` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`

---

### `cco140_precio_cannon`

**Valor actual:** `205500`

**👁️ Lee:**
- `app.py:L14953` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15372` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15860` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L16148` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`

---

### `cco160_precio_cannon`

**Valor actual:** `251500`

**👁️ Lee:**
- `app.py:L14953` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15372` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15860` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L16148` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`

---

### `cco80_precio_cannon`

**Valor actual:** `144800`

**👁️ Lee:**
- `app.py:L14953` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15372` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L15860` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`
- `app.py:L16148` → `for _r in query_db("SELECT clave, valor FROM configuracion WHERE clave IN ('cco80_precio_cannon','cco100_precio_cannon','cco140_p…`

---

### `checkout_version`

**Valor actual:** `bricks`

**👁️ Lee:**
- `tienda_bp.py:L4467` → `_cur_cv.execute("SELECT valor FROM configuracion WHERE clave = 'checkout_version'")`

---

### `competencia_pasajes`

**Valor actual:** `{"colchon": [[3, 6], [6, 9], [9, 12], [12, 18]], "sommier": [[3, 6], [6, 9], [9,…` _(truncado, 122 chars)_

_Sin uso detectado en el código._

---

### `competencia_running`

**Valor actual:** `0`

_Sin uso detectado en el código._

---

### `costo_delega`

**Valor actual:** `5000`

**✏️ Escribe:**
- `app.py:L15302` → `execute_db("UPDATE configuracion SET valor=%s WHERE clave='costo_delega'",       [str(int(costo_del))])`

**👁️ Lee:**
- `app.py:L13469` → `_row_del = query_one("SELECT valor FROM configuracion WHERE clave='costo_delega'")`
- `app.py:L13502` → `_r = query_one("SELECT valor FROM configuracion WHERE clave='costo_delega'")`
- `app.py:L15120` → `r_del = query_one("SELECT valor FROM configuracion WHERE clave='costo_delega'")`
- `app.py:L15159` → `r_del = query_one("SELECT valor FROM configuracion WHERE clave='costo_delega'")`
- `app.py:L15300` → `costo_del = float(request.form.get('costo_delega', 5000))`

---

### `costo_flete_propio`

**Valor actual:** `35000`

**✏️ Escribe:**
- `app.py:L15301` → `execute_db("UPDATE configuracion SET valor=%s WHERE clave='costo_flete_propio'", [str(int(costo_fp))])`

**👁️ Lee:**
- `app.py:L13460` → `_row_fp = query_one("SELECT valor FROM configuracion WHERE clave='costo_flete_propio'")`
- `app.py:L13495` → `_r = query_one("SELECT valor FROM configuracion WHERE clave='costo_flete_propio'")`
- `app.py:L15119` → `r_fp  = query_one("SELECT valor FROM configuracion WHERE clave='costo_flete_propio'")`
- `app.py:L15158` → `r_fp  = query_one("SELECT valor FROM configuracion WHERE clave='costo_flete_propio'")`
- `app.py:L15299` → `costo_fp  = float(request.form.get('costo_flete_propio', 35000))`

---

### `ctr80_precio_cannon`

**Valor actual:** `72500`

**✏️ Escribe:**
- `app.py:L15820` → `INSERT INTO configuracion (clave, valor) VALUES ('ctr80_precio_cannon', %s)`

**👁️ Lee:**
- `app.py:L14826` → `ctr80_row = query_one("SELECT valor FROM configuracion WHERE clave = 'ctr80_precio_cannon'")`
- `app.py:L14949` → `ctr80_row = query_one("SELECT valor FROM configuracion WHERE clave = 'ctr80_precio_cannon'")`
- `app.py:L15368` → `ctr80_row = query_one("SELECT valor FROM configuracion WHERE clave = 'ctr80_precio_cannon'")`
- `app.py:L15857` → `ctr80_row = query_one("SELECT valor FROM configuracion WHERE clave = 'ctr80_precio_cannon'")`
- `app.py:L16144` → `ctr80_row = query_one("SELECT valor FROM configuracion WHERE clave = 'ctr80_precio_cannon'")`

---

### `cuotas_3_coef`

**Valor actual:** `1.2`

**✏️ Escribe:**
- `app.py:L16708` → `"INSERT INTO configuracion (clave, valor) VALUES ('cuotas_3_coef', %s) ON DUPLICATE KEY UPDATE valor=%s",`

**👁️ Lee:**
- `app.py:L16639` → `coef_3_row = query_one("SELECT valor FROM configuracion WHERE clave='cuotas_3_coef'")`
- `tienda_bp.py:L2060` → `cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('cuotas_3_coef','cuotas_6_coef')")`
- `tienda_bp.py:L2062` → `if row['clave'] == 'cuotas_3_coef':`

---

### `cuotas_6_coef`

**Valor actual:** `1.2`

**✏️ Escribe:**
- `app.py:L16712` → `"INSERT INTO configuracion (clave, valor) VALUES ('cuotas_6_coef', %s) ON DUPLICATE KEY UPDATE valor=%s",`

**👁️ Lee:**
- `app.py:L16640` → `coef_6_row = query_one("SELECT valor FROM configuracion WHERE clave='cuotas_6_coef'")`
- `tienda_bp.py:L2060` → `cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('cuotas_3_coef','cuotas_6_coef')")`
- `tienda_bp.py:L2064` → `elif row['clave'] == 'cuotas_6_coef':`

---

### `demora_sin_stock`

**Valor actual:** `10`

**✏️ Escribe:**
- `app.py:L16664` → `execute_db("INSERT INTO configuracion (clave, valor) VALUES ('demora_sin_stock', '0') ON DUPLICATE KEY UPDATE valor='0'")`
- `app.py:L16668` → `"INSERT INTO configuracion (clave, valor) VALUES ('demora_sin_stock', %s) ON DUPLICATE KEY UPDATE valor=%s",`

**👁️ Lee:**
- `app.py:L16631` → `demora_row = query_one("SELECT valor FROM configuracion WHERE clave='demora_sin_stock'")`
- `tienda_bp.py:L2140` → `cur.execute("SELECT valor FROM configuracion WHERE clave = 'demora_sin_stock'")`

---

### `faltantes_catalogo_cache`

**Valor actual:** `{"timestamp": "21/05/2026 12:32", "resultados": [{"sku": "CDO100", "faltantes": …` _(truncado, 59014 chars)_

**✏️ Escribe:**
- `app.py:L9162` → `execute_db("UPDATE configuracion SET valor = %s WHERE clave = 'faltantes_catalogo_cache'", (cache_data,))`
- `app.py:L9164` → `execute_db("INSERT INTO configuracion (clave, valor) VALUES ('faltantes_catalogo_cache', %s)", (cache_data,))`

**👁️ Lee:**
- `app.py:L9160` → `existing = query_one("SELECT 1 FROM configuracion WHERE clave = 'faltantes_catalogo_cache'")`
- `app.py:L9170` → `Guarda resultados en configuracion['faltantes_catalogo_cache'].`
- `app.py:L9307` → `cache_row = query_one("SELECT valor FROM configuracion WHERE clave = 'faltantes_catalogo_cache'")`

---

### `getnet_enabled`

**Valor actual:** `1`

**👁️ Lee:**
- `tienda_bp.py:L4492` → `_cur_gn.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('getnet_enabled', '0')")`
- `tienda_bp.py:L4494` → `_cur_gn.execute("SELECT valor FROM configuracion WHERE clave = 'getnet_enabled'")`

---

### `hot_email_envio_estado`

**Valor actual:** `completado_37ok_36err_20260511_120153`

**✏️ Escribe:**
- `app.py:L531` → `INSERT INTO configuracion (clave, valor) VALUES ('hot_email_envio_estado', %s)`
- `app.py:L551` → `INSERT INTO configuracion (clave, valor) VALUES ('hot_email_envio_estado', %s)`
- `app.py:L12887` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_envio_estado'")`
- `app.py:L12925` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_envio_estado'")`

**👁️ Lee:**
- `app.py:L416` → `Usa un LOCK ATÓMICO en la tabla configuracion (clave 'hot_email_envio_estado')`
- `app.py:L449` → `VALUES ('hot_email_envio_estado', 'no_iniciado')`
- `app.py:L464` → `WHERE clave = 'hot_email_envio_estado'`
- `app.py:L479` → `"SELECT valor FROM configuracion WHERE clave='hot_email_envio_estado'"`
- `app.py:L487` → `"SELECT valor FROM configuracion WHERE clave='hot_email_envio_estado'"`
- `app.py:L12941` → `"SELECT valor FROM configuracion WHERE clave='hot_email_envio_estado'"`

---

### `hot_email_envio_fallidos`

**Valor actual:** `[{"email": "lea_not@hotmail.com", "error": "{'lea_not@hotmail.com': (550, b'User…` _(truncado, 5544 chars)_

**✏️ Escribe:**
- `app.py:L538` → `INSERT INTO configuracion (clave, valor) VALUES ('hot_email_envio_fallidos', %s)`
- `app.py:L542` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_envio_fallidos'")`
- `app.py:L12888` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_envio_fallidos'")`
- `app.py:L12926` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_envio_fallidos'")`

**👁️ Lee:**
- `app.py:L565` → `'hot_email_envio_fallidos' (los que NO recibieron ninguna copia el lunes`
- `app.py:L637` → `"SELECT valor FROM configuracion WHERE clave='hot_email_envio_fallidos'"`
- `app.py:L12944` → `"SELECT valor FROM configuracion WHERE clave='hot_email_envio_fallidos'"`

---

### `hot_email_reenvio_estado`

**Valor actual:** `completado_36ok_0err_20260512_120132`

**✏️ Escribe:**
- `app.py:L684` → `INSERT INTO configuracion (clave, valor) VALUES ('hot_email_reenvio_estado', %s)`
- `app.py:L705` → `INSERT INTO configuracion (clave, valor) VALUES ('hot_email_reenvio_estado', %s)`
- `app.py:L12910` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_reenvio_estado'")`
- `app.py:L12931` → `execute_db("DELETE FROM configuracion WHERE clave='hot_email_reenvio_estado'")`

**👁️ Lee:**
- `app.py:L569` → `('hot_email_reenvio_estado'), también con UPDATE atómico para evitar`
- `app.py:L575` → `la entrada 'hot_email_reenvio_estado' desde el panel admin.`
- `app.py:L591` → `VALUES ('hot_email_reenvio_estado', 'no_iniciado')`
- `app.py:L605` → `WHERE clave = 'hot_email_reenvio_estado'`
- `app.py:L619` → `"SELECT valor FROM configuracion WHERE clave='hot_email_reenvio_estado'"`
- `app.py:L626` → `"SELECT valor FROM configuracion WHERE clave='hot_email_reenvio_estado'"`
- `app.py:L643` → `VALUES ('hot_email_reenvio_estado', 'completado_0ok_0err_sin_fallidos')`
- `app.py:L12947` → `"SELECT valor FROM configuracion WHERE clave='hot_email_reenvio_estado'"`

---

### `hot_event_activo`

**Valor actual:** `auto`

**👁️ Lee:**
- `tienda_bp.py:L2152` → `Valores soportados para 'hot_event_activo':`
- `tienda_bp.py:L2173` → `WHERE clave IN ('hot_event_activo', 'hot_event_fecha_inicio', 'hot_event_fecha_fin')`
- `tienda_bp.py:L2180` → `flag = config.get('hot_event_activo', '0').lower()`

---

### `hot_event_fecha_fin`

**Valor actual:** `2026-05-18 23:59:59`

**👁️ Lee:**
- `tienda_bp.py:L2156` → `'hot_event_fecha_inicio' y 'hot_event_fecha_fin'`
- `tienda_bp.py:L2173` → `WHERE clave IN ('hot_event_activo', 'hot_event_fecha_inicio', 'hot_event_fecha_fin')`
- `tienda_bp.py:L2186` → `fin_str    = config.get('hot_event_fecha_fin', '')`
- `tienda_bp.py:L2205` → `fin_str = config.get('hot_event_fecha_fin', '')`

---

### `hot_event_fecha_inicio`

**Valor actual:** `2026-05-11 00:00:00`

**👁️ Lee:**
- `tienda_bp.py:L2156` → `'hot_event_fecha_inicio' y 'hot_event_fecha_fin'`
- `tienda_bp.py:L2173` → `WHERE clave IN ('hot_event_activo', 'hot_event_fecha_inicio', 'hot_event_fecha_fin')`
- `tienda_bp.py:L2185` → `inicio_str = config.get('hot_event_fecha_inicio', '')`

---

### `ml_progress`

**Valor actual:** `{"running": false, "total": 2, "done": 0, "ok": [], "errors": [], "skus": ["PLAT…` _(truncado, 86 chars)_

**✏️ Escribe:**
- `app.py:L13888` → `"INSERT INTO configuracion (clave, valor) VALUES ('ml_progress', %s) "`

**👁️ Lee:**
- `app.py:L13899` → `row = query_db("SELECT valor FROM configuracion WHERE clave = 'ml_progress' LIMIT 1")`

---

### `ml_token`

**Valor actual:** `{"ac...0Z"}` _(sensible, censurado)_

**✏️ Escribe:**
- `app.py:L6724` → `"INSERT INTO configuracion (clave, valor) VALUES ('ml_token', %s) "`
- `app.py:L6773` → `"INSERT INTO configuracion (clave, valor) VALUES ('ml_token', %s) "`

**👁️ Lee:**
- `app.py:L6694` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'ml_token'")`
- `app.py:L6740` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'ml_token'")`
- `app.py:L6759` → `existing_json = query_one("SELECT valor FROM configuracion WHERE clave = 'ml_token'")`

---

### `nl_minimo`

**Valor actual:** `300000`

**✏️ Escribe:**
- `app.py:L16689` → `"INSERT INTO configuracion (clave, valor) VALUES ('nl_minimo', %s) ON DUPLICATE KEY UPDATE valor=%s",`

**👁️ Lee:**
- `app.py:L16635` → `nl_minimo_row = query_one("SELECT valor FROM configuracion WHERE clave='nl_minimo'")`
- `tienda_bp.py:L5710` → `cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('nl_monto','nl_minimo')")`
- `tienda_bp.py:L5713` → `return rows.get('nl_monto', 5000), rows.get('nl_minimo', 200000)`

---

### `nl_monto`

**Valor actual:** `10000`

**✏️ Escribe:**
- `app.py:L16685` → `"INSERT INTO configuracion (clave, valor) VALUES ('nl_monto', %s) ON DUPLICATE KEY UPDATE valor=%s",`

**👁️ Lee:**
- `app.py:L16634` → `nl_monto_row  = query_one("SELECT valor FROM configuracion WHERE clave='nl_monto'")`
- `tienda_bp.py:L5710` → `cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('nl_monto','nl_minimo')")`
- `tienda_bp.py:L5713` → `return rows.get('nl_monto', 5000), rows.get('nl_minimo', 200000)`

---

### `payway_6_enabled`

**Valor actual:** `0`

**👁️ Lee:**
- `tienda_bp.py:L4507` → `_cur_p6.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('payway_6_enabled', '0')")`
- `tienda_bp.py:L4509` → `_cur_p6.execute("SELECT valor FROM configuracion WHERE clave = 'payway_6_enabled'")`

---

### `porcentajes_ml`

**Valor actual:** `{"cuota_simple": 5, "cuotas_3": 8.8, "cuotas_6": 12.7, "cuotas_9": 15.9, "cuotas…` _(truncado, 91 chars)_

**✏️ Escribe:**
- `app.py:L1041` → `"INSERT INTO configuracion (clave, valor) VALUES ('porcentajes_ml', %s) "`

**👁️ Lee:**
- `app.py:L1025` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`
- `app.py:L8577` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`
- `app.py:L8903` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`
- `app.py:L9180` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`
- `app.py:L14751` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`
- `app.py:L15323` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`
- `app.py:L16057` → `row = query_one("SELECT valor FROM configuracion WHERE clave = 'porcentajes_ml'")`

---


## ⚠️ Keys sin uso detectado (2)

Podrían ser legacy o usarse desde otros archivos no escaneados.

- `competencia_pasajes`
- `competencia_running`
