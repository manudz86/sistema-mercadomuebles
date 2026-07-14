# -*- coding: utf-8 -*-
"""
competencia_v2_bp.py — "Competencia V2" (BOTS)
Ventas mensuales de competidores (JSON del integrador) vs mis precios, por SKU y
por cuota REAL.

IMPORTANTE: el `installments` del JSON es la cuota REAL de la publicación (el
"pasaje" de ML es solo visual y NO se descuenta). Por eso NO se revierte.

Precio ACTUAL del competidor (jerarquía que definió el usuario):
  - Publi de CATÁLOGO:   monitor (competencia_snapshots) → scraper → catálogo ML (fórmula del monitor)
  - Publi NO de catálogo: scraper
  - Último recurso: el precio del propio JSON (marcado 'json').
Mi precio: mi publi ML (monitor es_propio) → /costos → (Compac: contado fijo 378k).

Los precios se recalculan en vivo (cache por snapshot del monitor).
"""
import os, json, re, csv, datetime
from collections import defaultdict
import pymysql
from flask import Blueprint, render_template, request, redirect, url_for

from competencia_bp import (_ml_catalog_all, _cuotas_publi, _campaign_from_tags,
                            _envio_tipo)

competencia_v2_bp = Blueprint('competencia_v2', __name__)

APP_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(APP_DIR, 'data', 'competencia_v2')
CSV_SCRAP = os.path.join(APP_DIR, 'data', 'competencia_procesado.csv')
MY_ID     = 29563319

# vendedor → alias en el JSON + seller_id (ML) + tienda (scraper)
VENDOR_META = {
    'TMS':       {'nombre': 'TMS',                  'alias': 'TU MEJOR SOMMIER',      'seller_id': 60351381,  'tienda': 'TMS'},
    'Ivana':     {'nombre': 'Colchonería Ivana',    'alias': 'COLCHONERIA IVANA',     'seller_id': 192769857, 'tienda': 'Ivana'},
    'Lanus':     {'nombre': 'Muebles Lanús',        'alias': 'MUEBLES LANUS',         'seller_id': 54898332,  'tienda': 'Lanus'},
    'Ballester': {'nombre': 'Colchonería Ballester', 'alias': 'COLCHONERIA BALLESTER', 'seller_id': 658910977, 'tienda': 'Ballester'},
    'Bedpoint':  {'nombre': 'Bedpoint',             'alias': 'BEDPOINT',              'seller_id': 168211358, 'tienda': 'Bedpoint'},
    'Metymas':   {'nombre': 'Metymas',              'alias': 'METYMAS',               'seller_id': 105539832, 'tienda': 'Metymas'},
    'Mercadomuebles': {'nombre': 'Mercadomuebles (vos)', 'alias': 'MERCADOMUEBLES (YO)', 'seller_id': MY_ID,   'tienda': None},
    'Milesi':    {'nombre': 'Milesi Hogar',         'alias': 'MILESI HOGAR',          'seller_id': None,      'tienda': None},
}
VENDORS_ORDEN = ['TMS', 'Ivana', 'Lanus', 'Ballester', 'Bedpoint', 'Metymas', 'Mercadomuebles']
# En "Ventas Competidores" además se puede ver a vendedores de solo-almohadas (Milesi).
VENDORS_VC = VENDORS_ORDEN + ['Milesi']
# Períodos DINÁMICOS: cada subcarpeta YYYY-MM de DATA_DIR con colchones.json/sommiers.json.
# Así, subir un período nuevo desde el sistema lo hace aparecer solo.
_MESES_ES = {'01':'Enero','02':'Febrero','03':'Marzo','04':'Abril','05':'Mayo','06':'Junio',
             '07':'Julio','08':'Agosto','09':'Septiembre','10':'Octubre','11':'Noviembre','12':'Diciembre'}
def _periodo_lbl(p):
    m = re.match(r'^(\d{4})-(\d{2})$', str(p or ''))
    return f"{_MESES_ES.get(m.group(2), m.group(2))} {m.group(1)}" if m else str(p or '')

