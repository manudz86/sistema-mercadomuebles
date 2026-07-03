# -*- coding: utf-8 -*-
"""
competencia_v2_bp.py — "Competencia V2" (BOTS)
Analiza las ventas mensuales de competidores (JSON del proveedor) y las compara
contra mis precios ACTUALES, por SKU y por tramo de cuota.

Precio ACTUAL de la competencia (jerarquía): monitor (competencia_snapshots) →
scraper (competencia_procesado.csv) → catálogo ML en vivo → precio del mes.
Mi precio: monitor (es_propio) → catálogo ML → /costos → (Compac: valor fijo).

Las VENTAS son históricas (del mes cargado); los PRECIOS se recalculan en vivo,
así que la comparación se actualiza sola con el refresco del monitor (2x/día).
Cachea el dataset por (vendedor, día) para no reconsultar en cada carga.
"""
import os, json, re, csv, datetime
from collections import defaultdict
import pymysql
from flask import Blueprint, render_template, request

# Helpers del monitor (import seguro; no importa app)
from competencia_bp import (_ml_catalog_all, _cuotas_publi, _campaign_from_tags,
                            _envio_tipo)

competencia_v2_bp = Blueprint('competencia_v2', __name__)

APP_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(APP_DIR, 'data', 'competencia_v2')
CSV_SCRAP = os.path.join(APP_DIR, 'data', 'competencia_procesado.csv')
MY_ID     = 29563319

VENDORS = {
    'TMS':   {'nombre': 'TMS', 'seller_id': 60351381, 'tienda': 'TMS',
              'files': [('tms_colchones.json', 'colchon'), ('tms_sommiers.json', 'sommier')]},
    'Lanus': {'nombre': 'Muebles Lanús', 'seller_id': 54898332, 'tienda': 'Lanus',
              'files': [('lanus_colchones.json', 'colchon'), ('lanus_sommier.json', 'sommier')]},
}

TIERS = ['sin', '3', '6', '9', '12']
TIER_LBL = {'sin': 'Contado', '3': '3 cuotas', '6': '6 cuotas', '9': '9 cuotas', '12': '12 cuotas'}
PORC_COMPAC = {'sin': 378000}  # Compac contado fijo; cuotas = _pc(378000, coef)

# ── Config cuotas (para calcular las cuotas del Compac) ──
def _porcentajes_ml(conn):
    with conn.cursor() as c:
        c.execute("SELECT valor FROM configuracion WHERE clave='porcentajes_ml'")
        r = c.fetchone()
    return json.loads(r['valor']) if r else {'cuotas_3': 8.4, 'cuotas_6': 12.3, 'cuotas_9': 15.7, 'cuotas_12': 19.2}

def _pc(base, pct):
    return round(base * 0.76 / (0.76 - pct / 100) / 1000) * 1000

