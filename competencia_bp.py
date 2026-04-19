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
    60351381: 'TMS',
    54898332: 'MUEBLESLANUS',
    # Ivana se agrega cuando aparezca en algún catálogo
}
MY_SELLER_ID = 29563319

CAMPAÑAS_CUOTAS = {
    'pcj-co-funded': 'Cuota Simple',
    '3x_campaign':   '3 cuotas s/interés',
    '6x_campaign':   '6 cuotas s/interés',
    '9x_campaign':   '9 cuotas s/interés',
    '12x_campaign':  '12 cuotas s/interés',
}

# SKUs a excluir del monitoreo
SKU_EXCLUIR = {'CERVICAL', 'CCO80', 'CCO90', 'CCO100', 'CCO140', 'CCO160', 'CCO180', 'CCO200'}

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
            INDEX idx_fecha_sku (fecha, sku),
            INDEX idx_seller (seller_id)
        )
    """)
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
    """Determina tipo de envío desde el campo shipping de ML"""
    if not shipping:
        return 'OTRO', False, 0
    mode = shipping.get('mode', '')
    logistic = shipping.get('logistic_type', '')
    free = shipping.get('free_shipping', False)
    tags = shipping.get('tags', [])
    cost = shipping.get('cost', 0) or 0

    if mode == 'me2' and logistic == 'self_service':
        return 'FLEX', True, 0
    if 'turbo' in str(tags).lower():
        return 'TURBO', free, cost
    if mode == 'me1':
        return 'ME1', free, cost
    if shipping.get('local_pick_up') and not free:
        return 'ACORDAR', False, 0
    return 'OTRO', free, cost

def _cuotas_desde_lt(lt, campaign):
    """Determina cuotas desde listing_type_id y campaign"""
    if lt == 'gold_special':
        return CAMPAÑAS_CUOTAS.get(campaign, 'Sin cuotas') if campaign else 'Sin cuotas'
    elif lt == 'gold_pro':
        return CAMPAÑAS_CUOTAS.get(campaign, '6 cuotas s/interés')
    return lt or 'Sin cuotas'

# ── Mapeo SKU → catalog_product_id ───────────────────────────────
def _get_catalog_id(sku):
    """Devuelve catalog_product_id para un SKU. Lo cachea en la BD."""
    cached = _q("SELECT catalog_product_id FROM sku_catalog_map WHERE sku=%s", (sku,), one=True)
    if cached:
        return cached['catalog_product_id']

    # Buscar un MLA del SKU sin Z
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

# ── Campaign activa de mis propios items ──────────────────────────
def _get_my_campaigns(sku):
    """Lee campaigns activas desde mis propios items del SKU."""
    rows = _q("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1", (sku,))
    campaigns = {}  # cuotas_publi → cuotas_efectivas
    for row in rows:
        data = _ml(f"https://api.mercadolibre.com/items/{row['mla_id']}?attributes=listing_type_id,sale_terms")
        if not data:
            continue
        lt = data.get('listing_type_id', '')
        camp = next((t.get('value_name', '').split('|')[0].strip()
                     for t in data.get('sale_terms', [])
                     if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
        publi = _cuotas_desde_lt(lt, None)   # cuotas propias sin campaign
        efectiva = _cuotas_desde_lt(lt, camp) # cuotas con campaign si aplica
        if publi not in campaigns:
            campaigns[publi] = efectiva
    return campaigns

# ── Snapshot de un catálogo ───────────────────────────────────────
def _snapshot_catalogo(sku, catalog_id, my_campaigns):
    """Consulta el catálogo y guarda snapshot de todos los vendedores relevantes."""
    rows_insertados = 0

    for cp in ['1425', '2000']:
        data = _ml(f"https://api.mercadolibre.com/products/{catalog_id}/items",
                   params={'zip_code': cp})
        if not data:
            continue

        # Obtener nicknames de sellers desconocidos
        seller_ids = {r['seller_id'] for r in data.get('results', [])}
        nicks = {}
        for sid in seller_ids:
            if sid == MY_SELLER_ID:
                nicks[sid] = 'MERCADOMUEBLES'
            elif sid in COMPETIDORES:
                nicks[sid] = COMPETIDORES[sid]
            else:
                u = _ml(f"https://api.mercadolibre.com/users/{sid}?attributes=id,nickname")
                nicks[sid] = u.get('nickname', str(sid)) if u else str(sid)
                # Auto-agregar si es Ivana
                if u and 'IVANA' in (u.get('nickname') or '').upper():
                    COMPETIDORES[sid] = u['nickname']

        for r in data.get('results', []):
            sid = r.get('seller_id')
            es_propio = (sid == MY_SELLER_ID)
            es_competidor = sid in COMPETIDORES

            if not es_propio and not es_competidor:
                continue

            precio = r.get('price')
            lt = r.get('listing_type_id', '')
            sale_terms = r.get('sale_terms', [])
            camp = next((t.get('value_name', '').split('|')[0].strip()
                         for t in sale_terms
                         if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)

            cuotas_publi = _cuotas_desde_lt(lt, None)
            # Para propios usamos campaign real; para competidores usamos la de nuestros items
            if es_propio:
                cuotas_ef = _cuotas_desde_lt(lt, camp)
            else:
                cuotas_ef = my_campaigns.get(cuotas_publi, cuotas_publi)

            envio_t, envio_free, envio_costo = _envio_tipo(r.get('shipping', {}))

            _exec("""INSERT INTO competencia_snapshots
                     (sku, catalog_product_id, seller_id, seller_nick, item_id,
                      precio, cuotas_publi, cuotas_efectivas, envio_tipo,
                      envio_gratis, envio_costo, es_propio)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (sku, catalog_id, sid, nicks.get(sid, str(sid)),
                   r.get('item_id'), precio,
                   cuotas_publi, cuotas_ef, envio_t,
                   1 if envio_free else 0, envio_costo,
                   1 if es_propio else 0))
            rows_insertados += 1

    return rows_insertados

