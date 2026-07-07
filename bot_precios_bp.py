import json, re, os
import requests
import mysql.connector
from concurrent.futures import ThreadPoolExecutor, as_completed

def _crear_tabla_bot_log():
    db = _db(); cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_precios_log (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            fecha        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sku          VARCHAR(50),
            mla_id       VARCHAR(20),
            titulo       VARCHAR(255),
            listing_type VARCHAR(50),
            precio_anterior INT,
            precio_nuevo    INT,
            ok           TINYINT(1) DEFAULT 1,
            usuario      VARCHAR(50) DEFAULT 'bot_precios'
        )
    """)
    db.commit(); cur.close(); db.close()
from flask import Blueprint, request, jsonify, render_template, session
from dotenv import load_dotenv
import anthropic

load_dotenv('config/.env')

bot_precios_bp = Blueprint('bot_precios', __name__)

# Crear tabla de log al importar el blueprint
try:
    _crear_tabla_bot_log()
except Exception:
    pass  # Si falla (ej: BD no disponible aún), no bloquear el arranque

# ── DB ────────────────────────────────────────────────────────────

def _db():
    return mysql.connector.connect(
        host='localhost', user='cannon',
        password=os.getenv('DB_PASSWORD', 'Sistema@32267845'),
        database='inventario_cannon'
    )

def _query(sql, params=None, fetchall=True):
    db = _db()
    cur = db.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall() if fetchall else cur.fetchone()
    cur.close(); db.close()
    return rows

def _to_float(obj):
    """Recursively convert Decimal/bytes to JSON-serializable types"""
    if isinstance(obj, dict):
        return {k: _to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_float(v) for v in obj]
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode('utf-8', errors='replace')
    try:
        if hasattr(obj, '__float__') and not isinstance(obj, (int, float, bool)):
            return float(obj)
    except Exception:
        pass
    return obj

# ── ML TOKEN ──────────────────────────────────────────────────────

def _ml_token():
    row = _query("SELECT valor FROM configuracion WHERE clave='ml_token'", fetchall=False)
    if row:
        return json.loads(row['valor'])['access_token']
    return None

def _ml_get(mla_id):
    token = _ml_token()
    try:
        r = requests.get(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=8
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def _ml_put_price(mla_id, precio):
    token = _ml_token()
    try:
        r = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'price': int(precio)},
            timeout=10
        )
        return r.status_code == 200, r.status_code
    except Exception as e:
        return False, str(e)

# ── SKU HELPERS ───────────────────────────────────────────────────

_MODEL_MAP = [
    ('CDOPEP', 'doral_pillow'), ('CDOP', 'doral_pillow'),
    ('CDORAL', 'doral'),        ('CDO', 'doral'),
    ('CSUBEP', 'sublime_europillow'), ('CSUB', 'sublime'),
    ('CEXPIL', 'exclusive_pillow'),   ('CEXP', 'exclusive_pillow'), ('CEX', 'exclusive'),
    ('CREP',   'renovation_europillow'), ('CRE', 'renovation'),
    ('CPR',    'princess_20'),
    ('CPLA',   'platino'),
    ('CSON',   'sonar'),
    ('CTR',    'tropical'),
    ('SDOP',   'doral_pillow'), ('SSUB', 'sublime'),
    ('SSUPEP', 'sublime_europillow'),
    ('SREP',   'renovation_europillow'), ('SRE', 'renovation'),
    ('SEX',    'exclusive'),
    ('BASE',   'bases'),
]

def _model_key(sku):
    s = sku.upper().rstrip('Z')
    for prefix, key in _MODEL_MAP:
        if s.startswith(prefix):
            return key
    return None

def _sku_width(sku):
    """Extrae el ancho en cm del SKU. CDOP140 → 140, CTR80 → 80"""
    s = sku.upper().rstrip('Z')
    for prefix, _ in _MODEL_MAP:
        if s.startswith(prefix):
            rest = s[len(prefix):]
            nums = re.findall(r'\d+', rest)
            if nums:
                return int(nums[0])
    return 0

def _needs_flex(sku):
    """True si el SKU lleva recargo Flex. Colecta dado de baja: todo colchón o
    sommier sin Z lleva flex (cualquier ancho), salvo Compac (CCO80/100/140/160)."""
    s = sku.upper()
    if s.endswith('Z'):
        return False          # con Z: siempre sin recargo
    if s in ('CCO80', 'CCO100', 'CCO140', 'CCO160'):
        return False          # Compac: sin flex
    return s.startswith('C') or s.startswith('S')  # colchones y sommiers

CAMPAÑAS_CUOTAS = {
    'pcj-co-funded': 'Cuota Simple',
    '3x_campaign':   '3 cuotas s/interés',
    '6x_campaign':   '6 cuotas s/interés',
    '9x_campaign':   '9 cuotas s/interés',
    '12x_campaign':  '12 cuotas s/interés',
}

def _listing_type_from_ml(ml_data):
    """Detecta el tipo de cuotas — lógica exacta de app.py obtener_datos_ml"""
    campaign = None
    for term in ml_data.get('sale_terms', []):
        if term.get('id') == 'INSTALLMENTS_CAMPAIGN':
            campaign = (term.get('value_name') or '').split('|')[0].strip()

    listing_type_id = ml_data.get('listing_type_id', '')
    if listing_type_id == 'gold_special':
        return CAMPAÑAS_CUOTAS.get(campaign, 'Sin cuotas propias') if campaign else 'Sin cuotas propias'
    elif listing_type_id == 'gold_pro':
        return CAMPAÑAS_CUOTAS.get(campaign, '6 cuotas s/interés')
    else:
        return listing_type_id or 'Sin cuotas propias'

_LT_TO_FIELD = {
    'Sin cuotas propias':   'sin_cuotas',
    'Cuota Simple':         'cuota_simple',
    '3 cuotas s/interés':   'c3',
    '6 cuotas s/interés':   'c6',
    '9 cuotas s/interés':   'c9',
    '12 cuotas s/interés':  'c12',
}

# ── PRICE CALCULATION ─────────────────────────────────────────────

def _detectar_clave(descripcion, sku_col):
    """Detecta la clave de descuento desde la descripción — igual que app.py"""
    desc = (descripcion or '').upper()
    sku_up = sku_col.upper()
    if sku_up in ('CLASICA','SUBLIME','CERVICAL','RENOVATION','PLATINO','DORAL','DUAL','EXCLUSIVE'):
        return 'almohadas'
    if desc.startswith('ALM'): return 'almohadas'
    if 'EUROPILLOW' in desc:
        if 'SUBLIME' in desc: return 'sublime_europillow'
        if 'RENOVATION' in desc: return 'renovation_europillow'
    if 'PILLOW' in desc or 'PIL' in desc:
        if 'EXCLUSIVE' in desc: return 'exclusive_pillow'
        if 'DORAL' in desc: return 'doral_pillow'
    if 'PRINCESS' in desc: return 'princess_23' if '23' in desc else 'princess_20'
    if 'ESPECIAL DE LUJO' in desc: return 'especial_de_lujo'
    if 'EXCLUSIVE' in desc: return 'exclusive'
    if 'RENOVATION' in desc: return 'renovation'
    if 'TROPICAL' in desc: return 'tropical'
    if 'SONAR' in desc or 'SOÑAR' in desc: return 'sonar'
    if 'PLATINO' in desc: return 'platino'
    if 'DORAL' in desc: return 'doral'
    if 'SUBLIME' in desc: return 'sublime'
    if 'BASE' in desc or sku_up.startswith('BASE_') or desc.startswith('SOM '): return 'bases'
    return None

def _precio_lista_formula(precio_cannon, desc_linea, desc_cliente, desc_adi, prontopago, mult):
    """Fórmula exacta de app.py _calcular_precio_lista"""
    c = precio_cannon
    c *= (1 - desc_linea / 100)
    if desc_cliente: c *= (1 - desc_cliente / 100)
    if desc_adi:     c *= (1 - desc_adi / 100)
    c *= 1 / (1 + prontopago / 100)
    return round(c * mult)

def _calc_prices(sku, recargo_flex=0, recargo_almohada_unit=0):
    """Wrapper sobre la función canónica de app.py (_get_precio_costos_sku) para
    que el Bot de Precios calcule EXACTAMENTE igual que 'cargar stock ML'
    (mismos parámetros, casos especiales CTR80/Compac/Almohadas y neteo de envío).
    Import lazy para evitar el import circular (app importa este blueprint)."""
    from app import _get_precio_costos_sku
    r = _get_precio_costos_sku(sku, recargo_flex=recargo_flex, recargo_almohada_unit=recargo_almohada_unit)
    if not r:
        return {"error": f"SKU {sku} no encontrado en la BD"}
    d = r.get('desglose', {}) or {}
    return {
        "sku": sku,
        "descripcion": d.get('descripcion'),
        "precio_lista_cannon": d.get('precio_cannon'),
        "modelo_key": d.get('clave'),
        "desc_linea_pct": d.get('desc_linea_pct'),
        "costo_envio": d.get('costo_envio'),
        "costo_almohadas": d.get('costo_almohadas'),
        "cant_almohadas": d.get('cant_almohadas'),
        "sin_cuotas":   r['precio_sin_cuotas'],
        "cuota_simple": r['precio_1c'],
        "c3":           r['precio_3c'],
        "c6":           r['precio_6c'],
        "c9":           r['precio_9c'],
        "c12":          r['precio_12c'],
        "desglose":     d,
    }

# ── TOOLS ─────────────────────────────────────────────────────────

def tool_sql(query):
    q = query.strip()
    if not q.upper().startswith('SELECT'):
        return {"error": "Solo consultas SELECT están permitidas"}
    db = _db(); cur = db.cursor(dictionary=True)
    try:
        cur.execute(q)
        rows = _to_float(cur.fetchall())
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close(); db.close()

def tool_calcular(skus_recargos):
    """[{sku, recargo_flex, recargo_almohada_unit}] → precios calculados por SKU"""
    return {"precios": [_calc_prices(
        i['sku'],
        i.get('recargo_flex', 0),
        i.get('recargo_almohada_unit', 0)
    ) for i in skus_recargos]}

def _buscar_mlas_por_sku(sku):
    """Devuelve las MLA ids de un seller_sku desde sku_mla_mapeo (tabla local
    recargada desde el export de ML). Antes consultaba la API en vivo, pero ML
    restringió /users/{id}/items/search (403). La forma vieja por API quedó
    comentada abajo para volver atrás si ML re-habilita el endpoint."""
    try:
        db = _db(); cur = db.cursor()
        cur.execute("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=TRUE", (sku,))
        rows = cur.fetchall()
        cur.close(); db.close()
        return [(r['mla_id'] if isinstance(r, dict) else r[0]) for r in rows]
    except Exception:
        return []
    # ── Forma vieja: búsqueda en vivo por API (ML la restringió → 403) ──────
    # from app import ML_SELLER_ID   # import lazy: evita import circular
    # token = _ml_token()
    # if not token:
    #     return []
    # try:
    #     r = requests.get(
    #         f'https://api.mercadolibre.com/users/{ML_SELLER_ID}/items/search',
    #         headers={'Authorization': f'Bearer {token}'},
    #         params={'seller_sku': sku},
    #         timeout=10
    #     )
    #     return r.json().get('results', []) if r.status_code == 200 else []
    # except Exception:
    #     return []

def _fetch_mla(mla_id):
    """Fetch un MLA de ML y devuelve dict procesado. Thread-safe."""
    data = _ml_get(mla_id)
    if not data:
        return mla_id, None
    titulo = data.get('title', '')
    try:
        db = _db(); cur = db.cursor()
        cur.execute("UPDATE sku_mla_mapeo SET titulo_ml=%s WHERE mla_id=%s", (titulo, mla_id))
        db.commit(); cur.close(); db.close()
    except Exception:
        pass
    sub_status = data.get('sub_status') or []
    return mla_id, {
        'mla_id':          mla_id,
        'titulo':          titulo,
        'precio_actual':   data.get('price'),
        'stock':           data.get('available_quantity'),
        'status':          data.get('status', 'unknown'),
        'sub_status':      sub_status if isinstance(sub_status, list) else [sub_status],
        'listing_type':    _listing_type_from_ml(data),
        'catalog_listing': data.get('catalog_listing', False),
        'item_relations':  [r['id'] for r in data.get('item_relations', [])],
        'tiene_almohada':  'almohada' in titulo.lower(),
        'skip':            False,
    }

def tool_obtener_publis(skus):
    """Trae MLAs + datos de ML en paralelo. Deduplica pares por item_relations."""
    resultado = {}
    for sku in skus:
        mla_ids = _buscar_mlas_por_sku(sku)

        # Consultas en paralelo — 10 threads simultáneos
        publis_raw = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_fetch_mla, mla_id): mla_id for mla_id in mla_ids}
            for future in as_completed(futures):
                mla_id, pub = future.result()
                publis_raw[mla_id] = pub

        # Dedup de publis linkeadas: ML sincroniza precio y stock entre la publi de
        # catálogo y su espejo. Si hay 2+ con igual (stock, precio), actualizar solo
        # la de Catálogo (skip al resto) para no tocar dos veces el mismo precio.
        grupos = {}
        for mla_id, pub in publis_raw.items():
            if pub is None:
                continue
            grupos.setdefault((pub.get('stock'), pub.get('precio_actual')), []).append(pub)
        for grupo in grupos.values():
            if len(grupo) < 2:
                continue
            catalogo = [p for p in grupo if p.get('catalog_listing')]
            if not catalogo:
                continue   # ninguna de catálogo → no deduplicar (no arriesgar)
            mantener = catalogo[0]
            for p in grupo:
                if p is not mantener:
                    p['skip'] = True

        publis = []
        for mla_id, pub in publis_raw.items():
            if pub is None:
                publis.append({'mla_id': mla_id, 'titulo': None, 'precio_actual': None,
                               'status': 'error', 'listing_type': None,
                               'tiene_almohada': False, 'skip': False})
            else:
                publis.append(pub)
        resultado[sku] = publis
    return {"publicaciones": resultado}

def _log_cambio(sku, mla_id, titulo, listing_type, precio_anterior, precio_nuevo, ok):
    """Guarda en bot_precios_log Y sistema_logs en paralelo."""
    def _write_bot_log():
        try:
            db = _db(); cur = db.cursor()
            cur.execute("""
                INSERT INTO bot_precios_log
                    (sku, mla_id, titulo, listing_type, precio_anterior, precio_nuevo, ok)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (sku, mla_id, titulo, listing_type, precio_anterior, precio_nuevo, 1 if ok else 0))
            db.commit(); cur.close(); db.close()
        except Exception as e:
            print(f"[bot_log] Error bot_precios_log: {e}")

    def _write_sistema_log():
        try:
            db = _db(); cur = db.cursor()
            estado = "OK" if ok else "ERROR"
            desc = (f"{estado} | SKU:{sku} MLA:{mla_id} "
                    f"${precio_anterior:,}→${precio_nuevo:,} ({listing_type})")
            cur.execute("""
                INSERT INTO sistema_logs (nivel, modulo, accion, descripcion, usuario)
                VALUES ('INFO','bot_precios','actualizar_precio',%s,'bot_precios')
            """, (desc,))
            db.commit(); cur.close(); db.close()
        except Exception as e:
            print(f"[bot_log] Error sistema_logs: {e}")

    with ThreadPoolExecutor(max_workers=2) as ex:
        ex.submit(_write_bot_log)
        ex.submit(_write_sistema_log)

