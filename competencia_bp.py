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
}

CPS = [
    {'cp': '1425', 'label': 'CABA'},
    {'cp': '2000', 'label': 'Interior'},
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
        return 'ME1', free, cost
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
def _snapshot_catalogo(sku, catalog_id, campaigns):
    """
    Consulta el catálogo por CP y guarda snapshot deduplicado.
    Un registro por: seller_id + cuotas_publi + cp (precio mínimo).
    """
    rows_insertados = 0

    for cp_info in CPS:
        cp = cp_info['cp']
        cp_label = cp_info['label']

        data = _ml(f"https://api.mercadolibre.com/products/{catalog_id}/items",
                   params={'zip_code': cp})
        if not data:
            continue

        # Resolver nicknames desconocidos
        seller_ids = {r['seller_id'] for r in data.get('results', [])}
        nicks = {}
        for sid in seller_ids:
            if sid == MY_SELLER_ID:
                nicks[sid] = 'MERCADOMUEBLES'
            elif sid in COMPETIDORES:
                nicks[sid] = COMPETIDORES[sid]
            else:
                u = _ml(f"https://api.mercadolibre.com/users/{sid}?attributes=id,nickname")
                if u:
                    nick = u.get('nickname', str(sid))
                    nicks[sid] = nick
                    # Auto-detectar Ivana
                    if 'IVANA' in nick.upper():
                        COMPETIDORES[sid] = nick
                else:
                    nicks[sid] = str(sid)

        # Deduplicar: seller_id + cuotas_publi → mejor precio
        dedup = {}  # (seller_id, cuotas_publi) → item_data
        for r in data.get('results', []):
            sid = r.get('seller_id')
            es_propio = (sid == MY_SELLER_ID)
            es_comp = sid in COMPETIDORES
            if not es_propio and not es_comp:
                continue

            lt = r.get('listing_type_id', '')
            sale_terms = r.get('sale_terms', [])
            camp = next((t.get('value_name', '').split('|')[0].strip()
                         for t in sale_terms
                         if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)

            cuotas_pub = _cuotas_publi(lt)
            # Aplicar campaign uniforme para todos (es por categoría)
            if camp:
                cuotas_ef = CAMPAÑAS_CUOTAS.get(camp, cuotas_pub)
            else:
                cuotas_ef = campaigns.get(cuotas_pub, cuotas_pub)

            key = (sid, cuotas_pub)
            precio = r.get('price') or 0
            if key not in dedup or precio < dedup[key]['precio']:
                envio_t, envio_free, envio_costo = _envio_tipo(r.get('shipping', {}))
                dedup[key] = {
                    'seller_id':   sid,
                    'seller_nick': nicks.get(sid, str(sid)),
                    'item_id':     r.get('item_id'),
                    'precio':      precio,
                    'cuotas_pub':  cuotas_pub,
                    'cuotas_ef':   cuotas_ef,
                    'envio_t':     envio_t,
                    'envio_free':  envio_free,
                    'envio_costo': envio_costo,
                    'es_propio':   es_propio,
                }

        # Guardar deduplicados
        for item in dedup.values():
            _exec("""INSERT INTO competencia_snapshots
                     (sku, catalog_product_id, cp, cp_label, seller_id, seller_nick, item_id,
                      precio, cuotas_publi, cuotas_efectivas, envio_tipo,
                      envio_gratis, envio_costo, es_propio, pausada_sin_stock)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)""",
                  (sku, catalog_id, cp, cp_label,
                   item['seller_id'], item['seller_nick'], item['item_id'],
                   item['precio'], item['cuotas_pub'], item['cuotas_ef'],
                   item['envio_t'], 1 if item['envio_free'] else 0,
                   item['envio_costo'], 1 if item['es_propio'] else 0))
            rows_insertados += 1

        # Agregar mis publis pausadas por stock como referencia
        pausadas = _get_mis_publis_pausadas(sku)
        for p in pausadas:
            lt = p['lt']
            camp = p['camp']
            cuotas_pub = _cuotas_publi(lt)
            cuotas_ef = _cuotas_efectivas(lt, camp)
            # Solo si no hay ya una publi propia activa con mismas cuotas para este CP
            key = (MY_SELLER_ID, cuotas_pub)
            if key not in dedup:
                envio_t, envio_free, envio_costo = _envio_tipo(p['shipping'])
                _exec("""INSERT INTO competencia_snapshots
                         (sku, catalog_product_id, cp, cp_label, seller_id, seller_nick, item_id,
                          precio, cuotas_publi, cuotas_efectivas, envio_tipo,
                          envio_gratis, envio_costo, es_propio, pausada_sin_stock)
                         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,1)""",
                      (sku, catalog_id, cp, cp_label,
                       MY_SELLER_ID, 'MERCADOMUEBLES (pausada)', p['mla_id'],
                       p['precio'], cuotas_pub, cuotas_ef,
                       envio_t, 1 if envio_free else 0, envio_costo))
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

@competencia_bp.route('/admin/competencia/datos')
def competencia_datos():
    sku_filtro  = request.args.get('sku')
    cuotas_filtro = request.args.get('cuotas', '6 cuotas s/interés')
    cp_filtro   = request.args.get('cp', '1425')

    ultima = _q("SELECT MAX(fecha) as f FROM competencia_snapshots", one=True)
    if not ultima or not ultima['f']:
        return jsonify({'rows': [], 'ultima_fecha': None})

    ultima_fecha = ultima['f']
    where = "WHERE DATE(s.fecha) = DATE(%s) AND s.cuotas_publi = %s AND s.cp = %s"
    params = [ultima_fecha, cuotas_filtro, cp_filtro]

    if sku_filtro:
        where += " AND s.sku = %s"
        params.append(sku_filtro.upper())

    rows = _q(f"""
        SELECT s.sku, s.seller_nick, s.item_id, s.precio,
               s.cuotas_publi, s.cuotas_efectivas,
               s.envio_tipo, s.envio_gratis, s.envio_costo,
               s.es_propio, s.pausada_sin_stock, s.catalog_product_id,
               s.cp, s.cp_label
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
    })

@competencia_bp.route('/admin/competencia/skus')
def competencia_skus():
    rows = _q("SELECT DISTINCT sku FROM competencia_snapshots ORDER BY sku")
    return jsonify({'skus': [r['sku'] for r in rows]})