# Archivos de datos por categoría. 'colchon'/'sommier' alimentan la comparación de
# precios (pestañas A–D); 'almohada' va SOLO al ranking (no tiene match de SKU/precio).
FILE_TIPOS = [('colchones.json', 'colchon'), ('sommiers.json', 'sommier'), ('almohadas.json', 'almohada')]
CAT_LBL = {'almohada': 'Almohadas', 'colchon': 'Colchones', 'sommier': 'Sommiers'}
CAT_ORDEN = ['almohada', 'colchon', 'sommier']

def PERIODOS():
    """{periodo: [(archivo, tipo)]} escaneando las carpetas de datos."""
    out = {}
    if os.path.isdir(DATA_DIR):
        for d in sorted(os.listdir(DATA_DIR), reverse=True):
            p = os.path.join(DATA_DIR, d)
            if not (os.path.isdir(p) and re.match(r'^\d{4}-\d{2}$', d)):
                continue
            files = [(fn, tp) for fn, tp in FILE_TIPOS if os.path.exists(os.path.join(p, fn))]
            if files: out[d] = files
    return out

TIERS = ['sin', '3', '6', '9', '12']
TIER_LBL = {'sin': 'Contado', '3': '3 cuotas', '6': '6 cuotas', '9': '9 cuotas', '12': '12 cuotas'}
PORC_COMPAC = {'sin': 378000}   # Compac contado fijo; cuotas = _pc(378000, coef)

def _porcentajes_ml(conn):
    with conn.cursor() as c:
        c.execute("SELECT valor FROM configuracion WHERE clave='porcentajes_ml'")
        r = c.fetchone()
    return json.loads(r['valor']) if r else {'cuotas_3': 8.4, 'cuotas_6': 12.3, 'cuotas_9': 15.7, 'cuotas_12': 19.2}

def _pc(base, pct):
    return round(base * 0.76 / (0.76 - pct / 100) / 1000) * 1000

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

# ── Cuota → tramo. installments del JSON = REAL (no se revierte). ──
def _lbl_to_tier(lbl):
    if not lbl: return None
    l = lbl.lower()
    if 'sin cuota' in l or l == 'contado': return 'sin'
    if l.startswith('cuota simple'): return None
    m = re.search(r'(\d+)\s*cuota', l)
    if m:
        n = int(m.group(1))
        if n in (3, 6, 9, 12): return str(n)
        if n >= 18: return '12'
    return None
def _inst_to_tier(inst):
    if not inst or inst == 'no_installments': return 'sin'
    m = re.match(r'(\d+)_', inst)
    if not m: return 'sin'
    n = int(m.group(1))
    if n in (3, 6, 9, 12): return str(n)
    if n >= 18: return '12'
    return None

# ── Match de SKU ──
def _modcod(model, title='', pillow_attr=False):
    """Detecta el código de modelo. El `model` del JSON no es confiable para el
    pillow, así que la variante CON pillow (EXP/REP/DOP) se detecta por la UNIÓN de:
    título (euro/doble/c-pillow/EP) OR atributo de la publicación (WITH_PILLOW='Sí'
    o SURFACE con pillow). Así cada fuente tapa lo que le falta a la otra."""
    m = (model or '').lower()
    txt = f"{model or ''} {title or ''}".lower().replace('sin pillow', '')
    pillow = bool(re.search(r'\b(ep|europillow|euro|pillow)\b', txt)) or 'c/pillow' in txt or bool(pillow_attr)
    if 'exclusive' in m or 'exclusive' in txt:   return 'EXP' if pillow else 'EX'
    if 'renovation' in m or 'renovation' in txt: return 'REP' if pillow else 'RE'
    if 'doral' in m or 'doral' in txt:           return 'DOP' if pillow else 'DO'
    if 'sublime' in m:    return 'SUP'
    if 'princess' in m:   return 'PR'
    if 'soñar' in m or 'sonar' in m: return 'SO'
    if 'tropical' in m:   return 'TR'
    if 'especial de lujo' in m: return 'EL'
    if 'compac' in m:     return 'CO'
    if 'clásico' in m or 'clasico' in m: return 'CL'
    if 'infantil' in m:   return 'INF'
    if 'bajo cama' in m:  return 'BC'
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
    a = _attrs(r)
    surf = (a.get('SURFACE_CONTACT_TYPE') or '').lower()
    pillow_attr = (a.get('WITH_PILLOW') == 'Sí') or ('pillow' in surf and 'sin pillow' not in surf)
    cod = _modcod(r.get('model'), r.get('title'), pillow_attr)
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