def tool_actualizar(cambios):
    """[{mla_id, sku, precio_nuevo, precio_anterior}] → actualiza en ML y loguea"""
    resultados = []
    for c in cambios:
        ok, code = _ml_put_price(c['mla_id'], c['precio_nuevo'])
        resultados.append({
            'mla_id':          c['mla_id'],
            'sku':             c.get('sku', ''),
            'precio_nuevo':    int(c['precio_nuevo']),
            'precio_anterior': c.get('precio_anterior'),
            'ok':              ok,
            'http_status':     code,
        })
        # Log en ambas tablas en paralelo
        _log_cambio(
            sku=c.get('sku',''),
            mla_id=c['mla_id'],
            titulo=c.get('titulo',''),
            listing_type=c.get('listing_type',''),
            precio_anterior=int(c.get('precio_anterior') or 0),
            precio_nuevo=int(c['precio_nuevo']),
            ok=ok
        )
    ok_n = sum(1 for r in resultados if r['ok'])
    return {"resultados": resultados, "ok": ok_n, "total": len(resultados)}

def _run_tool(name, inp):
    if name == 'sql_select':          return tool_sql(inp['query'])
    if name == 'calcular_precios':    return tool_calcular(inp['skus_recargos'])
    if name == 'obtener_publicaciones': return tool_obtener_publis(inp['skus'])
    if name == 'actualizar_precios':  return tool_actualizar(inp['cambios'])
    return {"error": f"Tool desconocida: {name}"}

