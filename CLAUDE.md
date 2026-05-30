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
- La carpeta `backups/` está en `.gitignore` (los backups NO se commitean).
- Nunca borrar ni modificar lo que ya está en `backups/`.

## Flujo de trabajo (obligatorio)
1. **Pensar primero.** Entender bien el cambio pedido y revisar los mapas y el código real antes de proponer nada.
2. **Presentar la idea**: qué archivos se van a tocar, qué se va a cambiar y por qué. Si algo es ambiguo, hacer 1–2 preguntas concretas en vez de asumir.
3. **Esperar mi autorización explícita.** No editar nada antes de mi OK.
4. Con mi OK: **backup** de cada archivo → hacer los cambios → **chequeo de sintaxis** (`python -m py_compile <archivo>` para `.py`; parseo Jinja2 para templates) → **diff** mostrándome que solo cambiaron las líneas previstas (cero borrados no intencionales).
5. `git add` (rutas explícitas, nunca `git add .`) + `git commit` + `git push`. Esto es solo respaldo/versionado: **no afecta lo que está corriendo**.
6. **Reiniciar = paso aparte, con confirmación.** El cambio NO entra en vivo hasta reiniciar (`--reload` está apagado). Reiniciar afecta a **tienda Y sistema** (es un solo proceso), así que: pedir confirmación, hacerlo en horario tranquilo, y una sola vez al final si hubo varios cambios:

```
systemctl restart cannon && systemctl is-active cannon
```

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
