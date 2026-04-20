import json, os, re, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import mysql.connector
from flask import Blueprint, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv('config/.env')

competencia_bp = Blueprint('competencia', __name__)

# ── Competidores conocidos ─────────────────────────────────────────
COMPETIDORES = {
    60351381:  'TMS',
    54898332:  'MUEBLESLANUS',
    192769857: 'COLCHONERIA IVANA',
}
MY_SELLER_ID = 29563319

CAMPAÑAS_CUOTAS = {
    'pcj-co-funded': 'Cuota Simple',
    '3x_campaign':   '3 cuotas s/interés',
    '6x_campaign':   '6 cuotas s/interés',
    '9x_campaign':   '9 cuotas s/interés',
    '12x_campaign':  '12 cuotas s/interés',
    '18x_campaign':  '12 cuotas s/interés',  # pasaje a 18, publi base es 12c
    '24x_campaign':  '12 cuotas s/interés',  # pasaje a 24, publi base es 12c
}

CPS = [
    {'cp': '1425', 'label': 'CABA'},
]

# ── DB ────────────────────────────────────────────────────────────
def _db():
    return mysql.connector.connect(
        host='localhost', user='cannon',
        password=os.getenv('DB_PASSWORD', 'Sistema@32267845'),
        database='inventario_cannon'
    )

def _q(sql, params=None, one=False):
    db = _db(); cur = db.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close(); db.close()

def _exec(sql, params=None):
    db = _db(); cur = db.cursor()
    try:
        cur.execute(sql, params or ())
        db.commit()
    finally:
        cur.close(); db.close()

