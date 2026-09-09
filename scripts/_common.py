"""Helpers compartidos por los scripts de consulta (scripts/q.py, scripts/ml.py).

Estos scripts son SOLO LECTURA a propósito: existen para que las investigaciones
(SQL y API de ML) sean un comando estable y repetible, y así puedan autorizarse
una sola vez en vez de pedir permiso en cada consulta.
"""
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(APP_DIR, 'config', '.env')


def cargar_env():
    """Lee config/.env y devuelve un dict (no imprime valores: hay secrets)."""
    env = {}
    try:
        with open(ENV_PATH) as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith('#') and '=' in ln:
                    k, v = ln.split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


def conectar_db(solo_lectura=True):
    """Conexión a MySQL. Por defecto usa el usuario de SOLO LECTURA (DB_RO_USER);
    si no está configurado, cae al usuario normal."""
    import pymysql
    env = cargar_env()
    user = env.get('DB_RO_USER') if solo_lectura else None
    pwd = env.get('DB_RO_PASSWORD') if solo_lectura else None
    if not user:
        user = env.get('DB_USER', 'root')
        pwd = env.get('DB_PASSWORD', '')
    return pymysql.connect(
        host=env.get('DB_HOST', 'localhost'),
        user=user, password=pwd,
        database=env.get('DB_NAME', 'inventario_cannon'),
        cursorclass=pymysql.cursors.DictCursor,
    )


def ml_token():
    """access_token de Mercado Libre (vive en configuracion['ml_token'])."""
    import json
    db = conectar_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave='ml_token'")
        row = cur.fetchone()
        cur.close()
    finally:
        db.close()
    if not row:
        raise SystemExit('No hay ml_token configurado en la tabla configuracion.')
    return json.loads(row['valor'])['access_token']


def imprimir_tabla(filas, max_ancho=60):
    """Imprime una lista de dicts como tabla alineada."""
    if not filas:
        print('(sin resultados)')
        return
    cols = list(filas[0].keys())
    def s(v):
        t = '' if v is None else str(v)
        t = t.replace('\n', ' ')
        return t if len(t) <= max_ancho else t[:max_ancho - 1] + '…'
    anchos = {c: max(len(c), *(len(s(f.get(c))) for f in filas)) for c in cols}
    print('  '.join(c.ljust(anchos[c]) for c in cols))
    print('  '.join('-' * anchos[c] for c in cols))
    for f in filas:
        print('  '.join(s(f.get(c)).ljust(anchos[c]) for c in cols))
    print(f'\n({len(filas)} fila{"s" if len(filas) != 1 else ""})')
