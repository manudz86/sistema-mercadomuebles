import json, os, re, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import mysql.connector
from flask import Blueprint, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv('config/.env')

competencia_bp = Blueprint('competencia', __name__)

# ── Competidores ──────────────────────────────────────────────────
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
    '18x_campaign':  '12 cuotas s/interés',
    '24x_campaign':  '12 cuotas s/interés',
}

ORDEN_CUOTAS = [
    'Sin cuotas', 'Cuota Simple',
    '3 cuotas s/interés', '6 cuotas s/interés',
    '9 cuotas s/interés', '12 cuotas s/interés', '18 cuotas s/interés'
]

# ── Modelo / Medida desde SKU ─────────────────────────────────────
SKU_MODELO = [
    ('CDOP',  'Doral Pillow'),   ('CDO',   'Doral'),
    ('CEXP',  'Exclusive Pillow'),('CEX',  'Exclusive'),
    ('CREP',  'Renovation Euro Pillow'), ('CRE', 'Renovation'),
    ('CSUP',  'Sublime Pillow'), ('CSO',   'Soñar'),
    ('CPR',   'Princess'),       ('CTR',   'Tropical'),
    ('CFR',   'Francia'),        ('CSP',   'Soñar Pillow'),
    ('SDOP',  'Doral Pillow'),   ('SDO',   'Doral'),
    ('SEXP',  'Exclusive Pillow'),('SEX',  'Exclusive'),
    ('SREP',  'Renovation Euro Pillow'), ('SRE', 'Renovation'),
    ('SSUP',  'Sublime Pillow'), ('SSO',   'Soñar'),
    ('SPR',   'Princess'),
]

def _sku_meta(sku):
    """Retorna (tipo, modelo, medida) desde el SKU."""
    s = sku.upper().rstrip('Z').rstrip('F')
    tipo = 'sommier' if s.startswith('S') else 'colchon'
    modelo = 'Otro'
    for prefix, name in SKU_MODELO:
        if s.startswith(prefix):
            modelo = name
            rest = s[len(prefix):]
            nums = re.findall(r'\d+', rest)
            # Tomar solo el primer número y limitarlo a 999 (ancho en cm)
            medida = int(nums[0]) if nums else 0
            if medida > 999: medida = medida % 1000  # SEXP90190 → 90
            return tipo, modelo, medida
    nums = re.findall(r'\d+', s)
    return tipo, modelo, int(nums[0]) if nums else 0

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