# ── Crear tablas ──────────────────────────────────────────────────
def _crear_tablas():
    db = _db(); cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sku_catalog_map (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            sku             VARCHAR(50) UNIQUE,
            catalog_product_id VARCHAR(30),
            category_id     VARCHAR(20),
            mla_ref         VARCHAR(20),
            actualizado_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS competencia_snapshots (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            fecha           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sku             VARCHAR(50),
            catalog_product_id VARCHAR(30),
            cp              VARCHAR(10),
            cp_label        VARCHAR(20),
            seller_id       INT,
            seller_nick     VARCHAR(100),
            item_id         VARCHAR(20),
            precio          DECIMAL(12,2),
            cuotas_publi    VARCHAR(30),
            cuotas_efectivas VARCHAR(30),
            envio_tipo      ENUM('FLEX','ME1','ACORDAR','TURBO','OTRO'),
            envio_gratis    TINYINT(1) DEFAULT 0,
            envio_costo     DECIMAL(10,2) DEFAULT 0,
            es_propio       TINYINT(1) DEFAULT 0,
            pausada_sin_stock TINYINT(1) DEFAULT 0,
            INDEX idx_fecha_sku (fecha, sku),
            INDEX idx_seller (seller_id)
        )
    """)
    # Agregar columnas nuevas si no existen (upgrade)
    try:
        cur.execute("ALTER TABLE competencia_snapshots ADD COLUMN cp VARCHAR(10) AFTER catalog_product_id")
    except Exception: pass
    try:
        cur.execute("ALTER TABLE competencia_snapshots ADD COLUMN cp_label VARCHAR(20) AFTER cp")
    except Exception: pass
    try:
        cur.execute("ALTER TABLE competencia_snapshots ADD COLUMN pausada_sin_stock TINYINT(1) DEFAULT 0")
    except Exception: pass
    db.commit(); cur.close(); db.close()

try:
    _crear_tablas()
except Exception as e:
    print(f"[competencia] Error creando tablas: {e}")

# ── ML helpers ────────────────────────────────────────────────────
def _token():
    row = _q("SELECT valor FROM configuracion WHERE clave='ml_token'", one=True)
    return json.loads(row['valor'])['access_token'] if row else None

def _ml(url, params=None):
    token = _token()
    try:
        r = requests.get(url, headers={'Authorization': f'Bearer {token}'},
                        params=params, timeout=10)
        if r.status_code == 429:
            time.sleep(2)
            r = requests.get(url, headers={'Authorization': f'Bearer {token}'},
                            params=params, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def _ml_catalog_all(catalog_id, zip_code):
    """Trae TODOS los resultados del catálogo con paginación."""
    token = _token()
    all_results = []
    offset = 0
    limit = 20
    while True:
        try:
            r = requests.get(
                f'https://api.mercadolibre.com/products/{catalog_id}/items',
                headers={'Authorization': f'Bearer {token}'},
                params={'zip_code': zip_code, 'limit': limit, 'offset': offset},
                timeout=10
            )
            if r.status_code == 429:
                time.sleep(2)
                continue
            if r.status_code != 200:
                break
            data = r.json()
            results = data.get('results', [])
            all_results.extend(results)
            total = data.get('paging', {}).get('total', len(results))
            offset += limit
            if offset >= total or not results:
                break
            time.sleep(0.2)
        except Exception:
            break
    return all_results

def _envio_tipo(shipping):
    if not shipping:
        return 'OTRO', False, 0
    mode = shipping.get('mode', '')
    logistic = shipping.get('logistic_type', '')
    free = shipping.get('free_shipping', False)
    tags = str(shipping.get('tags', []))
    cost = float(shipping.get('cost') or 0)

    if mode == 'me2' and logistic == 'self_service':
        return 'FLEX', True, 0
    if 'turbo' in tags.lower():
        return 'TURBO', free, cost
    if mode == 'me1':
        return 'ME1', free, 0  # cost is unreliable from products endpoint
    if shipping.get('local_pick_up') and not free:
        return 'ACORDAR', False, 0
    return 'OTRO', free, cost

def _cuotas_publi(lt):
    """Cuotas de la publicación SIN tener en cuenta campaigns (estructura base)"""
    if lt == 'gold_special':
        return 'Sin cuotas'
    elif lt == 'gold_pro':
        return '6 cuotas s/interés'
    return lt or 'Sin cuotas'

def _cuotas_efectivas(lt, campaign):
    """Cuotas efectivas CON campaign aplicada"""
    if lt == 'gold_special':
        return CAMPAÑAS_CUOTAS.get(campaign, 'Sin cuotas') if campaign else 'Sin cuotas'
    elif lt == 'gold_pro':
        return CAMPAÑAS_CUOTAS.get(campaign, '6 cuotas s/interés')
    return lt or 'Sin cuotas'

# ── Mapeo SKU → catalog_product_id ───────────────────────────────
def _get_catalog_id(sku):
    cached = _q("SELECT catalog_product_id FROM sku_catalog_map WHERE sku=%s", (sku,), one=True)
    if cached:
        return cached['catalog_product_id']

    sku_base = sku.rstrip('Z') if sku.endswith('Z') else sku
    row = _q("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1 LIMIT 1",
             (sku_base,), one=True)
    if not row:
        return None

    data = _ml(f"https://api.mercadolibre.com/items/{row['mla_id']}")
    if not data:
        return None

    cat_id = data.get('catalog_product_id')
    cat_eg = data.get('category_id')
    if cat_id:
        try:
            _exec("""INSERT INTO sku_catalog_map (sku, catalog_product_id, category_id, mla_ref)
                     VALUES (%s,%s,%s,%s)
                     ON DUPLICATE KEY UPDATE catalog_product_id=%s, category_id=%s""",
                  (sku_base, cat_id, cat_eg, row['mla_id'], cat_id, cat_eg))
        except Exception:
            pass
    return cat_id

# ── Detectar campaigns desde mis propios items ────────────────────
def _get_campaigns_activas(sku):
    """
    Lee campaigns activas desde mis items.
    Retorna dict: cuotas_publi → cuotas_efectivas
    El pasaje es por categoría — aplica igual para TODOS los vendedores.
    """
    rows = _q("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1", (sku,))
    campaigns = {}
    seen_lts = set()
    for row in rows:
        data = _ml(f"https://api.mercadolibre.com/items/{row['mla_id']}?attributes=listing_type_id,sale_terms,status,sub_status")
        if not data:
            continue
        lt = data.get('listing_type_id', '')
        if lt in seen_lts:
            continue
        seen_lts.add(lt)
        camp = next((t.get('value_name', '').split('|')[0].strip()
                     for t in data.get('sale_terms', [])
                     if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
        publi = _cuotas_publi(lt)
        efectiva = _cuotas_efectivas(lt, camp)
        if publi not in campaigns:
            campaigns[publi] = efectiva
    return campaigns

# ── Mis publis pausadas (sin stock) ──────────────────────────────
def _get_mis_publis_pausadas(sku):
    """
    Retorna publis propias pausadas por out_of_stock para mostrar precio referencial.
    """
    rows = _q("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1", (sku,))
    pausadas = []
    for row in rows:
        data = _ml(f"https://api.mercadolibre.com/items/{row['mla_id']}?attributes=id,price,listing_type_id,sale_terms,status,sub_status,shipping")
        if not data:
            continue
        status = data.get('status', '')
        sub_status = data.get('sub_status') or []
        if isinstance(sub_status, str):
            sub_status = [sub_status]
        if status == 'paused' and 'out_of_stock' in sub_status:
            lt = data.get('listing_type_id', '')
            camp = next((t.get('value_name', '').split('|')[0].strip()
                         for t in data.get('sale_terms', [])
                         if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
            pausadas.append({
                'mla_id': row['mla_id'],
                'precio': data.get('price'),
                'lt': lt,
                'camp': camp,
                'shipping': data.get('shipping', {}),
            })
    return pausadas

# ── Snapshot de un catálogo ───────────────────────────────────────
def _get_mis_publis_all(sku):
    """
    Trae TODAS mis publis del SKU (activas y pausadas por stock).
    SKU sin Z → FLEX, SKU con Z → ME1
    """
    result = []
    for suffix, envio_t, envio_free in [
        ('',  'FLEX', True),   # sin Z = Flex
        ('Z', 'ME1',  False),  # con Z = ME1
    ]:
        sku_buscar = sku + suffix if not sku.endswith('Z') else sku
        if suffix == 'Z' and sku.endswith('Z'):
            sku_buscar = sku
        elif suffix == '' and not sku.endswith('Z'):
            sku_buscar = sku
        else:
            sku_buscar = sku.rstrip('Z') + suffix

        rows = _q("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1", (sku_buscar,))
        for row in rows:
            data = _ml(f"https://api.mercadolibre.com/items/{row['mla_id']}?attributes=id,price,listing_type_id,sale_terms,status,sub_status,shipping")
            if not data:
                continue
            status = data.get('status', '')
            sub_status = data.get('sub_status') or []
            if isinstance(sub_status, str):
                sub_status = [sub_status]

            lt = data.get('listing_type_id', '')
            camp = next((t.get('value_name', '').split('|')[0].strip()
                         for t in data.get('sale_terms', [])
                         if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
            cuotas_pub = _cuotas_publi(lt)
            cuotas_ef  = _cuotas_efectivas(lt, camp)
            pausada = (status == 'paused' and 'out_of_stock' in sub_status)

            result.append({
                'mla_id':     row['mla_id'],
                'precio':     data.get('price'),
                'cuotas_pub': cuotas_pub,
                'cuotas_ef':  cuotas_ef,
                'envio_t':    envio_t,
                'envio_free': envio_free,
                'pausada':    pausada,
                'activa':     (status == 'active'),
            })
    return result


def _snapshot_catalogo(sku, catalog_id, campaigns):
    """
    Guarda snapshot:
    - Mis publis: desde sku_mla_mapeo directamente (sin Z=FLEX, con Z=ME1)
    - Competidores: desde catalog endpoint, deduplicados por seller+cuotas+envio
    Borra rows del día antes de insertar para evitar duplicados en re-runs.
    """
    # Limpiar rows del día para este SKU (evita duplicados en re-run)
    _exec("DELETE FROM competencia_snapshots WHERE sku=%s AND DATE(fecha)=CURDATE()", (sku,))

    rows_insertados = 0
    cp = '1425'
    cp_label = 'CABA'

    # ── MIS PUBLIS ────────────────────────────────────────────────
    mis_publis = _get_mis_publis_all(sku)
    cuotas_vistas = set()  # para saber qué cuotas tengo activas

    for p in mis_publis:
        nick = 'MERCADOMUEBLES' if p['activa'] else 'MERCADOMUEBLES (pausada)'
        _exec("""INSERT INTO competencia_snapshots
                 (sku, catalog_product_id, cp, cp_label, seller_id, seller_nick, item_id,
                  precio, cuotas_publi, cuotas_efectivas, envio_tipo,
                  envio_gratis, envio_costo, es_propio, pausada_sin_stock)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,1,%s)""",
              (sku, catalog_id, cp, cp_label,
               MY_SELLER_ID, nick, p['mla_id'],
               p['precio'], p['cuotas_pub'], p['cuotas_ef'],
               p['envio_t'], 1 if p['envio_free'] else 0,
               1 if p['pausada'] else 0))
        rows_insertados += 1
        if p['activa']:
            cuotas_vistas.add(p['cuotas_pub'])

    # ── COMPETIDORES desde catálogo ───────────────────────────────
    all_results = _ml_catalog_all(catalog_id, cp)
    if not all_results:
        return rows_insertados

    # Resolver nicknames
    seller_ids = {r['seller_id'] for r in all_results}
    nicks = {}
    for sid in seller_ids:
        if sid == MY_SELLER_ID:
            continue  # ya procesamos los nuestros
        if sid in COMPETIDORES:
            nicks[sid] = COMPETIDORES[sid]
        else:
            u = _ml(f"https://api.mercadolibre.com/users/{sid}?attributes=id,nickname")
            if u:
                nick_val = u.get('nickname', str(sid))
                nicks[sid] = nick_val
                if 'IVANA' in nick_val.upper():
                    COMPETIDORES[sid] = nick_val
            else:
                nicks[sid] = str(sid)

    dedup = {}
    for r in all_results:
        sid = r.get('seller_id')
        if sid == MY_SELLER_ID or sid not in COMPETIDORES:
            continue

        lt = r.get('listing_type_id', '')
        sale_terms = r.get('sale_terms', [])
        camp = next((t.get('value_name', '').split('|')[0].strip()
                     for t in sale_terms
                     if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)

        cuotas_pub = _cuotas_publi(lt)
        cuotas_ef = CAMPAÑAS_CUOTAS.get(camp, campaigns.get(cuotas_pub, cuotas_pub)) if camp else campaigns.get(cuotas_pub, cuotas_pub)

        envio_t, envio_free, _ = _envio_tipo(r.get('shipping', {}))
        key = (sid, cuotas_pub, envio_t)
        precio = r.get('price') or 0
        if key not in dedup or precio < dedup[key]['precio']:
            dedup[key] = {
                'seller_nick': nicks.get(sid, str(sid)),
                'item_id':     r.get('item_id'),
                'precio':      precio,
                'cuotas_pub':  cuotas_pub,
                'cuotas_ef':   cuotas_ef,
                'envio_t':     envio_t,
                'envio_free':  envio_free,
                'seller_id':   sid,
            }

    for item in dedup.values():
        _exec("""INSERT INTO competencia_snapshots
                 (sku, catalog_product_id, cp, cp_label, seller_id, seller_nick, item_id,
                  precio, cuotas_publi, cuotas_efectivas, envio_tipo,
                  envio_gratis, envio_costo, es_propio, pausada_sin_stock)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0)""",
              (sku, catalog_id, cp, cp_label,
               item['seller_id'], item['seller_nick'], item['item_id'],
               item['precio'], item['cuotas_pub'], item['cuotas_ef'],
               item['envio_t'], 1 if item['envio_free'] else 0))
        rows_insertados += 1

    return rows_insertados

# ── Función principal ─────────────────────────────────────────────
def correr_agente(skus_filtro=None):
    rows = _q("""SELECT DISTINCT sku FROM sku_mla_mapeo
                 WHERE activo=1 AND sku NOT LIKE '%Z'
                 AND sku NOT IN ('CERVICAL')
                 AND sku NOT LIKE 'CCO%'
                 AND (sku LIKE 'C%' OR sku LIKE 'S%')
                 ORDER BY sku""")
    todos_skus = [r['sku'] for r in rows]

    if skus_filtro:
        skus_up = [s.upper().rstrip('Z') for s in skus_filtro]
        skus = [s for s in todos_skus if s.upper() in skus_up]
    else:
        skus = todos_skus

    if not skus:
        return {'ok': False, 'error': 'No se encontraron SKUs'}

    resultado = {'procesados': 0, 'sin_catalogo': [], 'errores': [], 'total_rows': 0}

    for sku in skus:
        try:
            cat_id = _get_catalog_id(sku)
            if not cat_id:
                resultado['sin_catalogo'].append(sku)
                continue
            campaigns = _get_campaigns_activas(sku)
            rows_n = _snapshot_catalogo(sku, cat_id, campaigns)
            resultado['procesados'] += 1
            resultado['total_rows'] += rows_n
            time.sleep(0.3)
        except Exception as e:
            resultado['errores'].append(f"{sku}: {e}")

    return {'ok': True, **resultado}

def job_competencia():
    print("[COMPETENCIA] Iniciando snapshot diario...")
    r = correr_agente()
    print(f"[COMPETENCIA] Listo. Procesados: {r.get('procesados')}, rows: {r.get('total_rows')}")

# ── Rutas ──────────────────────────────────────────────────────────
@competencia_bp.route('/admin/competencia')
def competencia_page():
    return render_template('competencia.html')

@competencia_bp.route('/admin/competencia/correr', methods=['POST'])
def competencia_correr():
    data = request.get_json() or {}
    skus = data.get('skus')
    if skus and isinstance(skus, str):
        skus = [s.strip() for s in skus.split(',') if s.strip()]
    import threading
    resultado = {}
    def run():
        nonlocal resultado
        resultado = correr_agente(skus)
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=300)
    return jsonify(resultado)

ORDEN_CUOTAS = [
    'Sin cuotas', 'Cuota Simple',
    '3 cuotas s/interés', '6 cuotas s/interés',
    '9 cuotas s/interés', '12 cuotas s/interés', '18 cuotas s/interés'
]

@competencia_bp.route('/admin/competencia/datos')
def competencia_datos():
    sku_filtro = request.args.get('sku')

    ultima = _q("SELECT MAX(fecha) as f FROM competencia_snapshots", one=True)
    if not ultima or not ultima['f']:
        return jsonify({'rows': [], 'ultima_fecha': None})

    ultima_fecha = ultima['f']
    where = "WHERE DATE(s.fecha) = DATE(%s) AND s.cp = '1425'"
    params = [ultima_fecha]

    if sku_filtro:
        where += " AND s.sku = %s"
        params.append(sku_filtro.upper())

    rows = _q(f"""
        SELECT s.sku, s.seller_nick, s.item_id, s.precio,
               s.cuotas_publi, s.cuotas_efectivas,
               s.envio_tipo, s.envio_gratis, s.envio_costo,
               s.es_propio, s.pausada_sin_stock, s.catalog_product_id
        FROM competencia_snapshots s
        {where}
        ORDER BY s.sku, s.precio ASC
    """, params)

    def fix(r):
        return {k: (float(v) if hasattr(v, '__float__') and not isinstance(v, (int, bool)) else
                    str(v) if hasattr(v, 'strftime') else v)
                for k, v in r.items()}

    return jsonify({
        'rows': [fix(r) for r in rows],
        'ultima_fecha': str(ultima_fecha),
        'orden_cuotas': ORDEN_CUOTAS,
    })

@competencia_bp.route('/admin/competencia/skus')
def competencia_skus():
    rows = _q("SELECT DISTINCT sku FROM competencia_snapshots ORDER BY sku")
    return jsonify({'skus': [r['sku'] for r in rows]})