# ── Match de almohadas (modelo → mi SKU, con tamaño de pack) ──
_ALM_MODELOS = [('platino', 'PLATINO'), ('doral', 'DORAL'), ('exclusive', 'EXCLUSIVE'),
                ('renovation', 'RENOVATION'), ('sublime', 'SUBLIME'), ('dual', 'DUAL'),
                ('cervical', 'CERVICAL'), ('clásica', 'CLASICA'), ('clasica', 'CLASICA')]
def _match_almohada(title, mis):
    """(sku, pack) de una almohada del competidor: sku = mi SKU si el modelo
    aparece en el título; pack = unidades del combo (default 1)."""
    t = (title or '').lower()
    sku = None
    for kw, s in _ALM_MODELOS:
        if kw in t and s in mis:
            sku = s
            break
    pack = 1
    m = re.search(r'(?:combo|pack|x)\s*(\d{1,2})\b', t) or re.search(r'(\d{1,2})\s*unidad', t)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 12:
            pack = n
    return sku, pack

def _precios_almohadas(conn):
    with conn.cursor() as c:
        c.execute("SELECT sku, precio_base FROM productos_base WHERE tipo='almohada' AND COALESCE(activo,1)=1")
        return {r['sku'].upper(): float(r['precio_base'] or 0) for r in c.fetchall()}

# ── Fuentes de precio ──
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
    inv = {'colchon': {6:3, 9:6, 12:9, 18:12}, 'sommier': {6:3, 12:9, 18:12}}
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
            real = inv.get(r['tipo'], {}).get(n, n)   # scraper: mostrada→real
            tier = str(real) if real in (3,6,9,12) else None
        if not tier: continue
        if tier not in out[sku] or p < out[sku][tier]:
            out[sku][tier] = p
    return out

# catálogo ML — cache por catalog_id/día. SIN reversión (installments=real; el
# catálogo con la fórmula del monitor ya trae la cuota bien).
_cat_cache = {}
def _cargar_catalogo(catalog_id, seller_id, hoy):
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

def _mi_compac(conn):
    pml = _porcentajes_ml(conn); base = PORC_COMPAC['sin']
    return {'sin': base, '3': _pc(base, pml.get('cuotas_3', 8.4)),
            '6': _pc(base, pml.get('cuotas_6', 12.3)), '9': _pc(base, pml.get('cuotas_9', 15.7)),
            '12': _pc(base, pml.get('cuotas_12', 19.2))}

def _mi_costos(sku):
    try:
        from app import _get_precio_costos_sku
        pc = _get_precio_costos_sku(sku) or _get_precio_costos_sku(sku.replace('_DEP', ''))
        if not pc: return {}
        return {'sin': pc['precio_sin_cuotas'], '3': pc['precio_3c'], '6': pc['precio_6c'],
                '9': pc['precio_9c'], '12': pc['precio_12c']}
    except Exception:
        return {}

# ── Construcción del dataset ──
def _cache_path(periodo, vendedor, snap_ts):
    safe = re.sub(r'[^0-9]', '', str(snap_ts))
    return os.path.join(DATA_DIR, f'.cache_{periodo}_{vendedor}_{safe}.json')

