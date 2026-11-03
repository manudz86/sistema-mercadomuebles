# CLAUDE.md — Sistema Cannon (sistema + tienda)

## Qué es esto
Aplicación Flask/Python con MySQL (`inventario_cannon`), servida por **un solo proceso Gunicorn** (servicio systemd `cannon`, puerto 5000) en `/home/cannon/app` (VPS `root@72.61.134.243`). Una misma app Flask sirve dos cosas:

- **Sistema** (panel admin interno): `app.py` + blueprints (`whatsapp_bp.py`, `competencia_bp.py`, `bot_precios_bp.py`, `competencia_scraper_bp.py`). URL: `sistema.mercadomuebles.com.ar`
- **Tienda** (pública, cobra con MP / Payway / GetNet): `tienda_bp.py` + `templates/tienda/`. URL: `mercadomuebles.com.ar`

> ⚠️ La tienda es un sitio EN VIVO que procesa pagos reales. Cambios conservadores, mínimos y cuidadosos. Ante la duda, hacer menos.

## Contexto — leer estos mapas antes de trabajar
- `STACK_CONTEXT.md` — stack, infraestructura, deploy, integraciones
- `SYSTEM_MAP.md` — rutas HTTP y helpers (con nº de línea)
- `DB_MAP.md` — qué función lee/escribe cada tabla
- `DB_SCHEMA.md` — esquema de la base
- `CONFIG_MAP.md` — keys de la tabla `configuracion`
- `GLOSSARY.md` — prefijos, estados y reglas del dominio (manual, no autogenerado)
- `INTEGRATIONS.md` — integraciones externas (Mercado Libre, MP, Payway, GetNet, Zipnova, WhatsApp)

(Todos los mapas salvo `GLOSSARY.md` se autogeneran con `scripts/generar_mapas.py` — no editarlos a mano.)

## REGLA INNEGOCIABLE — Backup antes de editar
Antes de modificar CUALQUIER archivo existente, copiarlo a `backups/` con fecha y hora:

```
cp -a "<archivo>" "backups/$(basename "<archivo>")_$(date +%Y%m%d_%H%M%S).bak"
```

- Nunca editar un archivo sin haber hecho el backup primero.
- **El backup NO se pide ni se pregunta: se hace.** Hay un hook `PreToolUse` (`scripts/hook_backup.py`) que respalda solo en cada Edit/Write, y queda registrado en `backups/_hook_backup.log`. Si el archivo se modifica por fuera de Edit/Write, hacer el `cp -a` a mano antes.
- La carpeta `backups/` está en `.gitignore` (los backups NO se commitean).
- Nunca borrar ni modificar lo que ya está en `backups/`.

## Qué necesita mi autorización (y qué no)
Solo dos cosas:

1. **Escribir en la base de datos de producción** (`UPDATE` / `DELETE` / `INSERT`, `ALTER`, migraciones).
2. **Reiniciar el servicio** (`systemctl restart cannon`).

Todo lo demás va de corrido, sin preguntarme: leer, buscar, backupear, editar, compilar, parsear templates, correr pruebas y diagnósticos, mostrar el diff, `git add` / `commit` / `push`. Lo mismo para los `PUT`/`POST` a la API de ML que cambian publicaciones reales: esos sí, avisar antes.

## Flujo de trabajo
1. **Pensar primero.** Entender el cambio pedido y revisar los mapas y el código real antes de escribir nada.
2. **Decir qué vas a hacer** — qué archivos, qué cambia y por qué — y seguir. No hace falta esperar un OK para código. Si algo es genuinamente ambiguo (dos lecturas que llevan a trabajos distintos), preguntar 1–2 cosas concretas; si no, elegir la opción razonable, decirla y avanzar.
3. De corrido: **backup** (lo hace el hook) → cambios → **chequeo de sintaxis** (`py_compile` para `.py`, parseo Jinja2 para templates) → **prueba** cuando la lógica lo amerite → **diff** mostrando que solo cambiaron las líneas previstas → `git add` (rutas explícitas, nunca `git add .`) + `commit` + `push`. El push es respaldo/versionado: **no afecta lo que está corriendo**.
4. **Frenar solo si aparece algo que invalida el plan** (otro enfoque, otro archivo, un hallazgo que cambia el diagnóstico). Ahí sí contarlo antes de seguir.
5. **Reiniciar = paso aparte, con confirmación.** El cambio NO entra en vivo hasta reiniciar (`--reload` está apagado). Reiniciar afecta a **tienda Y sistema** (es un solo proceso), así que: pedir confirmación, chequear que no haya nadie en el embudo de compra, y una sola vez al final si hubo varios cambios:

