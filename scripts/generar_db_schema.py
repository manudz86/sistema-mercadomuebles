#!/usr/bin/env python3
"""
generar_db_schema.py — Genera DB_SCHEMA.md con el schema completo de la BD.

Para cada tabla muestra:
- Cantidad de filas
- Todas las columnas con tipo, null, key, default, comentario
- Valores típicos de columnas tipo "enum implícito" (varchar con pocos valores
  distintos): útil para conocer estados, canales, métodos, etc.

CONFIGURACIÓN:
  Lee credenciales de un archivo .env (formato KEY=value) si existe en el CWD,
  o de variables de entorno. Si no hay nada, usa los defaults de abajo.

USO:
  cd /home/cannon/app
  python scripts/generar_db_schema.py

SALIDA: DB_SCHEMA.md en el directorio actual.

DEPENDENCIAS: pymysql
  Si falta:  pip install pymysql --break-system-packages
"""
import os
import sys
from datetime import datetime

try:
    import pymysql
except ImportError:
    print("ERROR: falta pymysql. Instalar con: pip install pymysql --break-system-packages")
    sys.exit(1)


# ───────────────────────── CONFIG ─────────────────────────
# Estos valores se sobreescriben si encontrás .env o variables de entorno
DEFAULT_DB_HOST = 'localhost'
DEFAULT_DB_USER = 'root'
DEFAULT_DB_PASSWORD = ''
DEFAULT_DB_NAME = 'inventario_cannon'
DEFAULT_DB_PORT = 3306

OUTPUT_FILE = 'DB_SCHEMA.md'

# Si una columna tiene <= este número de valores distintos, se listan todos.
MAX_DISTINCT_FOR_ENUM = 20

# Columnas que NO se analizan para valores típicos (datos libres, sensibles, etc.)
SKIP_COLUMN_KEYWORDS = (
    'id', 'fecha', 'created', 'updated', 'date', 'time',
    'token', 'password', 'secret', 'hash',
    'email', 'telefono', 'direccion', 'domicilio',
    'nota', 'comentario', 'observacion', 'descripcion',
    'json', 'payload', 'response', 'url', 'link',
    # IDs / identificadores únicos (no son enums reales)
    'sku', 'nombre', 'cliente', 'filename', 'username',
    'codigo', 'numero', 'nro', 'clave', 'titulo', 'permalink',
)

# Tipos de columna que NO se analizan (texto largo, blobs, números)
SKIP_TYPE_KEYWORDS = (
    'text', 'blob', 'json',
    'int', 'decimal', 'float', 'double', 'numeric',
    'datetime', 'timestamp', 'date', 'time',
)


