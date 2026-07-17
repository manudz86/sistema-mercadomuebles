"""
competencia_scraper_bp.py
Panel de monitoreo de competencia ML con detección automática de pasajes.

Endpoints:
  GET  /admin/competencia-scraper                — panel HTML
  GET  /admin/competencia-scraper/sondas/lista   — JSON con sondas activas (auth)
  POST /admin/competencia-scraper/upload         — recibe CSVs y procesa
"""
import os, csv, json, datetime, statistics, re, hmac
from functools import wraps
from collections import defaultdict
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from dotenv import load_dotenv

load_dotenv('config/.env')

import pymysql
from procesar_competencia import procesar
from scraper_alerts import alerta_falla_scraper
import competencia_informe as ci

competencia_scraper_bp = Blueprint('competencia_scraper', __name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CSV_PATH        = os.path.join(DATA_DIR, 'competencia_procesado.csv')
CSV_CRUDO_PATH  = os.path.join(DATA_DIR, 'competencia_crudo.csv')
SONDAS_RES_PATH = os.path.join(DATA_DIR, 'sondas_resultado.csv')

# Pasajes por defecto si nunca se detectaron sondas (fallback)
PASAJES_DEFAULT = {
    'colchon':  [(3, 6), (6, 9), (9, 12), (12, 18)],
    'sommier':  [(3, 6), (6, 9), (9, 12), (12, 18)],
    'almohada': [(3, 6), (6, 9), (9, 12), (12, 18)],
}


def _token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        expected = os.getenv('SCRAPER_TOKEN', '')
        provided = request.headers.get('X-Scraper-Token', '')
        if not expected or not hmac.compare_digest(provided, expected):
            return jsonify({'error': 'unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper


# ============================================================================
# Utilidades de BD
# ============================================================================
def _db():
    return pymysql.connect(
        host='localhost', user='cannon',
        password=os.environ.get('DB_PASSWORD', 'Sistema@32267845'),
        db='inventario_cannon', charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def cargar_pasajes_activos():
    """Lee los pasajes de la tabla configuracion (clave=competencia_pasajes).
    Si no existe, devuelve los defaults."""
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave = 'competencia_pasajes'")
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return PASAJES_DEFAULT, None
        data = json.loads(row['valor'])
        pasajes = {
            'colchon':  [tuple(p) for p in data.get('colchon', [])],
            'sommier':  [tuple(p) for p in data.get('sommier', [])],
            'almohada': [tuple(p) for p in data.get('almohada', [])],
        }
        return pasajes, data.get('detectado_en')
    except Exception:
        return PASAJES_DEFAULT, None


def guardar_pasajes(pasajes, detectado_en):
    """Upsert de los pasajes detectados en la tabla configuracion."""
    payload = json.dumps({
        'colchon':       [list(p) for p in pasajes.get('colchon', [])],
        'sommier':       [list(p) for p in pasajes.get('sommier', [])],
        'almohada':      [list(p) for p in pasajes.get('almohada', [])],
        'detectado_en':  detectado_en,
    })
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO configuracion (clave, valor) VALUES ('competencia_pasajes', %s)
        ON DUPLICATE KEY UPDATE valor = VALUES(valor)
    """, (payload,))
    conn.commit()
    cur.close(); conn.close()


def cargar_sondas_activas():
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, item_id_ml, tipo, cuotas_reales, sku_referencia, url
          FROM competencia_sondas
         WHERE activa = 1
         ORDER BY tipo, cuotas_reales
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def actualizar_sonda_resultado(item_id_ml, cuotas_mostradas):
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE competencia_sondas
           SET cuotas_mostradas_ultimo = %s, fecha_ultimo_scrape = NOW()
         WHERE item_id_ml = %s
    """, (cuotas_mostradas, item_id_ml))
    conn.commit()
    cur.close(); conn.close()


# ============================================================================
# Detección de pasajes a partir de los resultados de sondas
# ============================================================================
def detectar_pasajes_desde_sondas(sondas_csv_path):
    """
    Lee el CSV con resultados de sondas y deduce los pasajes activos.
    Una sonda con cuotas_reales=R y cuotas_mostradas=M (M != R) implica un pasaje R→M.
    Un par (0, N) significa que ML aplica un pasaje a publicaciones SIN cuotas s/i (raro).
    """
    pasajes = {'colchon': set(), 'sommier': set(), 'almohada': set()}
    if not os.path.exists(sondas_csv_path):
        return None

    with open(sondas_csv_path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                reales    = int(r['cuotas_reales'])
                mostradas = int(r['cuotas_mostradas'])
            except (ValueError, KeyError):
                continue
            actualizar_sonda_resultado(r['item_id_ml'], mostradas)
            if reales != mostradas and mostradas > 0:
                tipo = r['tipo']
                if tipo in pasajes:
                    pasajes[tipo].add((reales, mostradas))

    return {tipo: sorted(s) for tipo, s in pasajes.items()}


# ============================================================================
# Lógica de aplicación de pasajes a un valor de cuotas
# ============================================================================
def calcular_cuotas_real(cuotas_si, tipo, pasajes):
    """Dado el valor de cuotas_si MOSTRADO en la publicación (lo que se ve hoy en
    el listado de ML) y los pasajes activos, devuelve (cuotas_real, hubo_pasaje)."""
    if not cuotas_si:
        return ('', False)
    try:
        n = int(cuotas_si)
    except ValueError:
        return (cuotas_si, False)
    for desde, hasta in pasajes.get(tipo, []):
        if hasta == n:
            return (str(desde), True)
    return (str(n), False)


# Mapeo tienda (scraper) → seller_nick (monitor de catálogo)
TIENDA_NICK = {
    'TMS': 'TMS', 'Lanus': 'MUEBLESLANUS', 'Ivana': 'COLCHONERIA IVANA',
    'Ballester': 'BALLESTER', 'Bedpoint': 'BEDPOINT', 'Metymas': 'METYMAS',
}
def _cuota_label_num(lbl):
    """'6 cuotas s/interés' → '6'. Contado/Cuota Simple → None (no aplica override)."""
    l = (lbl or '').lower()
    if 'sin cuota' in l or l.startswith('cuota simple'):
        return None
    m = re.search(r'(\d+)', l)
    return m.group(1) if m else None

def _cuotas_reales_monitor():
    """{(sku_upper, seller_nick): [(precio_float, cuota_str), ...]} del último snapshot
    del monitor de catálogo, que trae la cuota REAL (lee listing_type/campaña)."""
    out = defaultdict(list)
    try:
        conn = _db(); cur = conn.cursor()
        cur.execute("SELECT MAX(DATE(fecha)) d FROM competencia_snapshots")
        row = cur.fetchone()
        d = row and row['d']
        if d:
            cur.execute("""SELECT sku, seller_nick, cuotas_efectivas, precio
                           FROM competencia_snapshots WHERE DATE(fecha)=%s""", (d,))
            for r in cur.fetchall():
                n = _cuota_label_num(r['cuotas_efectivas'])
                if not n:
                    continue
                out[(str(r['sku']).upper(), r['seller_nick'])].append((float(r['precio'] or 0), n))
        cur.close(); conn.close()
    except Exception as e:
        print(f"[scraper] error cargando cuotas del monitor: {e}")
    return out

def _cuota_real_desde_monitor(mon, sku, tienda, precio, cuotas_mostrada):
    """Si el monitor tiene esta publi (mismo sku+vendedor y precio cercano), devuelve
    su cuota REAL. Si no, None (se usa el pasaje). Matchea por precio (cada tramo de
    cuota tiene su propio precio), con tolerancia."""
    nick = TIENDA_NICK.get(tienda)
    if not nick or not sku or not precio:
        return None
    try:
        p = float(precio)
    except (TypeError, ValueError):
        return None
    cands = mon.get((str(sku).upper(), nick))
    if not cands:
        return None
    best = None
    for mp, mc in cands:
        if mp <= 0:
            continue
        diff = abs(mp - p)
        if diff / mp <= 0.03 and (best is None or diff < best[0]):   # 3% de tolerancia
            best = (diff, mc)
    return best[1] if best else None


# ── Cuota real desde el CATÁLOGO de cada publi (por su URL), cacheado por día ──
TIENDA_SELLER = {'TMS': 60351381, 'Lanus': 54898332, 'Ivana': 192769857,
                 'Ballester': 658910977, 'Bedpoint': 168211358, 'Metymas': 105539832}

def _catalog_id_de_url(url):
    m = re.search(r'/p/(MLA\d+)', url or '')
    return m.group(1) if m else None

def _catalog_cuota_query(catalog_id):
    """Consulta ML y devuelve [[seller_id, precio, cuota_str], ...]. Cachea por día."""
    try:
        from competencia_bp import _ml_catalog_all, _cuotas_publi, _campaign_from_tags
        res = _ml_catalog_all(catalog_id, '1425')
        out = []
        for r in res:
            lt = r.get('listing_type_id', '')
            camp = next((t.get('value_name', '').split('|')[0].strip()
                         for t in r.get('sale_terms', []) if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
            if not camp:
                camp = _campaign_from_tags(r.get('tags'))
            n = _cuota_label_num(_cuotas_publi(lt, camp))
            p = r.get('price') or 0
            if not n or p <= 0:
                continue
            out.append([r.get('seller_id'), float(p), n])
        conn = _db(); cur = conn.cursor()
        cur.execute("""INSERT INTO competencia_cat_cache (catalog_id, fecha, data)
                       VALUES (%s, CURDATE(), %s)
                       ON DUPLICATE KEY UPDATE fecha=CURDATE(), data=VALUES(data)""",
                    (catalog_id, json.dumps(out)))
        conn.commit(); cur.close(); conn.close()
        return out
    except Exception as e:
        print(f"[scraper] catálogo {catalog_id} error: {e}")
        return None

def _catalog_cuota_cached(catalog_id):
    """Lee del cache (solo del día). Sin llamadas a ML. None si no está cacheado."""
    try:
        conn = _db(); cur = conn.cursor()
        cur.execute("SELECT data FROM competencia_cat_cache WHERE catalog_id=%s AND fecha=CURDATE()", (catalog_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        return json.loads(row['data']) if (row and row['data']) else None
    except Exception:
        return None

def _cuota_real_desde_catalogo(url, tienda, precio, memo):
    """Cuota real del catálogo de la publi (matcheando seller+precio). Usa cache del día."""
    sid = TIENDA_SELLER.get(tienda)
    cid = _catalog_id_de_url(url)
    if not sid or not cid or not precio:
        return None
    try: p = float(precio)
    except (TypeError, ValueError): return None
    if cid not in memo:
        memo[cid] = _catalog_cuota_cached(cid)   # None si no está cacheado
    data = memo[cid]
    if not data:
        return None
    best = None
    for s, mp, mc in data:
        if s == sid and mp > 0:
            diff = abs(mp - p)
            if diff / mp <= 0.03 and (best is None or diff < best[0]):
                best = (diff, mc)
    return best[1] if best else None

def prewarm_catalogos_scraper():
    """Consulta y cachea las cuotas reales de todos los catálogos del CSV (para el día).
    Se corre en background al subir un barrido; el display solo lee del cache."""
    if not os.path.exists(CSV_PATH):
        return 0
    cats = set()
    with open(CSV_PATH, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if (r.get('cuotas_si') or '').strip():
                cid = _catalog_id_de_url(r.get('url'))
                if cid and not _catalog_cuota_cached(cid):
                    cats.add(cid)
    for cid in cats:
        _catalog_cuota_query(cid)
    return len(cats)


# ============================================================================
# Carga de productos para el panel
# ============================================================================
def _cargar_productos():
    if not os.path.exists(CSV_PATH):
        return [], None
    pasajes, detectado_en = cargar_pasajes_activos()

    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Cuotas REALES: 1º monitor, 2º catálogo de la publi (cache), 3º pasaje
    mon_cuotas = _cuotas_reales_monitor()
    _cat_memo = {}

    grupos = defaultdict(list)
    for r in rows:
        grupos[(r['titulo_orig'], r['tienda'])].append(r)

    productos = []
    for (titulo, tienda), variantes in grupos.items():
        base = variantes[0]
        tipo = base['tipo']
        sku_m = base.get('sku_match', '')
        opciones = []
        for v in variantes:
            precio = v.get('precio', '') or ''
            cuotas_mostrada = v.get('cuotas_si', '') or ''
            cuotas_simple = v.get('cuotas_simple', '0') == '1'
            # 1º monitor, 2º catálogo de la publi, 3º pasaje
            cuota_ok = None; cuota_fuente = 'pasaje'
            if cuotas_mostrada:
                cuota_ok = _cuota_real_desde_monitor(mon_cuotas, sku_m, tienda, precio, cuotas_mostrada)
                if cuota_ok is not None:
                    cuota_fuente = 'monitor'
                else:
                    cuota_ok = _cuota_real_desde_catalogo(v.get('url', ''), tienda, precio, _cat_memo)
                    if cuota_ok is not None:
                        cuota_fuente = 'catalogo'
            if cuota_ok is not None:
                cuotas_real = cuota_ok
                hubo_pasaje = (cuotas_mostrada and cuotas_real != cuotas_mostrada)
            else:
                cuotas_real, hubo_pasaje = calcular_cuotas_real(cuotas_mostrada, tipo, pasajes)
            if precio:
                opciones.append({
                    'precio':              precio,
                    'cuotas_si':           cuotas_real,
                    'cuotas_si_mostrada':  cuotas_mostrada,
                    'pasaje':              hubo_pasaje,
                    'cuotas_simple':       cuotas_simple,
                    'cuota_fuente':        cuota_fuente,
                })
        precio_min = min((int(o['precio']) for o in opciones if o['precio']), default=0)

        productos.append({
            'tienda':         tienda,
            'tipo':           tipo,
            'modelo':         base['modelo'],
            'medida':         base['medida'],
            'medida_origen':  base.get('medida_origen', 'explicita'),
            'almohadas':      base.get('almohadas', '0'),
            'pack':           base.get('pack', '1'),
            'sku_match':      base.get('sku_match', ''),
            'titulo':         titulo,
            'url':            base['url'],
            'opciones':       opciones,
            'precio_min':     precio_min,
            'fecha':          base.get('fecha', ''),
        })

    productos.sort(key=lambda x: (x['tienda'], x['modelo'], x['medida']))
    return productos, {'pasajes': pasajes, 'detectado_en': detectado_en}


def _get_filtros(productos):
    modelos = sorted(set(p['modelo'] for p in productos
                          if p['modelo'] not in ('DESCONOCIDO', '')))
    medidas = sorted(set(p['medida'] for p in productos
                          if p['medida'] and p['medida'] != '?'),
                     key=lambda x: (int(x.split('x')[0]) if 'x' in x else 999, x))
    # Tiendas dinámicas: cualquier tienda nueva en los datos aparece sola en el filtro.
    tiendas = sorted(set(p['tienda'] for p in productos if p.get('tienda')),
                     key=lambda x: x.lower())
    return modelos, medidas, tiendas


# ============================================================================
# Informe de competencia + histórico de precios
# ============================================================================
def _inv_pasajes():
    pasajes, _ = cargar_pasajes_activos()
    return ci.inv_desde_pasajes(pasajes)


def guardar_snapshot_hist():
    """Guarda un snapshot del día (precios representativos de competencia) en
    competencia_precios_hist. Idempotente por (fecha, tienda, sku, bucket).
    Devuelve la cantidad de filas del snapshot, o 0 si falló."""
    try:
        snap = ci.construir_snapshot(CSV_PATH, _inv_pasajes())
        if not snap:
            return 0
        hoy = datetime.date.today().isoformat()
        conn = _db()
        cur = conn.cursor()
        cur.executemany("""
            INSERT INTO competencia_precios_hist (fecha, tienda, sku, bucket, precio, n)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE precio = VALUES(precio), n = VALUES(n)
        """, [(hoy, s['tienda'], s['sku'], s['bucket'], s['precio'], s['n']) for s in snap])
        conn.commit()
        cur.close(); conn.close()
        return len(snap)
    except Exception as e:
        print(f"[competencia snapshot] error: {e}")
        return 0


def _hist_cambios():
    """Compara el último snapshot del histórico contra el anterior (sobre el contado).
    Devuelve mediana del % de cambio por tienda + los mayores saltos (posibles promos)."""
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT fecha FROM competencia_precios_hist ORDER BY fecha DESC LIMIT 2")
        fechas = [r['fecha'] for r in cur.fetchall()]
        if len(fechas) < 2:
            cur.close(); conn.close()
            return {'hay': False, 'fechas': [f.strftime('%d/%m/%Y') for f in fechas]}
        nueva, vieja = fechas[0], fechas[1]
        cur.execute("""
            SELECT fecha, tienda, sku, bucket, precio
              FROM competencia_precios_hist
             WHERE fecha IN (%s, %s) AND bucket = 'sin'
        """, (nueva, vieja))
        pn, pv = {}, {}
        for r in cur.fetchall():
            key = (r['tienda'], r['sku'])
            (pn if r['fecha'] == nueva else pv)[key] = r['precio']
        cur.close(); conn.close()

        porc = defaultdict(list)
        movers = []
        for key in set(pn) & set(pv):
            if pv[key] <= 0:
                continue
            ch = (pn[key] / pv[key] - 1) * 100
            porc[key[0]].append(ch)
            if abs(ch) >= 15:
                movers.append({'tienda': key[0], 'sku': key[1],
                               'viejo': pv[key], 'nuevo': pn[key], 'ch': ch})
        comp = {t: {'med': statistics.median(v), 'n': len(v)} for t, v in porc.items()}
        movers.sort(key=lambda m: -abs(m['ch']))
        return {'hay': True,
                'fechas': [nueva.strftime('%d/%m/%Y'), vieja.strftime('%d/%m/%Y')],
                'comp': comp, 'top': movers[:40]}
    except Exception as e:
        print(f"[competencia hist] error: {e}")
        return {'hay': False, 'fechas': []}


@competencia_scraper_bp.route('/admin/competencia-scraper/informe')
@login_required
def competencia_informe_page():
    # Import perezoso: el proceso ya tiene app cargada (no re-ejecuta el módulo
    # ni dispara el scheduler); así usamos la función de precios REAL de /costos.
    from app import _get_precio_costos_sku, query_db, query_one

    inv = _inv_pasajes()
    row = query_one("SELECT valor FROM configuracion WHERE clave='porcentajes_ml'")
    pml = json.loads(row['valor']) if row else None

    col = [r['sku'] for r in query_db(
        "SELECT sku FROM productos_base WHERE COALESCE(activo,1)=1 AND sku LIKE %s ORDER BY sku", ('C%',))]
    som = [r['sku'] for r in query_db(
        "SELECT sku FROM productos_compuestos WHERE activo=1 AND sku LIKE %s ORDER BY sku", ('S%',))]
    col = [s for s in col if s not in ('CERVICAL', 'CLASICA')]

    nombres = {}
    for r in query_db("SELECT sku, nombre FROM productos_base WHERE COALESCE(activo,1)=1 AND sku LIKE %s", ('C%',)):
        nombres[r['sku']] = r['nombre']
    for r in query_db("SELECT sku, nombre FROM productos_compuestos WHERE activo=1 AND sku LIKE %s", ('S%',)):
        nombres[r['sku']] = r['nombre']

    mis = {}
    for s in col + som:
        p = _get_precio_costos_sku(s, pml)
        if p:
            mis[s] = p

    comps = ['TMS', 'Lanus', 'Ivana']
    lines = ci.construir_comparacion(CSV_PATH, mis, inv, comps=tuple(comps))
    recargo = ci.recargo_por_tienda(CSV_PATH, inv, comps=tuple(comps))

    kpis = {}
    for c in comps:
        ds = [l['diff'] for l in lines if l['comp'] == c]
        if ds:
            kpis[c] = {'n': len(ds), 'med': statistics.median(ds),
                       'barato': sum(1 for d in ds if d < 0),
                       'flag': sum(1 for d in ds if abs(d) >= 30)}

    for l in lines:
        l['lbl'] = ci.LBL[l['bt']]
        l['nombre'] = nombres.get(l['sku'], '')
        l['tipo_txt'] = 'Sommier' if l['sku'].startswith('S') else 'Colchón'
        l['flag'] = abs(l['diff']) >= 30
        d = l['diff']
        l['cls'] = 'g2' if d <= -10 else ('g1' if d < 0 else ('r1' if d < 10 else 'r2'))
        l['ordc'] = ci.ORDER.index(l['bt'])
    lines.sort(key=lambda l: (0 if not l['sku'].startswith('S') else 1,
                              l['sku'], l['ordc'], comps.index(l['comp'])))

    try:
        fecha_csv = datetime.datetime.fromtimestamp(os.path.getmtime(CSV_PATH)).strftime('%d/%m/%Y %H:%M')
    except Exception:
        fecha_csv = ''

    return render_template('competencia_informe.html',
        lines=lines, kpis=kpis, recargo=recargo, comps=comps,
        fecha_csv=fecha_csv, hist=_hist_cambios(),
        n_skus=len(set(l['sku'] for l in lines)), lbl=ci.LBL)


# ============================================================================
# RUTAS
# ============================================================================
@competencia_scraper_bp.route('/admin/competencia-scraper')
@login_required
def competencia_scraper_page():
    productos, meta = _cargar_productos()
    modelos, medidas, tiendas = _get_filtros(productos)
    return render_template(
        'competencia_scraper.html',
        productos=productos, modelos=modelos, medidas=medidas, tiendas=tiendas,
        pasajes=(meta or {}).get('pasajes', PASAJES_DEFAULT),
        detectado_en=(meta or {}).get('detectado_en'),
    )


@competencia_scraper_bp.route('/admin/competencia-scraper/sondas/lista')
@_token_required
def listar_sondas_json():
    """Endpoint para que el scraper local pida las sondas activas."""
    sondas = cargar_sondas_activas()
    return jsonify({'sondas': sondas})


@competencia_scraper_bp.route('/admin/competencia-scraper/upload', methods=['POST'])
@_token_required
def upload_csv():
    """Recibe el CSV crudo de competencia y opcionalmente el de sondas."""
    f_comp = request.files.get('competencia') or request.files.get('file')
    f_sond = request.files.get('sondas')
    if not f_comp:
        return jsonify({'error': 'No competencia file'}), 400

    os.makedirs(DATA_DIR, exist_ok=True)
    f_comp.save(CSV_CRUDO_PATH)

    pasajes_detectados = None
    if f_sond:
        f_sond.save(SONDAS_RES_PATH)
        pasajes_detectados = detectar_pasajes_desde_sondas(SONDAS_RES_PATH)
        if pasajes_detectados:
            ahora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            guardar_pasajes(pasajes_detectados, ahora)

    try:
        rows = procesar(CSV_CRUDO_PATH, CSV_PATH)
    except Exception as e:
        return jsonify({'error': f'Error al procesar: {e}'}), 500

    # Snapshot del día para el histórico de precios de competencia (no rompe el upload si falla)
    snap_n = guardar_snapshot_hist()

    # Cachear en background las cuotas reales de los catálogos (para el display)
    try:
        import threading
        threading.Thread(target=prewarm_catalogos_scraper, daemon=True).start()
    except Exception:
        pass

    total = len(rows)
    matches = sum(1 for r in rows if r['sku_match'])
    cuotas_si = sum(1 for r in rows if r['cuotas_si'])
    return jsonify({
        'ok':                 True,
        'rows':               total,
        'matches':            matches,
        'sin_match':          total - matches,
        'cuotas_si':          cuotas_si,
        'pasajes_detectados': pasajes_detectados,
        'snapshot_hist':      snap_n,
    })


@competencia_scraper_bp.route('/admin/competencia-scraper/alert', methods=['POST'])
@_token_required
def alerta_scraper():
    """
    Endpoint llamado por run_scraper.bat (Windows) cuando algo falla.
    Recibe motivo y detalle, dispara mail al vendedor.
    """
    motivo  = request.form.get('motivo')  or request.json and request.json.get('motivo')
    detalle = request.form.get('detalle') or (request.json and request.json.get('detalle')) or ''
    if not motivo:
        return jsonify({'error': 'motivo requerido'}), 400
    ok, err = alerta_falla_scraper(motivo, detalle)
    if ok:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': err}), 500