# ── Crear / migrar tablas ─────────────────────────────────────────
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
            tipo            VARCHAR(10),
            modelo          VARCHAR(60),
            medida          SMALLINT,
            catalog_product_id VARCHAR(30),
            cp              VARCHAR(10) DEFAULT '1425',
            cp_label        VARCHAR(20) DEFAULT 'CABA',
            seller_id       INT,
            seller_nick     VARCHAR(100),
            item_id         VARCHAR(20),
            precio          DECIMAL(12,2),
            cuotas_publi    VARCHAR(30),
            cuotas_efectivas VARCHAR(30),
            envio_tipo      VARCHAR(20),
            envio_gratis    TINYINT(1) DEFAULT 0,
            envio_costo     DECIMAL(10,2) DEFAULT 0,
            es_propio       TINYINT(1) DEFAULT 0,
            pausada_sin_stock TINYINT(1) DEFAULT 0,
            INDEX idx_fecha_sku (fecha, sku),
            INDEX idx_tipo_modelo (tipo, modelo, medida)
        )
    """)
    # Migraciones para columnas nuevas
    for col, defn in [
        ('tipo',   "VARCHAR(10) DEFAULT 'colchon' AFTER sku"),
        ('modelo', "VARCHAR(60) DEFAULT '' AFTER tipo"),
        ('medida', "SMALLINT DEFAULT 0 AFTER modelo"),
    ]:
        try:
            cur.execute(f"ALTER TABLE competencia_snapshots ADD COLUMN {col} {defn}")
        except Exception:
            pass
    # Fix ENUM → VARCHAR for envio_tipo (allows COLECTA)
    try:
        cur.execute("ALTER TABLE competencia_snapshots MODIFY COLUMN envio_tipo VARCHAR(20)")
    except Exception:
        pass
    db.commit(); cur.close(); db.close()

try:
    _crear_tablas()
except Exception as e:
    print(f"[competencia] Error tablas: {e}")

# ── ML helpers ────────────────────────────────────────────────────
def _token():
    row = _q("SELECT valor FROM configuracion WHERE clave='ml_token'", one=True)
    return json.loads(row['valor'])['access_token'] if row else None

def _ml(url, params=None):
    token = _token()
    try:
        r = requests.get(url, headers={'Authorization': f'Bearer {token}'},
                        params=params, timeout=12)
        if r.status_code == 429:
            time.sleep(3)
            r = requests.get(url, headers={'Authorization': f'Bearer {token}'},
                            params=params, timeout=12)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def _ml_catalog_all(catalog_id, zip_code):
    token = _token()
    all_results = []
    offset = 0; limit = 20
    while True:
        try:
            r = requests.get(
                f'https://api.mercadolibre.com/products/{catalog_id}/items',
                headers={'Authorization': f'Bearer {token}'},
                params={'zip_code': zip_code, 'limit': limit, 'offset': offset},
                timeout=12
            )
            if r.status_code == 429:
                time.sleep(3); continue
            if r.status_code != 200: break
            data = r.json()
            results = data.get('results', [])
            all_results.extend(results)
            total = data.get('paging', {}).get('total', len(results))
            offset += limit
            if offset >= total or not results: break
            time.sleep(0.2)
        except Exception:
            break
    return all_results

def _campaign_from_tags(tags):
    if not tags: return None
    keys = ['pcj-co-funded','3x_campaign','6x_campaign','9x_campaign',
            '12x_campaign','18x_campaign','24x_campaign']
    for tag in tags:
        for ck in keys:
            if ck in tag.lower():
                return ck
    return None

def _envio_tipo(shipping):
    if not shipping: return 'OTRO', False, 0
    mode     = shipping.get('mode', '')
    logistic = shipping.get('logistic_type', '')
    free     = shipping.get('free_shipping', False)
    tags_s   = str(shipping.get('tags', []))
    cost     = 0

    if mode == 'me2':
        if logistic == 'cross_docking':
            return 'COLECTA', True, 0
        return 'FLEX', True, 0
    if 'turbo' in tags_s.lower():
        return 'TURBO', free, cost
    if mode == 'me1':
        return 'ME1', free, 0
    if shipping.get('local_pick_up') and not free:
        return 'ACORDAR', False, 0
    return 'OTRO', free, 0

def _cuotas_publi(lt, campaign=None):
    if lt == 'gold_pro':
        return '6 cuotas s/interés' if not campaign else CAMPAÑAS_CUOTAS.get(campaign, '6 cuotas s/interés')
    if lt == 'gold_special':
        if not campaign: return 'Sin cuotas'
        if campaign == 'pcj-co-funded': return 'Cuota Simple'
        return CAMPAÑAS_CUOTAS.get(campaign, 'Sin cuotas')
    return lt or 'Sin cuotas'

def _cuotas_efectivas(lt, campaign):
    return _cuotas_publi(lt, campaign)

# ── Catalog ID ────────────────────────────────────────────────────
def _get_catalog_id(sku):
    cached = _q("SELECT catalog_product_id FROM sku_catalog_map WHERE sku=%s", (sku,), one=True)
    if cached: return cached['catalog_product_id']
    sku_base = sku.rstrip('Z')
    row = _q("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1 LIMIT 1", (sku_base,), one=True)
    if not row: return None
    data = _ml(f"https://api.mercadolibre.com/items/{row['mla_id']}")
    if not data: return None
    cat_id = data.get('catalog_product_id')
    if cat_id:
        try:
            _exec("""INSERT INTO sku_catalog_map (sku, catalog_product_id, category_id, mla_ref)
                     VALUES (%s,%s,%s,%s)
                     ON DUPLICATE KEY UPDATE catalog_product_id=%s, category_id=%s""",
                  (sku_base, cat_id, data.get('category_id'), row['mla_id'], cat_id, data.get('category_id')))
        except Exception: pass
    return cat_id

# ── Mis publis desde catálogo ─────────────────────────────────────
def _get_mis_publis_all(catalog_id):
    all_results = _ml_catalog_all(catalog_id, '1425')
    mis_items = [r for r in all_results if r.get('seller_id') == MY_SELLER_ID]
    result = []
    for r in mis_items:
        mla_id = r.get('item_id')
        data = _ml(f"https://api.mercadolibre.com/items/{mla_id}"
                   "?attributes=id,price,listing_type_id,sale_terms,status,sub_status,tags")
        if not data: continue
        status = data.get('status', '')
        sub_status = data.get('sub_status') or []
        if isinstance(sub_status, str): sub_status = [sub_status]
        pausada = (status == 'paused' and 'out_of_stock' in sub_status)
        activa  = (status == 'active')
        if not activa and not pausada: continue
        lt   = data.get('listing_type_id', '')
        camp = next((t.get('value_name', '').split('|')[0].strip()
                     for t in data.get('sale_terms', [])
                     if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
        if not camp: camp = _campaign_from_tags(data.get('tags', []))
        cuotas_pub = _cuotas_publi(lt, camp)
        envio_t, envio_free, _ = _envio_tipo(r.get('shipping', {}))
        result.append({
            'mla_id':     mla_id,
            'precio':     data.get('price'),
            'cuotas_pub': cuotas_pub,
            'cuotas_ef':  cuotas_pub,
            'envio_t':    envio_t,
            'envio_free': envio_free,
            'pausada':    pausada,
            'activa':     activa,
        })
    return result

# ── Snapshot ──────────────────────────────────────────────────────
def _snapshot_catalogo(sku, catalog_id):
    tipo, modelo, medida = _sku_meta(sku)
    _exec("DELETE FROM competencia_snapshots WHERE sku=%s AND DATE(fecha)=CURDATE()", (sku,))
    rows_insertados = 0
    cp = '1425'; cp_label = 'CABA'

    # Mis publis
    mis_publis = _get_mis_publis_all(catalog_id)
    for p in mis_publis:
        nick = 'MERCADOMUEBLES' if p['activa'] else 'MERCADOMUEBLES (pausada)'
        _exec("""INSERT INTO competencia_snapshots
                 (sku,tipo,modelo,medida,catalog_product_id,cp,cp_label,
                  seller_id,seller_nick,item_id,precio,cuotas_publi,cuotas_efectivas,
                  envio_tipo,envio_gratis,envio_costo,es_propio,pausada_sin_stock)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,1,%s)""",
              (sku,tipo,modelo,medida,catalog_id,cp,cp_label,
               MY_SELLER_ID,nick,p['mla_id'],p['precio'],
               p['cuotas_pub'],p['cuotas_ef'],p['envio_t'],
               1 if p['envio_free'] else 0, 1 if p['pausada'] else 0))
        rows_insertados += 1

    # Competidores
    all_results = _ml_catalog_all(catalog_id, cp)

    # Resolver nicknames
    seller_ids = {r['seller_id'] for r in all_results if r.get('seller_id') != MY_SELLER_ID}
    nicks = {}
    for sid in seller_ids:
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

    _comp_dedup = {}
    for r in all_results:
        sid = r.get('seller_id')
        if sid == MY_SELLER_ID or sid not in COMPETIDORES:
            continue
        lt = r.get('listing_type_id', '')
        sale_terms = r.get('sale_terms', [])
        camp = next((t.get('value_name', '').split('|')[0].strip()
                     for t in sale_terms
                     if t.get('id') == 'INSTALLMENTS_CAMPAIGN'), None)
        if not camp:
            camp = _campaign_from_tags(r.get('tags', []))
        cuotas_pub = _cuotas_publi(lt, camp)
        envio_t, envio_free, _ = _envio_tipo(r.get('shipping', {}))
        key = (sid, cuotas_pub, envio_t)
        precio = r.get('price') or 0
        if key not in _comp_dedup or precio < _comp_dedup[key]['precio']:
            _comp_dedup[key] = {
                'sid': sid, 'item_id': r.get('item_id'), 'precio': precio,
                'cq': cuotas_pub, 'envio_t': envio_t, 'envio_free': envio_free,
            }

    for item in _comp_dedup.values():
        _exec("""INSERT INTO competencia_snapshots
                 (sku,tipo,modelo,medida,catalog_product_id,cp,cp_label,
                  seller_id,seller_nick,item_id,precio,cuotas_publi,cuotas_efectivas,
                  envio_tipo,envio_gratis,envio_costo,es_propio,pausada_sin_stock)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0)""",
              (sku,tipo,modelo,medida,catalog_id,cp,cp_label,
               item['sid'],nicks.get(item['sid'],str(item['sid'])),item['item_id'],
               item['precio'],item['cq'],item['cq'],
               item['envio_t'],1 if item['envio_free'] else 0))
        rows_insertados += 1

    return rows_insertados

# ── Lista de SKUs a monitorear ────────────────────────────────────
def _get_skus_monitorear():
    rows = _q("""SELECT DISTINCT sku FROM sku_mla_mapeo
                 WHERE activo=1 AND sku NOT LIKE '%Z'
                 AND sku NOT IN ('CERVICAL','CLASICA')
                 AND sku NOT LIKE 'CCO%'
                 AND (sku LIKE 'C%' OR sku LIKE 'S%')
                 ORDER BY sku""")
    return [r['sku'] for r in rows]

# ── Agente principal ──────────────────────────────────────────────
def correr_agente(skus_filtro=None, delay_entre_skus=60):
    todos = _get_skus_monitorear()
    if skus_filtro:
        skus_up = [s.upper().rstrip('Z') for s in skus_filtro]
        skus = [s for s in todos if s.upper() in skus_up]
    else:
        skus = todos

    if not skus:
        return {'ok': False, 'error': 'No hay SKUs para procesar'}

    resultado = {
        'procesados': 0, 'sin_catalogo': [],
        'errores': [], 'total_rows': 0,
        'skus_total': len(skus)
    }

    for i, sku in enumerate(skus):
        if i > 0 and delay_entre_skus > 0:
            time.sleep(delay_entre_skus)

        # Hasta 2 intentos por SKU
        ok = False
        for intento in range(2):
            try:
                cat_id = _get_catalog_id(sku)
                if not cat_id:
                    resultado['sin_catalogo'].append(sku)
                    ok = True
                    break
                rows_n = _snapshot_catalogo(sku, cat_id)
                resultado['procesados'] += 1
                resultado['total_rows'] += rows_n
                ok = True
                break
            except Exception as e:
                if intento == 0:
                    print(f"[COMP] Reintentando {sku} tras error: {e}")
                    time.sleep(10)
                else:
                    resultado['errores'].append(f"{sku}: {e}")

    return {'ok': True, **resultado}

def job_competencia():
    """Job scheduler — usa lock en DB para evitar ejecución simultánea en múltiples workers."""
    # Intentar adquirir lock
    try:
        lock_row = _q("SELECT valor FROM configuracion WHERE clave='competencia_running'", one=True)
        if lock_row and lock_row['valor'] == '1':
            print("[COMPETENCIA] Ya hay un proceso corriendo, saltando este worker.")
            return
        _exec("""INSERT INTO configuracion (clave, valor)
                  VALUES ('competencia_running','1')
                  ON DUPLICATE KEY UPDATE valor='1'""")
    except Exception as e:
        print(f"[COMPETENCIA] Error adquiriendo lock: {e}")
        return

    try:
        skus = _get_skus_monitorear()
        print(f"[COMPETENCIA] {datetime.now()} — Iniciando snapshot completo ({len(skus)} SKUs)...")
        r = correr_agente(delay_entre_skus=60)
        print(f"[COMPETENCIA] Listo. Procesados:{r.get('procesados')} "
              f"Sin catálogo:{len(r.get('sin_catalogo',[]))} "
              f"Errores:{len(r.get('errores',[]))} "
              f"Rows:{r.get('total_rows')}")
        if r.get('errores'):
            print(f"[COMPETENCIA] Errores: {r['errores']}")
    finally:
        # Liberar lock siempre
        try:
            _exec("UPDATE configuracion SET valor='0' WHERE clave='competencia_running'")
        except Exception:
            pass

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
    # On-demand: sin delay entre SKUs si es un solo SKU, 5s si son varios
    delay = 0 if (skus and len(skus) == 1) else 5
    import threading
    resultado = {}
    def run():
        nonlocal resultado
        resultado = correr_agente(skus, delay_entre_skus=delay)
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=600)
    return jsonify(resultado)

@competencia_bp.route('/admin/competencia/datos')
def competencia_datos():
    sku_filtro  = request.args.get('sku', '').strip().upper()
    tipo_filtro = request.args.get('tipo', '')
    modelo_filtro = request.args.get('modelo', '')
    medida_filtro = request.args.get('medida', '')

    ultima = _q("SELECT MAX(fecha) as f FROM competencia_snapshots", one=True)
    if not ultima or not ultima['f']:
        return jsonify({'rows': [], 'ultima_fecha': None, 'filtros': {}})

    ultima_fecha = ultima['f']
    where = "WHERE DATE(s.fecha) = DATE(%s)"
    params = [ultima_fecha]

    if sku_filtro:
        where += " AND s.sku = %s"; params.append(sku_filtro)
    if tipo_filtro:
        where += " AND s.tipo = %s"; params.append(tipo_filtro)
    if modelo_filtro:
        where += " AND s.modelo = %s"; params.append(modelo_filtro)
    if medida_filtro:
        where += " AND s.medida = %s"; params.append(int(medida_filtro))

    rows = _q(f"""
        SELECT s.sku, s.tipo, s.modelo, s.medida,
               s.seller_nick, s.item_id, s.precio,
               s.cuotas_publi, s.cuotas_efectivas,
               s.envio_tipo, s.envio_gratis,
               s.es_propio, s.pausada_sin_stock, s.catalog_product_id
        FROM competencia_snapshots s
        {where}
        ORDER BY s.tipo, s.modelo, s.medida, s.sku, s.precio ASC
    """, params)

    def fix(r):
        return {k: (float(v) if hasattr(v, '__float__') and not isinstance(v, (int, bool)) else
                    str(v) if hasattr(v, 'strftime') else v)
                for k, v in r.items()}

    # Opciones para filtros
    filtros_rows = _q("""
        SELECT DISTINCT tipo, modelo, medida FROM competencia_snapshots
        WHERE DATE(fecha) = DATE(%s) ORDER BY tipo, modelo, medida
    """, [ultima_fecha])

    modelos = sorted(set(r['modelo'] for r in filtros_rows if r['modelo']))
    medidas = sorted(set(r['medida'] for r in filtros_rows if r['medida']))

    return jsonify({
        'rows': [fix(r) for r in rows],
        'ultima_fecha': str(ultima_fecha),
        'filtros': {
            'modelos': modelos,
            'medidas': [int(m) for m in medidas],
        }
    })

@competencia_bp.route('/admin/competencia/estado')
def competencia_estado():
    """Estadísticas del último snapshot."""
    row = _q("""SELECT COUNT(DISTINCT sku) as skus_con_datos,
                       MAX(fecha) as ultima_fecha
                FROM competencia_snapshots
                WHERE DATE(fecha) = CURDATE()""", one=True)
    sin_cat = _q("""SELECT COUNT(DISTINCT s.sku) as n FROM sku_mla_mapeo s
                    WHERE s.activo=1 AND s.sku NOT LIKE '%Z'
                    AND (s.sku LIKE 'C%' OR s.sku LIKE 'S%')
                    AND s.sku NOT IN ('CERVICAL','CLASICA')
                    AND s.sku NOT LIKE 'CCO%'
                    AND s.sku NOT IN (SELECT DISTINCT sku FROM competencia_snapshots WHERE DATE(fecha)=CURDATE())
                """, one=True)
    return jsonify({
        'skus_con_datos': row['skus_con_datos'] if row else 0,
        'skus_total': len(_get_skus_monitorear()),
        'skus_faltantes': sin_cat['n'] if sin_cat else 0,
        'ultima_fecha': str(row['ultima_fecha']) if row and row['ultima_fecha'] else None,
    })
