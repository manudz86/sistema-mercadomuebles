#!/usr/bin/env python3
"""
generar_config_map.py — Genera CONFIG_MAP.md con todos los keys de la tabla
`configuracion`.

Para cada key muestra:
- Valor actual (truncado si parece sensible: tokens, secrets, etc.)
- Dónde se LEE en el código (app.py y tienda_bp.py)
- Dónde se ESCRIBE en el código

CONFIGURACIÓN:
  Igual que generar_db_schema.py: lee .env o variables de entorno.

USO:
  cd /home/cannon/app
  python scripts/generar_config_map.py

SALIDA: CONFIG_MAP.md en el directorio actual.

DEPENDENCIAS: pymysql
  Si falta:  pip install pymysql --break-system-packages
"""
import os
import re
import sys
from datetime import datetime

try:
    import pymysql
except ImportError:
    print("ERROR: falta pymysql. Instalar con: pip install pymysql --break-system-packages")
    sys.exit(1)


# ───────────────────────── CONFIG ─────────────────────────
DEFAULT_DB_HOST = 'localhost'
DEFAULT_DB_USER = 'root'
DEFAULT_DB_PASSWORD = ''
DEFAULT_DB_NAME = 'inventario_cannon'
DEFAULT_DB_PORT = 3306

SOURCE_FILES = ['app.py', 'tienda_bp.py']
OUTPUT_FILE = 'CONFIG_MAP.md'

# Keys cuyo valor se censura
SENSITIVE_PATTERNS = ('token', 'password', 'secret', 'apikey', 'api_key', 'private')

# Si el valor visible supera esto, se trunca
VALUE_PREVIEW_CHARS = 80


# ─────────────────────── .env ───────────────────────
def load_env_file(path='.env'):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env_file()

DB_HOST = os.environ.get('DB_HOST', DEFAULT_DB_HOST)
DB_USER = os.environ.get('DB_USER', DEFAULT_DB_USER)
DB_PASSWORD = os.environ.get('DB_PASSWORD', DEFAULT_DB_PASSWORD)
DB_NAME = os.environ.get('DB_NAME', DEFAULT_DB_NAME)
DB_PORT = int(os.environ.get('DB_PORT', DEFAULT_DB_PORT))


# ─────────────────────── HELPERS ───────────────────────
def get_conn():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, port=DB_PORT,
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
    )


def detect_columns(cur):
    """Detecta cómo se llaman las columnas key/value en la tabla configuracion."""
    cur.execute("SHOW COLUMNS FROM configuracion")
    cols = [c['Field'] for c in cur.fetchall()]
    key_col = next((c for c in ('clave', 'key', 'nombre', 'config_key', 'k') if c in cols), None)
    val_col = next((c for c in ('valor', 'value', 'config_value', 'v') if c in cols), None)
    return key_col, val_col, cols


def is_sensitive(key):
    k = key.lower()
    return any(p in k for p in SENSITIVE_PATTERNS)


def preview_value(key, value):
    if value is None:
        return '_(NULL)_'
    s = str(value)
    if not s:
        return '_(vacío)_'
    if is_sensitive(key) and len(s) > 10:
        return f"`{s[:4]}...{s[-4:]}` _(sensible, censurado)_"
    if len(s) > VALUE_PREVIEW_CHARS:
        return f"`{s[:VALUE_PREVIEW_CHARS]}…` _(truncado, {len(s)} chars)_"
    # escape pipes for markdown safety
    return f"`{s}`"


def load_sources():
    out = {}
    for f in SOURCE_FILES:
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as fp:
                out[f] = fp.readlines()
    return out


def find_usages(key, sources):
    """Devuelve lista de (archivo, lineno, linea) donde aparece 'key' o \"key\"."""
    usages = []
    patterns = [f"'{key}'", f'"{key}"']
    for fname, lines in sources.items():
        for i, line in enumerate(lines, 1):
            if any(p in line for p in patterns):
                usages.append((fname, i, line.rstrip()))
    return usages