```
systemctl restart cannon && systemctl is-active cannon
```

## Cómo ejecutar comandos (para no generar autorizaciones de más)
La allowlist de `.claude/settings.local.json` matchea por **texto del comando**, y en un comando compuesto alcanza con que una parte no esté permitida para que pregunte. Estas costumbres la anulan — medidas sobre una sesión real, explican casi todos los permisos de más:

- **Nada de Python inline.** Ni `-c "..."` ni heredocs (`venv/bin/python3 - <<'PY'`). Son texto único: no matchean ningún patrón, nunca. Si hace falta lógica, escribirla **una vez** en `scripts/` y ejecutarla.
- **Nada de `timeout N ...` como prefijo.** El tool Bash ya tiene su propio parámetro `timeout`; el prefijo rompe el match de todo el comando.
- **Nada de `sed -i` ni `tee` para editar** — usar Edit/Write, que disparan el hook de backup. `sed -i` edita salteándolo.
- **No usar `cd`.** El directorio de trabajo ya es `/home/cannon/app`.
- **Nada de loops de shell** (`for f in ...; do`) ni `set -a`. Si hace falta iterar, un script en `scripts/`.
- **Nombrar los scripts con los prefijos preautorizados**: `probar_`, `auditar_`, `verificar_`, `validar_`, `analizar_`, `revisar_`, `check_`, `diag_`, `generar_`. Un script de diagnóstico con nombre libre pide permiso cada vez. Los que escriben en producción o en ML van **sin** esos prefijos, a propósito, para que pidan autorización.
- **Agrupar** los comandos independientes en una sola llamada en vez de encadenar muchas chicas.
- `venv/bin/python` y `venv/bin/python3` están los dos permitidos: son el mismo intérprete.

Herramientas preautorizadas para investigar: `scripts/q.py` (SQL de solo lectura, con usuario `cannon_ro` sin permiso de escritura), `scripts/ml.py` (GET a la API de ML), `scripts/dump.py` (backup de tablas antes de escribir en la DB).

Para medir si esto se está cumpliendo: `scripts/verificar_permisos.py` pasa todos los comandos de una sesión por la allowlist real y dice cuántos no matchean y por qué.

## Estilo de cambios
- **Quirúrgicos y mínimos.** No refactorizar, no renombrar, no reorganizar, no "modularizar" sin que lo pida. El código es un monolito grande y por ahora se mantiene así a propósito.
- Devolver el archivo completo modificado cuando se pida. Comentar solo lo no obvio.
- En lógica nueva: validar entradas y manejar errores razonablemente. No agregar scaffolding de tests salvo que lo pida.
- Después de cada cambio, verificar que no se rompió nada anterior en el archivo.

## Base de datos y APIs
- Las queries `SELECT` son libres. Cualquier `UPDATE` / `DELETE` / `INSERT` sobre datos de producción: primero mostrarme un `SELECT` de preview + esperar mi OK + backup de la tabla afectada.
- Pasar las queries SQL/MySQL en **una sola línea** y con el comando `mysql` adelante (formato: `mysql ... -e "..."`).
- API de Mercado Libre: los `GET` son libres; los `PUT` / `POST` que cambian stock, precios o publicaciones reales requieren confirmación previa.

## No commitear ni borrar
`backups/`, `venv/`, `__pycache__/`, `config/.env`, `config/ml_token.json` y demás secrets, `data/` (CSVs del scraper), imágenes subidas en `static/img/`.
(`migrations/` y `sqls/` SÍ van trackeadas — son esquema/historial real, no tocar a la ligera.)