# ── ANTHROPIC TOOLS SCHEMA ────────────────────────────────────────

TOOLS = [
    {
        "name": "sql_select",
        "description": (
            "Ejecuta una consulta SELECT de solo lectura en la base de datos MySQL. "
            "Tablas principales: "
            "cannon_productos(sku, descripcion, codigo_material, activo), "
            "cannon_lista_precios(codigo_material, precio_lista), "
            "cannon_descuentos(clave, valor, desc_adicional, tipo) — contiene multiplicador(1.85), "
            "cliente(10%), prontopago(5%) y por modelo (doral_pillow→30%), "
            "sku_mla_mapeo(sku, mla_id, titulo_ml, activo), "
            "configuracion(clave, valor) — clave='porcentajes_ml' tiene JSON con cuotas ML."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta SQL SELECT válida"}},
            "required": ["query"]
        }
    },
    {
        "name": "calcular_precios",
        "description": (
            "Calcula los precios ML para una lista de SKUs con sus recargos. "
            "Fórmula: precio_lista × mult × (1−desc%) × (1−dc%) ÷ (1+pp%) + recargo_flex + recargo_almohadas = base. "
            "recargo_almohadas = recargo_almohada_unit × (1 si ancho≤100, 2 si ancho>100). "
            "Luego para cuotas: round(0.76/(0.76−pct/100) × base / 1000) × 1000. "
            "Devuelve sin_cuotas, cuota_simple, c3, c6, c9, c12, costo_almohadas, cant_almohadas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "skus_recargos": {
                    "type": "array",
                    "description": "Lista de SKUs con sus recargos",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string"},
                            "recargo_flex": {"type": "number",
                                            "description": "Recargo en pesos por Flex. 0 si no aplica."},
                            "recargo_almohada_unit": {"type": "number",
                                            "description": "Precio por unidad de almohada en pesos. 0 si no aplica. El sistema multiplica por 1 o 2 según el ancho del SKU."}
                        },
                        "required": ["sku", "recargo_flex"]
                    }
                }
            },
            "required": ["skus_recargos"]
        }
    },
    {
        "name": "obtener_publicaciones",
        "description": (
            "Obtiene las publicaciones activas de ML para una lista de SKUs, "
            "consultando la API de MercadoLibre en tiempo real. "
            "Devuelve mla_id, titulo, precio_actual, listing_type, status, tiene_almohada."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "skus": {"type": "array", "items": {"type": "string"},
                         "description": "Lista de SKUs a consultar"}
            },
            "required": ["skus"]
        }
    },
    {
        "name": "actualizar_precios",
        "description": (
            "⚠️ ACCIÓN IRREVERSIBLE. Actualiza precios en MercadoLibre vía API. "
            "SOLO llamar DESPUÉS de confirmación explícita del usuario ('sí', 'dale', 'confirmar'). "
            "Nunca llamar sin confirmación."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cambios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "mla_id":          {"type": "string"},
                            "sku":             {"type": "string"},
                            "precio_nuevo":    {"type": "number"},
                            "precio_anterior": {"type": "number"}
                        },
                        "required": ["mla_id", "precio_nuevo"]
                    }
                }
            },
            "required": ["cambios"]
        }
    }
]