def classify(line):
    """R = lectura, W = escritura. Heurística simple."""
    l = line.lower()
    write_indicators = (
        'insert into configuracion', 'update configuracion',
        'replace into configuracion', 'delete from configuracion',
    )
    if any(w in l for w in write_indicators):
        return 'W'
    return 'R'


def trim_line(line, max_chars=130):
    line = line.strip()
    if len(line) > max_chars:
        return line[:max_chars - 1] + '…'
    return line


# ─────────────────────── MAIN ───────────────────────
def main():
    print(f"→ Conectando a {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}...")
    try:
        conn = get_conn()
    except Exception as e:
        print(f"ERROR al conectar: {e}")
        sys.exit(1)

    cur = conn.cursor()
    key_col, val_col, cols = detect_columns(cur)

    if not key_col or not val_col:
        print(f"ERROR: no detecté columnas key/value en `configuracion`.")
        print(f"Columnas disponibles: {cols}")
        print("Editá detect_columns() en este script con los nombres reales.")
        sys.exit(1)

    print(f"→ Detectadas columnas: key=`{key_col}`, value=`{val_col}`")

    cur.execute(
        f"SELECT `{key_col}` AS k, `{val_col}` AS v FROM configuracion "
        f"ORDER BY `{key_col}`"
    )
    rows = cur.fetchall()
    print(f"→ {len(rows)} keys en configuracion")

    cur.close()
    conn.close()

    sources = load_sources()
    if not sources:
        print(f"WARNING: no encontré ninguno de los archivos {SOURCE_FILES}")
        print("Corré el script desde la raíz del proyecto.")

    print(f"→ Archivos fuente cargados: {list(sources.keys())}\n")

    out = [
        "# 🔧 CONFIG_MAP — Tabla `configuracion`",
        "",
        f"Generado automáticamente por `scripts/generar_config_map.py` "
        f"el {datetime.now().strftime('%Y-%m-%d %H:%M')}. **No editar a mano.**",
        "",
        f"Total: **{len(rows)} keys** en la tabla.",
        "",
        "Para cada key se muestra el valor actual (truncado si es sensible), "
        "dónde se **lee** y dónde se **escribe** en el código.",
        "",
        "---",
        "",
    ]

    sin_uso = []

    for row in rows:
        key = row['k']
        value = row['v']
        print(f"  · {key}")

        out.append(f"### `{key}`")
        out.append("")
        out.append(f"**Valor actual:** {preview_value(key, value)}")
        out.append("")

        usages = find_usages(key, sources)
        if not usages:
            out.append("_Sin uso detectado en el código._")
            out.append("")
            sin_uso.append(key)
        else:
            writes, reads = [], []
            for fname, lineno, line in usages:
                entry = f"`{fname}:L{lineno}` → `{trim_line(line)}`"
                (writes if classify(line) == 'W' else reads).append(entry)

            if writes:
                out.append("**✏️ Escribe:**")
                for w in writes:
                    out.append(f"- {w}")
                out.append("")
            if reads:
                out.append("**👁️ Lee:**")
                MAX_READS = 12
                for r in reads[:MAX_READS]:
                    out.append(f"- {r}")
                if len(reads) > MAX_READS:
                    out.append(f"- _(...{len(reads) - MAX_READS} usos más)_")
                out.append("")

        out.append("---")
        out.append("")

    if sin_uso:
        out.append("")
        out.append(f"## ⚠️ Keys sin uso detectado ({len(sin_uso)})")
        out.append("")
        out.append("Podrían ser legacy o usarse desde otros archivos no escaneados.")
        out.append("")
        for k in sin_uso:
            out.append(f"- `{k}`")
        out.append("")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    print(f"\n✓ Generado: {OUTPUT_FILE}")
    if sin_uso:
        print(f"  (con {len(sin_uso)} keys sin uso detectado — listadas al final)")


if __name__ == '__main__':
    main()