# ── Función principal del agente ──────────────────────────────────
def correr_agente(skus_filtro=None):
    """
    Corre el agente de competencia.
    skus_filtro: lista de SKUs específicos, o None para correr todos.
    Retorna dict con resultado.
    """
    # Obtener SKUs a procesar (solo sin Z, sin almohadas/compac)
    rows = _q("""SELECT DISTINCT sku FROM sku_mla_mapeo
                 WHERE activo=1 AND sku NOT LIKE '%Z'
                 AND sku NOT IN ('CERVICAL')
                 AND sku NOT LIKE 'CCO%'
                 AND (sku LIKE 'C%' OR sku LIKE 'S%')
                 ORDER BY sku""")
    todos_skus = [r['sku'] for r in rows]

    if skus_filtro:
        skus_filtro_up = [s.upper().rstrip('Z') for s in skus_filtro]
        skus = [s for s in todos_skus if s.upper() in skus_filtro_up]
    else:
        skus = todos_skus

    if not skus:
        return {'ok': False, 'error': 'No se encontraron SKUs para procesar'}

    resultados = {'procesados': 0, 'sin_catalogo': [], 'errores': [], 'total_rows': 0}

    for sku in skus:
        try:
            cat_id = _get_catalog_id(sku)
            if not cat_id:
                resultados['sin_catalogo'].append(sku)
                continue

            my_camps = _get_my_campaigns(sku)
            rows_n = _snapshot_catalogo(sku, cat_id, my_camps)
            resultados['procesados'] += 1
            resultados['total_rows'] += rows_n
            time.sleep(0.3)  # respetar rate limits de ML

        except Exception as e:
            resultados['errores'].append(f"{sku}: {e}")

    return {'ok': True, **resultados}

# ── Scheduler jobs ────────────────────────────────────────────────
def job_competencia():
    """Job para APScheduler — corre el agente completo."""
    print("[COMPETENCIA] Iniciando snapshot diario...")
    r = correr_agente()
    print(f"[COMPETENCIA] Listo. Procesados: {r.get('procesados')}, rows: {r.get('total_rows')}")

# ── Rutas ──────────────────────────────────────────────────────────
@competencia_bp.route('/admin/competencia')
def competencia_page():
    return render_template('competencia.html')

@competencia_bp.route('/admin/competencia/correr', methods=['POST'])
def competencia_correr():
    """Corre el agente on-demand."""
    data = request.get_json() or {}
    skus = data.get('skus')  # None = todos, lista = filtro
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
    """Devuelve la última comparativa para mostrar en la tabla."""
    sku_filtro = request.args.get('sku')
    cuotas_filtro = request.args.get('cuotas', '6 cuotas s/interés')

    # Última fecha de snapshot
    ultima = _q("""SELECT MAX(fecha) as f FROM competencia_snapshots""", one=True)
    if not ultima or not ultima['f']:
        return jsonify({'rows': [], 'ultima_fecha': None})

    ultima_fecha = ultima['f']

    where = "WHERE DATE(s.fecha) = DATE(%s)"
    params = [ultima_fecha]
    if sku_filtro:
        where += " AND s.sku = %s"
        params.append(sku_filtro.upper())
    if cuotas_filtro:
        where += " AND s.cuotas_publi = %s"
        params.append(cuotas_filtro)

    rows = _q(f"""
        SELECT s.sku, s.seller_nick, s.item_id, s.precio,
               s.cuotas_publi, s.cuotas_efectivas,
               s.envio_tipo, s.envio_gratis, s.envio_costo,
               s.es_propio, s.catalog_product_id
        FROM competencia_snapshots s
        {where}
        ORDER BY s.sku, s.precio ASC
    """, params)

    # Convertir Decimal a float para JSON
    def fix(r):
        return {k: (float(v) if hasattr(v, '__float__') and not isinstance(v, (int, bool)) else v)
                for k, v in r.items()}

    return jsonify({
        'rows': [fix(r) for r in rows],
        'ultima_fecha': str(ultima_fecha),
        'cuotas_disponibles': [
            'Sin cuotas', 'Cuota Simple',
            '3 cuotas s/interés', '6 cuotas s/interés',
            '9 cuotas s/interés', '12 cuotas s/interés'
        ]
    })

@competencia_bp.route('/admin/competencia/skus')
def competencia_skus():
    """Lista de SKUs disponibles para filtrar."""
    rows = _q("""SELECT DISTINCT sku FROM competencia_snapshots ORDER BY sku""")
    return jsonify({'skus': [r['sku'] for r in rows]})