def _construir(periodo, vendedor):
    conn = _db()
    with conn.cursor() as c:
        c.execute("SELECT MAX(fecha) t FROM competencia_snapshots")
        snap_ts = c.fetchone()['t']
    cpath = _cache_path(periodo, vendedor, snap_ts)
    if os.path.exists(cpath):
        try:
            conn.close()
            with open(cpath, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    meta = VENDOR_META[vendedor]
    alias = meta['alias']
    # las almohadas no entran a la comparación de precios (no tienen match de SKU)
    files = [ft for ft in PERIODOS().get(periodo, []) if ft[1] != 'almohada']
    mis = _cargar_mis_skus(conn)
    mon, snap = _cargar_monitor(conn, meta['seller_id'])
    scr = _cargar_scraper(meta['tienda']) if meta['tienda'] else {}
    compac_precio = _mi_compac(conn)

    productos = {}
    for fname, tipo in files:
        path = os.path.join(DATA_DIR, periodo, fname)
        if not os.path.exists(path): continue
        for r in json.load(open(path, encoding='utf-8')):
            if r.get('alias') != alias: continue
            sku, w = _match_sku(r, tipo, mis)
            q = int(r.get('sold_quantity') or 0)
            p = _price(r.get('price')); g = q * p   # GMV real (el del JSON viene redondeado)
            tier = _inst_to_tier(r.get('installments'))
            if tier is None: continue
            key = sku or f"NOMATCH|{tipo}|{r.get('model')}|{w}"
            P = productos.get(key)
            if not P:
                P = productos[key] = {'sku': sku, 'tipo': tipo, 'model': r.get('model'),
                    'w': w, 'u': 0, 'gmv': 0.0, 'cuota_u': defaultdict(int),
                    'pjson': defaultdict(list), 'prov_cat': r.get('catalog_product_id'),
                    'es_cat': r.get('is_catalog_product') == 'yes', 'titulos': defaultdict(int),
                    'cuota_gmv': defaultdict(float)}
            P['u'] += q; P['gmv'] += g; P['cuota_u'][tier] += q; P['cuota_gmv'][tier] += g
            if r.get('title'): P['titulos'][r['title']] += q
            if p > 0: P['pjson'][tier].append(p)
            if r.get('is_catalog_product') == 'yes': P['es_cat'] = True
            if not P['prov_cat'] and r.get('catalog_product_id'):
                P['prov_cat'] = r.get('catalog_product_id')

    for key, P in productos.items():
        sku = P['sku']
        P['comp_now'] = {}; P['mio_now'] = {}; P['fuente'] = {}
        if not sku: continue
        es_compac = sku.startswith('CCO')
        m = mon.get(sku) or mon.get(sku.replace('_DEP', '')) or {'comp': {}, 'mio': {}}
        scr_sku = scr.get(sku) or scr.get(sku.replace('_DEP', '')) or {}
        cat = None
        def _cat():
            nonlocal cat
            if cat is None:
                cid = _catalog_id_de(sku, P['prov_cat'], conn)
                cat = _cargar_catalogo(cid, meta['seller_id'], datetime.date.today().isoformat()) if cid else {'comp': {}, 'mio': {}}
            return cat
        costos = None
        for tier in TIERS:
            # ── precio del competidor (jerarquía) ──
            comp_p, src = None, None
            if P['es_cat']:
                if m.get('comp', {}).get(tier):
                    comp_p, src = m['comp'][tier], 'monitor'
                elif scr_sku.get(tier):
                    comp_p, src = scr_sku[tier], 'scraper'
                elif _cat()['comp'].get(tier):
                    comp_p, src = _cat()['comp'][tier], 'catalogo_ml'
            else:
                if scr_sku.get(tier):
                    comp_p, src = scr_sku[tier], 'scraper'
            if comp_p is None and P['pjson'].get(tier):
                vals = sorted(P['pjson'][tier]); comp_p, src = vals[len(vals)//2], 'json'
            # ── mi precio: mi publi ML (monitor) → catálogo → /costos → Compac ──
            if es_compac:
                mio_p = compac_precio.get(tier)
            else:
                mio_p = m.get('mio', {}).get(tier)
                if mio_p is None and P['es_cat'] and _cat()['mio'].get(tier):
                    mio_p = _cat()['mio'][tier]
                if mio_p is None:
                    if costos is None: costos = _mi_costos(sku)
                    if costos.get(tier): mio_p = costos[tier]
            if comp_p is not None:
                P['comp_now'][tier] = comp_p; P['fuente'][tier] = src
            if mio_p is not None:
                P['mio_now'][tier] = mio_p
    conn.close()

    vistas = _armar_vistas(productos, meta, snap, periodo)
    try:
        for old in os.listdir(DATA_DIR):
            if old.startswith(f'.cache_{periodo}_{vendedor}_') and os.path.join(DATA_DIR, old) != cpath:
                try: os.remove(os.path.join(DATA_DIR, old))
                except Exception: pass
        with open(cpath, 'w', encoding='utf-8') as f:
            json.dump(vistas, f, ensure_ascii=False, default=str)
    except Exception:
        pass
    return vistas

def _dcls(d):
    return 'g2' if d <= -10 else ('g1' if d < 0 else ('r1' if d < 10 else 'r2'))

def _armar_vistas(productos, meta, snap, periodo):
    con = [p for p in productos.values() if p['sku']]
    nomatch = [p for p in productos.values() if not p['sku']]

    def _tit(p):
        """(título representativo = el de más unidades, todos los distintos)."""
        ts = p.get('titulos') or {}
        if not ts: return '', ''
        rep = max(ts.items(), key=lambda x: x[1])[0]
        return rep, ' | '.join(sorted(ts.keys()))

    A = []
    for p in con:
        rep, allt = _tit(p)
        for t in TIERS:
            comp = p['comp_now'].get(t)
            if not comp: continue
            u_t = p['cuota_u'].get(t, 0)
            if u_t == 0: continue   # solo tramos donde el competidor realmente vendió
            mio = p['mio_now'].get(t)
            d = (mio/comp - 1) * 100 if (comp and mio) else None
            A.append({'sku': p['sku'], 'model': p['model'], 'w': p['w'], 'tipo': p['tipo'],
                'tier': t, 'tier_lbl': TIER_LBL[t], 'u': p['cuota_u'].get(t, 0),
                'gmv': p['cuota_gmv'].get(t, 0),
                'comp': comp, 'mio': mio, 'd': d, 'dtxt': (f"{d:+.0f}%" if d is not None else None),
                'cls': (_dcls(d) if d is not None else ''), 'fu': p['fuente'].get(t),
                'titulo': rep, 'titulos': allt})
    A.sort(key=lambda x: (-x['u'], x['sku']))
    caros = sum(1 for f in A if f['d'] is not None and f['d'] > 0 and f['u'] >= 5)

    B = []; tot = defaultdict(int)
    for p in sorted(con, key=lambda x: -x['u']):
        cu = p['cuota_u']; u = p['u']; cells = []
        for t in TIERS:
            v = cu.get(t, 0); tot[t] += v
            cells.append({'v': v, 'pct': (100*v/u if u else 0)})
        B.append({'sku': p['sku'], 'model': p['model'], 'u': u, 'cells': cells})
    U = sum(tot.values()) or 1
    Btot = [{'v': tot[t], 'pct': 100*tot[t]/U} for t in TIERS]

    allp = sorted(con + nomatch, key=lambda x: -x['gmv'])
    gtot = sum(p['gmv'] for p in allp) or 1
    gmax = max((p['gmv'] for p in allp), default=1)
    C = []; cum = 0
    for p in allp[:40]:
        cum += p['gmv']
        C.append({'nombre': p['sku'] or f"({p['model']} {p['w']})", 'model': p['model'],
            'tiene': bool(p['sku']), 'u': p['u'], 'gmv': p['gmv'],
            'share': 100*p['gmv']/gtot, 'cum': 100*cum/gtot, 'barw': int(120*p['gmv']/gmax)})

    agg = defaultdict(lambda: {'u': 0, 'gmv': 0.0, 'model': '', 'w': None, 'tipo': '', 'contado': 0, 'titulos': {}})
    for p in nomatch:
        k = (p['model'], p['w'], p['tipo'])
        a = agg[k]; a['u'] += p['u']; a['gmv'] += p['gmv']; a['model'] = p['model']
        a['w'] = p['w']; a['tipo'] = p['tipo']; a['contado'] += p['cuota_u'].get('sin', 0)
        for tt, qq in (p.get('titulos') or {}).items():
            a['titulos'][tt] = a['titulos'].get(tt, 0) + qq
    D = []
    for k, a in sorted(agg.items(), key=lambda x: -x[1]['u']):
        ts = a['titulos']
        rep = max(ts.items(), key=lambda x: x[1])[0] if ts else ''
        D.append({'model': a['model'], 'w': a['w'], 'tipo': a['tipo'], 'u': a['u'],
            'gmv': a['gmv'], 'pct_contado': (100*a['contado']/a['u'] if a['u'] else 0),
            'titulo': rep, 'titulos': (' | '.join(sorted(ts.keys())) if ts else '')})

    return {'snap': snap, 'periodo': periodo, 'A': A, 'caros': caros, 'B': B, 'Btot': Btot,
            'C': C, 'D': D, 'tiers': TIERS, 'tier_lbl': TIER_LBL,
            'n_skus': len(con), 'u_con': sum(p['u'] for p in con),
            'u_no': sum(p['u'] for p in nomatch), 'gmv_tot': gtot}


@competencia_v2_bp.route('/admin/competencia-v2')
def competencia_v2_page():
    pers = PERIODOS()
    pers_orden = sorted(pers.keys(), reverse=True)
    periodo = request.args.get('periodo') or (pers_orden[0] if pers_orden else '')
    if periodo not in pers:
        periodo = pers_orden[0] if pers_orden else ''
    vends = VENDORS_ORDEN
    vendor = request.args.get('vendedor') or vends[0]
    if vendor not in vends:
        vendor = vends[0]
    try:
        data = _construir(periodo, vendor) if periodo else None
        err = None if periodo else 'No hay períodos cargados todavía.'
    except Exception as e:
        data, err = None, str(e)
    return render_template('competencia_v2.html',
        periodo=periodo, periodos=pers, periodo_lbl={p: _periodo_lbl(p) for p in pers},
        vendor=vendor, vendor_nombre=VENDOR_META[vendor]['nombre'],
        vends=vends, vendor_meta=VENDOR_META, data=data, err=err,
        msg=request.args.get('msg'))


@competencia_v2_bp.route('/admin/competencia-v2/upload', methods=['POST'])
def competencia_v2_upload():
    """Sube los JSON (colchones/sommiers, todos los vendedores) de un período y
    dispara el reprocesamiento (borrando el cache de ese período)."""
    periodo = (request.form.get('periodo') or '').strip()
    if not re.match(r'^\d{4}-\d{2}$', periodo):
        return redirect(url_for('competencia_v2.competencia_v2_page', msg='Período inválido (usá formato AAAA-MM, ej. 2026-07)'))
    dest = os.path.join(DATA_DIR, periodo)
    os.makedirs(dest, exist_ok=True)
    guardados = []
    for campo, fname in [('colchones', 'colchones.json'), ('sommiers', 'sommiers.json'), ('almohadas', 'almohadas.json')]:
        f = request.files.get(campo)
        if not f or not f.filename:
            continue
        raw = f.read()
        try:
            data = json.loads(raw.decode('utf-8'))
            if not isinstance(data, list):
                raise ValueError('el JSON no es una lista de ventas')
        except Exception as e:
            return redirect(url_for('competencia_v2.competencia_v2_page', periodo=periodo,
                                    msg=f'{fname}: JSON inválido ({e})'))
        with open(os.path.join(dest, fname), 'wb') as out:
            out.write(raw)
        guardados.append(f'{fname} ({len(data)} filas)')
    # limpiar cache de ese período para que reprocese
    try:
        for old in os.listdir(DATA_DIR):
            if old.startswith(f'.cache_{periodo}_'):
                os.remove(os.path.join(DATA_DIR, old))
    except Exception:
        pass
    msg = ('✅ Subido y reprocesando: ' + ', '.join(guardados)) if guardados else '⚠️ No se seleccionó ningún archivo.'
    return redirect(url_for('competencia_v2.competencia_v2_page', periodo=periodo, msg=msg))


# ── Parte 2: ventas detalladas por competidor (día × producto × cuota) ──
MESES = {'January':'01','February':'02','March':'03','April':'04','May':'05','June':'06',
         'July':'07','August':'08','September':'09','October':'10','November':'11','December':'12'}
def _dia_sort(day):
    m = re.match(r'([A-Za-z]+)\s+(\d+),\s+(\d+)', str(day or ''))
    if not m: return str(day or '')
    return f"{m.group(3)}-{MESES.get(m.group(1),'00')}-{int(m.group(2)):02d}"
def _dia_corto(day):
    m = re.match(r'([A-Za-z]+)\s+(\d+),\s+(\d+)', str(day or ''))
    if not m: return str(day or '')
    return f"{int(m.group(2)):02d}/{MESES.get(m.group(1),'00')}"

def _ventas_detalle(periodo, vendor):
    data = _construir(periodo, vendor)   # cacheado; trae A con precios por sku×tramo
    L = {}
    for r in data.get('A', []):
        L[(r['sku'], r['tier'])] = (r.get('comp'), r.get('mio'), r.get('fu'))
    conn = _db(); mis = _cargar_mis_skus(conn); alm_precios = _precios_almohadas(conn); conn.close()
    meta = VENDOR_META[vendor]; alias = meta['alias']
    rows = []
    for fname, tipo in PERIODOS().get(periodo, []):   # incluye almohadas
        path = os.path.join(DATA_DIR, periodo, fname)
        if not os.path.exists(path): continue
        for r in json.load(open(path, encoding='utf-8')):
            if r.get('alias') != alias: continue
            q = int(r.get('sold_quantity') or 0)
            if q <= 0: continue
            title_full = r.get('title') or ''
            pvend = _price(r.get('price'))
            base = {'dia': _dia_corto(r.get('day')), 'dia_sort': _dia_sort(r.get('day')),
                    'title': title_full[:70], 'title_full': title_full,
                    'tipo': tipo, 'u': q, 'gmv': q * pvend, 'pvend': pvend}
            if tipo == 'almohada':
                # match por modelo; el competidor puede vender packs → comparo por unidad
                sku, pack = _match_almohada(title_full, mis)
                comp_u = (pvend / pack) if pack else pvend
                mio = alm_precios.get(sku) if sku else None
                d = ((mio / comp_u - 1) * 100) if (comp_u and mio) else None
                base.update({'model': r.get('model') or 'Almohada',
                    'medida': (f"pack x{pack}" if pack > 1 else 'unidad'),
                    'sku': sku or '—', 'tier': 'sin', 'tier_lbl': TIER_LBL['sin'],
                    'comp': comp_u, 'mio': mio, 'fu': ('catálogo' if mio else None), 'd': d,
                    'dtxt': (f"{d:+.0f}%" if d is not None else None),
                    'cls': (_dcls(d) if d is not None else '')})
                rows.append(base)
                continue
            sku, w = _match_sku(r, tipo, mis)
            tier = _inst_to_tier(r.get('installments')) or 'sin'
            comp, mio, fu = L.get((sku, tier), (None, None, None))
            d = ((mio/comp - 1) * 100) if (comp and mio) else None
            base.update({'model': r.get('model') or '', 'medida': (f"{w}cm" if w else '?'),
                'sku': sku or '—', 'tier': tier, 'tier_lbl': TIER_LBL.get(tier, '?'),
                'comp': comp, 'mio': mio, 'fu': fu, 'd': d,
                'dtxt': (f"{d:+.0f}%" if d is not None else None),
                'cls': (_dcls(d) if d is not None else '')})
            rows.append(base)
    rows.sort(key=lambda x: (x['dia_sort'], -x['u']))
    return rows, data


@competencia_v2_bp.route('/admin/ventas-competidores')
def ventas_competidores_page():
    pers = PERIODOS()
    pers_orden = sorted(pers.keys(), reverse=True)
    periodo = request.args.get('periodo') or (pers_orden[0] if pers_orden else '')
    if periodo not in pers:
        periodo = pers_orden[0] if pers_orden else ''
    vendor = request.args.get('vendedor') or VENDORS_VC[0]
    if vendor not in VENDORS_VC:
        vendor = VENDORS_VC[0]
    try:
        rows, data = _ventas_detalle(periodo, vendor) if periodo else ([], None)
        err = None
    except Exception as e:
        rows, data, err = [], None, str(e)
    dias = sorted(set(r['dia'] for r in rows), key=lambda x: x)
    modelos = sorted(set(r['model'] for r in rows if r['model']))
    medidas = sorted(set(r['medida'] for r in rows))
    return render_template('ventas_competidores.html',
        periodo=periodo, periodos=pers, periodo_lbl={p: _periodo_lbl(p) for p in pers},
        vendor=vendor, vendor_nombre=VENDOR_META[vendor]['nombre'],
        vends=VENDORS_VC, vendor_meta=VENDOR_META, rows=rows,
        dias=dias, modelos=modelos, medidas=medidas,
        total_u=sum(r['u'] for r in rows), total_gmv=sum(r['gmv'] for r in rows),
        snap=(data.get('snap') if data else ''), err=err)


# ── Parte 3: ranking de competidores por categoría y total (por mes) ──
ALIAS_YO = 'MERCADOMUEBLES (YO)'
def _vend_key(r):
    """(clave, etiqueta, nombrado) del vendedor: alias real si está cargado; si no
    ('-' o vacío), el nickname de ML (cada seller sin nombre = fila propia)."""
    al = (r.get('alias') or '').strip()
    if al and al != '-':
        return al, al, True
    nk = (r.get('nickname') or '').strip() or '(sin dato)'
    return nk, nk, False

def _ranking(periodo):
    """Suma unidades y GMV (u×precio) por vendedor, por categoría y total, del mes."""
    present = set(tp for fn, tp in FILE_TIPOS
                  if os.path.exists(os.path.join(DATA_DIR, periodo, fn)))
    vend = {}   # key -> {nombre, nombrado, yo, cat:{tipo:{u,gmv}}, u, gmv}
    for fname, tipo in FILE_TIPOS:
        path = os.path.join(DATA_DIR, periodo, fname)
        if not os.path.exists(path): continue
        try:
            data = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        for r in data:
            q = int(r.get('sold_quantity') or 0)
            if q <= 0: continue
            key, disp, nombrado = _vend_key(r)
            g = q * _price(r.get('price'))
            v = vend.get(key)
            if not v:
                v = vend[key] = {'nombre': disp, 'nombrado': nombrado, 'yo': False,
                                 'cat': {t: {'u': 0, 'gmv': 0.0} for t in CAT_ORDEN},
                                 'u': 0, 'gmv': 0.0}
            c = v['cat'][tipo]; c['u'] += q; c['gmv'] += g
            v['u'] += q; v['gmv'] += g
            if (r.get('alias') or '').strip() == ALIAS_YO: v['yo'] = True

    total = sorted(vend.values(), key=lambda x: -x['gmv'])
    gtot = sum(v['gmv'] for v in total) or 1
    for i, v in enumerate(total, 1):
        v['pos'] = i; v['share'] = 100 * v['gmv'] / gtot

    porcat = {}
    for t in CAT_ORDEN:
        filas = [{'nombre': v['nombre'], 'nombrado': v['nombrado'], 'yo': v['yo'],
                  'u': v['cat'][t]['u'], 'gmv': v['cat'][t]['gmv']}
                 for v in vend.values() if v['cat'][t]['u'] > 0]
        filas.sort(key=lambda x: -x['gmv'])
        gt = sum(f['gmv'] for f in filas) or 1
        for i, f in enumerate(filas, 1):
            f['pos'] = i; f['share'] = 100 * f['gmv'] / gt
        porcat[t] = {'lbl': CAT_LBL[t], 'filas': filas,
                     'u': sum(f['u'] for f in filas), 'gmv': sum(f['gmv'] for f in filas)}

    return {'periodo': periodo, 'total': total, 'gmv_tot': gtot,
            'u_tot': sum(v['u'] for v in total), 'n_vend': len(total),
            'porcat': porcat, 'cats_presentes': [t for t in CAT_ORDEN if t in present],
            'cat_lbl': CAT_LBL}


@competencia_v2_bp.route('/admin/competencia-v2/ranking')
def ranking_competidores_page():
    pers = PERIODOS()
    pers_orden = sorted(pers.keys(), reverse=True)
    periodo = request.args.get('periodo') or (pers_orden[0] if pers_orden else '')
    if periodo not in pers:
        periodo = pers_orden[0] if pers_orden else ''
    try:
        data = _ranking(periodo) if periodo else None
        err = None if periodo else 'No hay períodos cargados todavía.'
    except Exception as e:
        data, err = None, str(e)
    return render_template('ranking_competidores.html',
        periodo=periodo, periodos=pers, periodo_lbl={p: _periodo_lbl(p) for p in pers},
        data=data, err=err)