# ─────────────────────── LECTURA .env ───────────────────────
def load_env_file(path='.env'):
    """Carga un .env simple (KEY=value por línea) en os.environ sin sobreescribir."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


# Carga primero config/.env (donde lo guarda este proyecto), luego .env (raíz)
# como fallback. setdefault hace que el primero gane.
load_env_file('config/.env')
load_env_file('.env')

DB_HOST = os.environ.get('DB_HOST', DEFAULT_DB_HOST)
DB_USER = os.environ.get('DB_USER', DEFAULT_DB_USER)
DB_PASSWORD = os.environ.get('DB_PASSWORD', DEFAULT_DB_PASSWORD)
DB_NAME = os.environ.get('DB_NAME', DEFAULT_DB_NAME)
DB_PORT = int(os.environ.get('DB_PORT', DEFAULT_DB_PORT))


# ─────────────────────── HELPERS ───────────────────────
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_all_tables(cur):
    cur.execute("SHOW TABLES")
    return [list(r.values())[0] for r in cur.fetchall()]


def get_columns(cur, table):
    cur.execute(f"SHOW FULL COLUMNS FROM `{table}`")
    return cur.fetchall()


def get_row_count(cur, table):
    try:
        cur.execute(f"SELECT COUNT(*) AS c FROM `{table}`")
        return cur.fetchone()['c']
    except Exception:
        return 0


def is_analyzable(col_name, col_type):
    """Decide si vale la pena buscar valores distintos en esta columna."""
    name_lower = col_name.lower()
    type_lower = col_type.lower()
    if any(k in name_lower for k in SKIP_COLUMN_KEYWORDS):
        return False
    if any(t in type_lower for t in SKIP_TYPE_KEYWORDS):
        return False
    return True


def get_distinct_values(cur, table, column, limit):
    """Top valores distintos con su count. Si hay > limit, devuelve None (no es enum)."""
    try:
        cur.execute(
            f"SELECT `{column}` AS v, COUNT(*) AS c FROM `{table}` "
            f"WHERE `{column}` IS NOT NULL "
            f"GROUP BY `{column}` ORDER BY c DESC LIMIT {limit + 1}"
        )
        rows = cur.fetchall()
        if len(rows) > limit:
            return None  # demasiados valores distintos, no es un enum implícito
        return rows
    except Exception:
        return None


def format_val(v):
    if v is None:
        return 'NULL'
    s = str(v)
    if len(s) > 50:
        return s[:47] + '...'
    return s


# ─────────────────────── RENDER ───────────────────────
def render_table(cur, table):
    out = []
    columns = get_columns(cur, table)
    rows = get_row_count(cur, table)

    out.append(f"## `{table}`  _(filas: {rows:,})_\n")

    out.append("| Columna | Tipo | Null | Key | Default | Comentario |")
    out.append("|---|---|---|---|---|---|")
    for c in columns:
        default = c.get('Default')
        default_str = '' if default is None else f"`{default}`"
        comment = (c.get('Comment') or '').replace('|', '\\|')
        out.append(
            f"| `{c['Field']}` | `{c['Type']}` | {c['Null']} | {c['Key']} "
            f"| {default_str} | {comment} |"
        )
    out.append("")

    # Análisis de enums implícitos
    if rows > 0:
        enum_lines = []
        for c in columns:
            if not is_analyzable(c['Field'], c['Type']):
                continue
            values = get_distinct_values(cur, table, c['Field'], MAX_DISTINCT_FOR_ENUM)
            if not values:
                continue
            # Si todos los valores aparecen solo 1 vez, no es un enum: son IDs únicos
            if len(values) > 1 and all(v['c'] == 1 for v in values):
                continue
            val_strs = [f"`{format_val(v['v'])}` ({v['c']:,})" for v in values]
            enum_lines.append(f"- **`{c['Field']}`** → {', '.join(val_strs)}")

        if enum_lines:
            out.append("**Valores típicos (enums implícitos):**\n")
            out.extend(enum_lines)
            out.append("")

    return '\n'.join(out)


# ─────────────────────── MAIN ───────────────────────
def main():
    print(f"→ Conectando a {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}...")
    try:
        conn = get_conn()
    except Exception as e:
        print(f"ERROR al conectar: {e}")
        sys.exit(1)

    cur = conn.cursor()
    tables = get_all_tables(cur)
    print(f"→ {len(tables)} tablas encontradas\n")

    out = [
        "# 🗄️ DB_SCHEMA — Schema completo de la BD",
        "",
        f"Generado automáticamente por `scripts/generar_db_schema.py` "
        f"el {datetime.now().strftime('%Y-%m-%d %H:%M')}. **No editar a mano.**",
        "",
        f"Base de datos: `{DB_NAME}` — {len(tables)} tablas",
        "",
        "Cada tabla muestra: cantidad de filas, todas las columnas con tipo, "
        "y los **valores típicos** de columnas que parecen enum implícito "
        "(útil para conocer estados, canales, métodos, etc.).",
        "",
        "---",
        "",
    ]

    for t in tables:
        print(f"  · {t}")
        out.append(render_table(cur, t))
        out.append("---\n")

    cur.close()
    conn.close()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    print(f"\n✓ Generado: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