SYSTEM = """Sos el Bot de Precios ML de Mercadomuebles. Tu función es ayudar a Manu a actualizar precios en MercadoLibre de forma rápida, correcta y segura.

═══ REGLAS DE NEGOCIO ═══
1. SKU termina en Z → sin recargo de envío (entra por stock de depósito)
2. Colecta está DADO DE BAJA: ya NO existe la excepción de "ancho ≤ 100cm sin recargo".
3. Todo colchón (empieza con C) o sommier (empieza con S), SIN Z y que NO sea Compac → lleva recargo Flex SIN IMPORTAR el ancho (mismo criterio que un colchón de 140 o más grande). Cuando Manu indica un monto de flex, aplicalo a TODOS esos SKUs (colchones y sommiers), no solo a los sommiers.
4. Compac (CCO80, CCO100, CCO140, CCO160) → SIN recargo Flex.
5. Publis con "almohada" en el título → recargo SOLO para esas publis, no para todas las del SKU:
   - SKU con ancho ≤ 100cm → 1 almohada → recargo = recargo_almohada_unit × 1
   - SKU con ancho > 100cm → 2 almohadas → recargo = recargo_almohada_unit × 2
   - Si Manu no indicó precio por almohada, PREGUNTAR antes de calcular esas publis
   - El recargo_almohada_unit se pasa igual que el flex: "almohadas a 15mil cada una" → recargo_almohada_unit=15000
   - IMPORTANTE: un mismo SKU puede tener publis con y sin almohadas. Llamar calcular_precios DOS VECES:
     * Una vez con recargo_almohada_unit=0 → para publis sin almohada (tiene_almohada=False)
     * Una vez con recargo_almohada_unit=X → para publis con almohada (tiene_almohada=True)
     Luego asignar el precio correcto a cada MLA según su tiene_almohada.
El ancho está en el SKU: CDOP140 → 140cm, CDOP80 → 80cm, CTR90 → 90cm

═══ IMPORTANTE SOBRE SKUs CON Z ═══
- Los SKUs con Z (ej: CDOP160Z, SDOP140Z) NO existen en cannon_productos — esa tabla solo tiene la versión sin Z
- Pero SÍ existen en sku_mla_mapeo (sus publicaciones están ahí)
- NUNCA busques un SKU con Z en cannon_productos — te va a dar error
- Para calcular precios de un SKU con Z, pasalo directamente a calcular_precios — la función internamente stripea la Z y busca el base
- Para buscar publicaciones de un SKU con Z, usá obtener_publicaciones — también lo maneja solo
- Si Manu pide "CDOP160Z", no busques en cannon_productos, andá directo a calcular_precios y obtener_publicaciones

═══ PRECIOS — REGLA DE ORO ═══
NUNCA calcules un precio a mano ni inventes factores (multiplicador, pronto pago, descuentos, recargos). Los precios SIEMPRE salen de la tool calcular_precios, que usa la MISMA fórmula y la MISMA config en vivo que "cargar stock ML".
- Para explicar el cálculo, usá EXACTAMENTE los valores del objeto "desglose" que devuelve calcular_precios: precio_cannon, multiplicador, prontopago_pct, desc_cliente_pct, desc_linea_pct, desc_adicional_pct, costo_envio. Si un factor no viene en el desglose, NO lo menciones ni lo inventes (no asumas 1.85, 5%, etc.).
- Sommiers (SKU empieza con S): el precio = colchón base + (precio de la base × cantidad_bases). Eso ya lo calcula la tool y lo reporta en desglose.sommier (base_sku, cantidad_bases, precio_base_unit). NO inventes ningún factor (NO existe ningún "×1.44") ni asumas que el sommier cuesta lo mismo que el colchón.
- Cuotas: mostrá SIEMPRE todas las que devuelve la tool: sin cuotas, 1 cuota (cuota simple), 3, 6, 9 y 12 cuotas. No omitas ninguna.

═══ FLUJO OBLIGATORIO ═══
1. Buscar SKUs con sql_select
2. Identificar cuáles necesitan recargo Flex → si no te los dieron, PREGUNTAR antes de continuar
3. calcular_precios con los recargos correctos
4. obtener_publicaciones para saber MLAs, precios actuales y tipos de cuota
5. Mostrar tabla de preview SOLO con publis donde skip=False. Las que tienen skip=True son secundarias sincronizadas automáticamente por ML — NO incluirlas en el preview ni en los CAMBIOS.
   Columnas: SKU | MLA | Título | Cuotas | Precio actual | Precio nuevo | Δ
   En Δ mostrá el cambio absoluto Y el porcentaje, con signo. Ej: "+$30.000 (+13,3%)" o "-$12.000 (-5,2%)". El % = (precio_nuevo − precio_actual) / precio_actual × 100, redondeado a 1 decimal.
   Si hay publis skipeadas, indicar al final cuántas se omitieron y por qué (ej: "3 publis omitidas — se sincronizan automáticamente con su par de catálogo").
6. Al final del mensaje de preview, incluir EXACTAMENTE este marcador (sin espacios extra):
   <!--CAMBIOS:[{"mla_id":"MLA...","sku":"...","precio_nuevo":000000,"precio_anterior":000000}]-->
   Incluir SOLO mla_id, sku, precio_nuevo y precio_anterior — sin titulo ni listing_type para mantener el marcador corto.
7. ESPERAR confirmación explícita del usuario
8. Solo entonces llamar actualizar_precios

═══ IMPORTANTE ═══
- NUNCA llamar actualizar_precios sin confirmación explícita
- Para consultas de historial (ej: "qué modifiqué hoy", "dame los cambios de ayer"):
  usar sql_select sobre bot_precios_log (columnas: fecha, sku, mla_id, titulo, listing_type, precio_anterior, precio_nuevo, ok)
  Ejemplo: SELECT * FROM bot_precios_log WHERE DATE(fecha)=CURDATE() ORDER BY fecha DESC
- Si los datos de recargo no están claros, preguntar
- Redondear siempre a miles de pesos
- Responder en español rioplatense, tono directo y claro
- Si hay muchas publicaciones (>20), indicar que puede tardar unos segundos"""