# ── DB ──
def _db():
    return pymysql.connect(host='localhost', user='cannon',
        password=os.environ.get('DB_PASSWORD', 'Sistema@32267845'),
        db='inventario_cannon', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

def _price(v):
    v = str(v or '').strip().replace('.', '').replace(',', '.')
    try: return float(v)
    except: return 0.0

def _num(v, lo=2, hi=3):
    m = re.search(r'\d{%d,%d}' % (lo, hi), str(v or ''))
    return int(m.group()) if m else None

# ── Pasaje de ML (mostrada → real), igual criterio que el scraper ──
# Se carga de la config competencia_pasajes (real→mostrada) y se invierte.
def _cargar_pasaje_inv(conn):
    inv = {'colchon': {6:3, 9:6, 12:9, 18:12}, 'sommier': {6:3, 12:9, 18:12}}  # fallback
    try:
        with conn.cursor() as c:
            c.execute("SELECT valor FROM configuracion WHERE clave='competencia_pasajes'")
            r = c.fetchone()
        if r:
            d = json.loads(r['valor'])
            out = {'colchon': {}, 'sommier': {}}
            for t in ('colchon', 'sommier'):
                for real, most in d.get(t, []):
                    out[t][int(most)] = int(real)
            if out['colchon'] or out['sommier']:
                # completar con fallback lo que falte (ej. sommier 12→9, 18→12)
                for t in ('colchon', 'sommier'):
                    for k, v in inv[t].items():
                        out[t].setdefault(k, v)
                return out
    except Exception:
        pass
    return inv

def _real_tier(n, tipo, inv):
    """Convierte un nº de cuota MOSTRADO al REAL según el pasaje."""
    try: n = int(n)
    except (TypeError, ValueError): return None
    r = inv.get(tipo, {}).get(n, n)
    return str(r) if r in (3, 6, 9, 12) else None

# ── Cuota → tramo canónico ──
def _lbl_to_tier(lbl):
    if not lbl: return None
    l = lbl.lower()
    if 'sin cuota' in l or l == 'contado': return 'sin'
    if l.startswith('cuota simple'): return None
    m = re.search(r'(\d+)\s*cuota', l)
    if m:
        n = int(m.group(1))
        if n in (3, 6, 9, 12): return str(n)
        if n == 18: return '12'
    return None
def _inst_to_tier(inst, tipo, inv):
    """installments del JSON = MOSTRADO → se revierte al real por el pasaje."""
    if not inst or inst == 'no_installments': return 'sin'
    m = re.match(r'(\d+)_', inst)
    if not m: return 'sin'
    return _real_tier(m.group(1), tipo, inv) or str(int(m.group(1)))

# ── Match de SKU ──
MODMAP = [('exclusive pillow','EXP'),('exclusive euro','EXP'),('exclusive','EX'),
 ('renovation euro','REP'),('renovation pillow','REP'),('renovation','RE'),
 ('doral pillow','DOP'),('doral','DO'),('sublime','SUP'),('princess','PR'),
 ('soñar','SO'),('sonar','SO'),('tropical','TR'),('especial de lujo','EL'),
 ('compac','CO'),('clásico','CL'),('clasico','CL'),('infantil','INF'),('bajo cama','BC')]
def _modcod(model):
    m = (model or '').lower()
    for k, v in MODMAP:
        if k in m: return v
    return '?'
def _attrs(r):
    try: return {a['id']: a.get('value_name') for a in json.loads(r.get('attributes') or '[]')}
    except: return {}
def _medida(r, tipo):
    a = _attrs(r)
    if tipo == 'sommier':
        w, h = _num(a.get('MAIN_BED_WIDTH')), _num(a.get('MAIN_BED_HEIGHT'), 1, 2)
    else:
        w, h = _num(a.get('WIDTH')), _num(a.get('HEIGHT'), 1, 2)
        if not w and a.get('MATTRESS_SIZE'):
            mm = re.search(r'(\d{2,3})\s*[xX]\s*(\d{2,3})', a['MATTRESS_SIZE'])
            if mm: w = int(mm.group(1))
    if not w:
        mm = re.search(r'(\d{2,3})\s*[xX]', r.get('title', ''))
        if mm: w = int(mm.group(1))
    return w, h
def _match_sku(r, tipo, mis):
    w, h = _medida(r, tipo)
    cod = _modcod(r.get('model'))
    pref = 'S' if tipo == 'sommier' else 'C'
    if cod == '?' or not w:
        return None, w
    cands = []
    if cod == 'PR':
        for hh in ([h] if h else []) + [20, 23]:
            cands.append(f"{pref}{cod}{w}{hh}")
    cands += [f"{pref}{cod}{w}", f"{pref}{cod}{w}_DEP"]
    for c in cands:
        if c.upper() in mis:
            return c.upper(), w
    return None, w

# ── Fuentes de precio actual ──
def _cargar_mis_skus(conn):
    with conn.cursor() as c:
        c.execute("SELECT sku FROM productos_base WHERE COALESCE(activo,1)=1 "
                  "UNION SELECT sku FROM productos_compuestos WHERE activo=1")
        return set(r['sku'].upper() for r in c.fetchall())

def _cargar_monitor(conn, seller_id):
    with conn.cursor() as c:
        c.execute("SELECT MAX(DATE(fecha)) d FROM competencia_snapshots")
        d = c.fetchone()['d']
        c.execute("""SELECT sku, seller_id, cuotas_efectivas, precio, envio_tipo, es_propio
                     FROM competencia_snapshots WHERE DATE(fecha)=%s
                     AND seller_id IN (%s,%s) AND pausada_sin_stock=0""",
                  (d, seller_id, MY_ID))
        rows = c.fetchall()
    out = defaultdict(lambda: {'comp': {}, 'mio': {}, 'mio_env': {}})
    for r in rows:
        tier = _lbl_to_tier(r['cuotas_efectivas'])
        if not tier: continue
        pr = float(r['precio'] or 0)
        if pr <= 0: continue
        sku = r['sku'].upper()
        if r['es_propio']:
            cur = out[sku]['mio'].get(tier); env = r['envio_tipo']
            prefer = (env == 'ME1')
            if cur is None or pr < cur or (prefer and out[sku]['mio_env'].get(tier) != 'ME1'):
                out[sku]['mio'][tier] = pr; out[sku]['mio_env'][tier] = env
        else:
            cur = out[sku]['comp'].get(tier)
            if cur is None or pr < cur:
                out[sku]['comp'][tier] = pr
    return out, str(d)

def _cargar_scraper(tienda):
    inv = {'colchon': {6:3,9:6,12:9,18:12}, 'sommier': {6:3,12:9,18:12}}
    out = defaultdict(dict)
    if not os.path.exists(CSV_SCRAP): return out
    for r in csv.DictReader(open(CSV_SCRAP, encoding='utf-8')):
        if r['tienda'] != tienda: continue
        sku = (r['sku_match'] or '').strip().upper()
        if not sku: continue
        if (r.get('pack','1') or '1') != '1' or int(r.get('almohadas','0') or 0) != 0: continue
        if r.get('medida_origen') == 'inferida' or r.get('cuotas_simple','0') == '1': continue
        p = _price(r.get('precio'))
        if p <= 0: continue
        cs = (r.get('cuotas_si') or '').strip()
        if not cs:
            tier = 'sin'
        else:
            try: n = int(cs)
            except: continue
            real = inv.get(r['tipo'], {}).get(n, n)
            tier = str(real) if real in (3,6,9,12) else None
        if not tier: continue
        if tier not in out[sku] or p < out[sku][tier]:
            out[sku][tier] = p
    return out

# catálogo ML — cache por catalog_id por día
_cat_cache = {}
def _cargar_catalogo(catalog_id, seller_id, hoy, tipo, inv):
    ck = (catalog_id, seller_id)
    hit = _cat_cache.get(ck)
    if hit and hit[0] == hoy:
        return hit[1]
    res = _ml_catalog_all(catalog_id, '1425')
    comp, mio, mio_env = {}, {}, {}
    for r in res:
        sid = r.get('seller_id')
        if sid not in (seller_id, MY_ID): continue
        lt = r.get('listing_type_id', '')
        camp = next((t.get('value_name','').split('|')[0].strip()
                     for t in r.get('sale_terms', []) if t.get('id')=='INSTALLMENTS_CAMPAIGN'), None)
        if not camp: camp = _campaign_from_tags(r.get('tags', []))
        tier = _lbl_to_tier(_cuotas_publi(lt, camp))
        # gold_pro sin campaña: ML muestra "6 cuotas" por default (MOSTRADO) →
        # revertir al real por el pasaje, igual criterio que el scraper.
        if lt == 'gold_pro' and not camp and tier and tier.isdigit():
            tier = _real_tier(tier, tipo, inv)
        if not tier: continue
        env, _, _ = _envio_tipo(r.get('shipping', {}))
        p = r.get('price') or 0
        if p <= 0: continue
        if sid == MY_ID:
            prefer = (env == 'ME1')
            if tier not in mio or p < mio[tier] or (prefer and mio_env.get(tier) != 'ME1'):
                mio[tier] = p; mio_env[tier] = env
        else:
            if tier not in comp or p < comp[tier]:
                comp[tier] = p
    out = {'comp': comp, 'mio': mio}
    _cat_cache[ck] = (hoy, out)
    return out

def _catalog_id_de(sku, prov_cat_id, conn):
    if prov_cat_id and str(prov_cat_id).strip():
        return 'MLA' + str(prov_cat_id).strip()
    base = sku.rstrip('Z').replace('_DEP', '')
    with conn.cursor() as c:
        c.execute("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1 LIMIT 5", (base,))
        mlas = [r['mla_id'] for r in c.fetchall()]
    import requests
    from competencia_bp import _token
    for mla in mlas:
        try:
            r = requests.get(f"https://api.mercadolibre.com/items/{mla}",
                             headers={'Authorization': f'Bearer {_token()}'},
                             params={'attributes': 'id,catalog_product_id'}, timeout=12)
            if r.status_code == 200 and r.json().get('catalog_product_id'):
                return r.json()['catalog_product_id']
        except: pass
    return None

# ── mi precio Compac (fijo) ──
def _mi_compac(conn):
    pml = _porcentajes_ml(conn)
    base = PORC_COMPAC['sin']
    return {'sin': base, '3': _pc(base, pml.get('cuotas_3', 8.4)),
            '6': _pc(base, pml.get('cuotas_6', 12.3)), '9': _pc(base, pml.get('cuotas_9', 15.7)),
            '12': _pc(base, pml.get('cuotas_12', 19.2))}

# ── mi precio por /costos (función real, import perezoso in-proc) ──
def _mi_costos(sku):
    try:
        from app import _get_precio_costos_sku
        pc = _get_precio_costos_sku(sku) or _get_precio_costos_sku(sku.replace('_DEP', ''))
        if not pc: return {}
        return {'sin': pc['precio_sin_cuotas'], '3': pc['precio_3c'], '6': pc['precio_6c'],
                '9': pc['precio_9c'], '12': pc['precio_12c']}
    except Exception:
        return {}

# ── Construcción del dataset por vendedor ──
# Cache en archivo, atado al snapshot del monitor: carga rápido entre workers y
# se recalcula solo cuando el monitor guarda un snapshot nuevo (2x/día).
def _cache_path(vendor_key, snap_ts):
    safe = re.sub(r'[^0-9]', '', str(snap_ts))
    return os.path.join(DATA_DIR, f'.cache_{vendor_key}_{safe}.json')

def _construir(vendor_key):
    hoy = datetime.date.today().isoformat()
    conn = _db()
    with conn.cursor() as c:
        c.execute("SELECT MAX(fecha) t FROM competencia_snapshots")
        snap_ts = c.fetchone()['t']
    cpath = _cache_path(vendor_key, snap_ts)
    if os.path.exists(cpath):
        try:
            conn.close()
            with open(cpath, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    V = VENDORS[vendor_key]
    mis = _cargar_mis_skus(conn)
    mon, snap = _cargar_monitor(conn, V['seller_id'])
    scr = _cargar_scraper(V['tienda'])
    compac_precio = _mi_compac(conn)
    inv = _cargar_pasaje_inv(conn)

    productos = {}
    for fname, tipo in V['files']:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path): continue
        for r in json.load(open(path, encoding='utf-8')):
            sku, w = _match_sku(r, tipo, mis)
            q = int(r.get('sold_quantity') or 0)
            g = _price(r.get('gmv')); p = _price(r.get('price'))
            tier = _inst_to_tier(r.get('installments'), tipo, inv)
            key = sku or f"NOMATCH|{tipo}|{r.get('model')}|{w}"
            P = productos.get(key)
            if not P:
                P = productos[key] = {'sku': sku, 'tipo': tipo, 'model': r.get('model'),
                    'w': w, 'u': 0, 'gmv': 0.0, 'cuota_u': defaultdict(int),
                    'pjunio': defaultdict(list), 'prov_cat': r.get('catalog_product_id'),
                    'es_cat': r.get('is_catalog_product') == 'yes'}
            P['u'] += q; P['gmv'] += g; P['cuota_u'][tier] += q
            if p > 0: P['pjunio'][tier].append(p)
            if not P['prov_cat'] and r.get('catalog_product_id'):
                P['prov_cat'] = r.get('catalog_product_id')

    for key, P in productos.items():
        sku = P['sku']
        P['comp_now'] = {}; P['mio_now'] = {}; P['fuente'] = {}
        if not sku: continue
        es_compac = sku.startswith('CCO')
        m = mon.get(sku) or mon.get(sku.replace('_DEP', '')) or {'comp': {}, 'mio': {}}
        scr_sku = scr.get(sku) or scr.get(sku.replace('_DEP', '')) or {}
        costos = None
        for tier in TIERS:
            src = None; comp_p = None
            if m.get('comp', {}).get(tier):
                comp_p = m['comp'][tier]; src = 'monitor'
            elif scr_sku.get(tier):
                comp_p = scr_sku[tier]; src = 'scraper'
            mio_p = None if es_compac else m.get('mio', {}).get(tier)
            if comp_p is None and P['es_cat']:
                cid = _catalog_id_de(sku, P['prov_cat'], conn)
                if cid:
                    cat = _cargar_catalogo(cid, V['seller_id'], hoy, P['tipo'], inv)
                    if cat['comp'].get(tier):
                        comp_p = cat['comp'][tier]; src = 'catalogo_ml'
                    if mio_p is None and not es_compac and cat['mio'].get(tier):
                        mio_p = cat['mio'][tier]
            if es_compac:
                mio_p = compac_precio.get(tier)
            elif mio_p is None:
                if costos is None: costos = _mi_costos(sku)
                if costos.get(tier): mio_p = costos[tier]
            if comp_p is None and P['pjunio'].get(tier):
                vals = sorted(P['pjunio'][tier]); comp_p = vals[len(vals)//2]; src = 'mes'
            if comp_p is not None:
                P['comp_now'][tier] = comp_p; P['fuente'][tier] = src
            if mio_p is not None:
                P['mio_now'][tier] = mio_p
    conn.close()

    vistas = _armar_vistas(productos, V, snap)
    # Guardar cache (y limpiar caches viejos de este vendedor)
    try:
        for old in os.listdir(DATA_DIR):
            if old.startswith(f'.cache_{vendor_key}_') and os.path.join(DATA_DIR, old) != cpath:
                try: os.remove(os.path.join(DATA_DIR, old))
                except Exception: pass
        with open(cpath, 'w', encoding='utf-8') as f:
            json.dump(vistas, f, ensure_ascii=False, default=str)
    except Exception:
        pass
    return vistas

def _dcls(d):
    return 'g2' if d <= -10 else ('g1' if d < 0 else ('r1' if d < 10 else 'r2'))

def _armar_vistas(productos, V, snap):
    con = [p for p in productos.values() if p['sku']]
    nomatch = [p for p in productos.values() if not p['sku']]

    # A — precio (fila por sku×tramo)
    A = []
    for p in con:
        for t in TIERS:
            comp = p['comp_now'].get(t)
            if not comp: continue
            mio = p['mio_now'].get(t)
            d = (mio/comp - 1) * 100 if (comp and mio) else None
            A.append({'sku': p['sku'], 'model': p['model'], 'w': p['w'], 'tipo': p['tipo'],
                'tier': t, 'tier_lbl': TIER_LBL[t], 'u': p['cuota_u'].get(t, 0),
                'comp': comp, 'mio': mio, 'd': d, 'dtxt': (f"{d:+.0f}%" if d is not None else None),
                'cls': (_dcls(d) if d is not None else ''), 'fu': p['fuente'].get(t)})
    A.sort(key=lambda x: (-x['u'], x['sku']))
    caros = sum(1 for f in A if f['d'] is not None and f['d'] > 0 and f['u'] >= 5)

    # B — cuotas
    B = []; tot = defaultdict(int)
    for p in sorted(con, key=lambda x: -x['u']):
        cu = p['cuota_u']; u = p['u']
        cells = []
        for t in TIERS:
            v = cu.get(t, 0); tot[t] += v
            cells.append({'v': v, 'pct': (100*v/u if u else 0)})
        B.append({'sku': p['sku'], 'model': p['model'], 'u': u, 'cells': cells})
    U = sum(tot.values()) or 1
    Btot = [{'v': tot[t], 'pct': 100*tot[t]/U} for t in TIERS]

    # C — mix (pareto)
    allp = sorted(con + nomatch, key=lambda x: -x['gmv'])
    gtot = sum(p['gmv'] for p in allp) or 1
    gmax = max((p['gmv'] for p in allp), default=1)
    C = []; cum = 0
    for p in allp[:40]:
        cum += p['gmv']
        C.append({'nombre': p['sku'] or f"({p['model']} {p['w']})", 'model': p['model'],
            'tiene': bool(p['sku']), 'u': p['u'], 'gmv': p['gmv'],
            'share': 100*p['gmv']/gtot, 'cum': 100*cum/gtot, 'barw': int(120*p['gmv']/gmax)})

    # D — oportunidad
    agg = defaultdict(lambda: {'u': 0, 'gmv': 0.0, 'model': '', 'w': None, 'tipo': '', 'contado': 0})
    for p in nomatch:
        k = (p['model'], p['w'], p['tipo'])
        a = agg[k]; a['u'] += p['u']; a['gmv'] += p['gmv']; a['model'] = p['model']
        a['w'] = p['w']; a['tipo'] = p['tipo']; a['contado'] += p['cuota_u'].get('sin', 0)
    D = []
    for k, a in sorted(agg.items(), key=lambda x: -x[1]['u']):
        D.append({'model': a['model'], 'w': a['w'], 'tipo': a['tipo'], 'u': a['u'],
            'gmv': a['gmv'], 'pct_contado': (100*a['contado']/a['u'] if a['u'] else 0)})

    return {'snap': snap, 'A': A, 'caros': caros, 'B': B, 'Btot': Btot,
            'C': C, 'D': D, 'tiers': TIERS, 'tier_lbl': TIER_LBL,
            'n_skus': len(con), 'u_con': sum(p['u'] for p in con),
            'u_no': sum(p['u'] for p in nomatch), 'gmv_tot': gtot}


@competencia_v2_bp.route('/admin/competencia-v2')
def competencia_v2_page():
    vendor = request.args.get('vendedor', 'TMS')
    if vendor not in VENDORS:
        vendor = 'TMS'
    try:
        data = _construir(vendor)
    except Exception as e:
        data = None
        err = str(e)
    else:
        err = None
    return render_template('competencia_v2.html',
        vendor=vendor, vendor_nombre=VENDORS[vendor]['nombre'],
        vendors=VENDORS, data=data, err=err)