# ── SERIALIZACIÓN DE BLOQUES ANTHROPIC ───────────────────────────

def _blocks_to_dicts(blocks):
    """Convierte ContentBlocks del SDK a dicts JSON-serializables"""
    result = []
    for b in blocks:
        if b.type == 'text':
            result.append({"type": "text", "text": b.text})
        elif b.type == 'tool_use':
            result.append({"type": "tool_use", "id": b.id,
                           "name": b.name, "input": b.input})
    return result

# ── ROUTES ────────────────────────────────────────────────────────

@bot_precios_bp.route('/admin/bot-precios')
def bot_precios_page():
    return render_template('bot_precios.html')

@bot_precios_bp.route('/admin/bot-precios/chat', methods=['POST'])
def bot_precios_chat():
    body = request.get_json()
    messages = body.get('messages', [])

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    for _ in range(15):
        resp = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=4096,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages
        )

        messages.append({"role": "assistant", "content": _blocks_to_dicts(resp.content)})

        if resp.stop_reason == 'end_turn':
            text = next((b.text for b in resp.content if hasattr(b, 'text')), '')
            return jsonify({"text": text, "messages": messages})

        if resp.stop_reason == 'tool_use':
            results = []
            for b in resp.content:
                if b.type == 'tool_use':
                    out = _run_tool(b.name, b.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": b.id,
                        "content": json.dumps(_to_float(out), ensure_ascii=False, default=str)
                    })
            messages.append({"role": "user", "content": results})

    return jsonify({"text": "Se agotó el límite de iteraciones. Intentá simplificar la consulta.", "messages": messages})

@bot_precios_bp.route('/admin/bot-precios/confirmar', methods=['POST'])
def bot_precios_confirmar():
    """Endpoint directo para ejecutar cambios confirmados (sin pasar por Claude)"""
    body = request.get_json()
    cambios = body.get('cambios', [])
    if not cambios:
        return jsonify({"error": "No hay cambios"}), 400
    result = tool_actualizar(cambios)
    return jsonify(result)
