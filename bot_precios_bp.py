import json, re, os
import requests
import mysql.connector
from flask import Blueprint, request, jsonify, render_template, session
from dotenv import load_dotenv
import anthropic

load_dotenv('config/.env')

bot_precios_bp = Blueprint('bot_precios', __name__)

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
    """True si el SKU necesita recargo por envío Flex"""
    s = sku.upper()
    if s.endswith('Z'):
        return False          # con Z: siempre sin recargo
    if s.startswith('S'):
        return True           # sommiers sin Z: siempre con recargo
    return _sku_width(sku) > 100  # colchones: solo si ancho > 100cm

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

def _calc_prices(sku, recargo_flex=0):
    # Strip Z para buscar en cannon_productos
    sku_buscar = sku[:-1] if sku.upper().endswith('Z') else sku
    es_sommier = sku_buscar.upper().startswith('S') and len(sku_buscar) > 1 and sku_buscar[1].isalpha()
    sku_col = ('C' + sku_buscar[1:]) if es_sommier else sku_buscar

    prod = _query("""
        SELECT cp.sku, cp.descripcion, clp.precio_lista,
               cd_adi.valor as desc_adicional,
               ce_col.costo as costo_colecta,
               ce_flex.costo as costo_flex
        FROM cannon_productos cp
        JOIN cannon_lista_precios clp ON clp.codigo_material = cp.codigo_material
        LEFT JOIN cannon_descuentos cd_adi ON cd_adi.clave = CONCAT('adicional_', cp.sku)
        LEFT JOIN cannon_costos_envio ce_col ON ce_col.sku = %s AND ce_col.tipo = 'colecta'
        LEFT JOIN cannon_costos_envio ce_flex ON ce_flex.sku = %s AND ce_flex.tipo = 'flex'
        WHERE cp.sku = %s
    """, (sku_buscar, sku_buscar, sku_col), fetchall=False)

    if not prod:
        return {"error": f"SKU {sku} no encontrado en la BD (buscado como {sku_col})"}

    descs = {r['clave']: {'valor': float(r['valor']), 'desc_adicional': float(r['desc_adicional'] or 0)}
             for r in _query("SELECT clave, valor, desc_adicional FROM cannon_descuentos WHERE tipo='descuento_linea'")}
    cfg_row = _query("SELECT clave, valor FROM cannon_descuentos", fetchall=True)
    cfg = {r['clave']: float(r['valor']) for r in cfg_row}

    mult        = cfg.get('multiplicador', 1.85)
    desc_cliente= cfg.get('cliente', 0.0)
    prontopago  = cfg.get('prontopago', 5.0)

    clave = _detectar_clave(prod['descripcion'], sku_col)
    entry = descs.get(clave, {'valor': 0, 'desc_adicional': 0}) if clave else {'valor': 0, 'desc_adicional': 0}
    desc_linea = entry['valor']
    desc_adi   = entry['desc_adicional'] + float(prod['desc_adicional'] or 0)

    precio_base = round(_precio_lista_formula(
        float(prod['precio_lista']), desc_linea, desc_cliente, desc_adi, prontopago, mult
    ) / 1000) * 1000

    # Sommiers: sumar base
    if es_sommier:
        cfg_conj = _query(
            "SELECT base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku=%s AND activo=1",
            (sku_col,), fetchall=False
        )
        if cfg_conj:
            base_sku = cfg_conj['base_sku_default']
            cant = int(cfg_conj['cantidad_bases'] or 1)
            cp_base = _query("""
                SELECT clp.precio_lista FROM cannon_productos cp
                JOIN cannon_lista_precios clp ON clp.codigo_material = cp.codigo_material
                WHERE cp.sku = %s
            """, (base_sku,), fetchall=False)
            if cp_base:
                desc_base = descs.get('bases', {'valor': 40})['valor']
                precio_base_calc = round(_precio_lista_formula(
                    float(cp_base['precio_lista']), desc_base, desc_cliente, 0, prontopago, mult
                ) / 1000) * 1000
                precio_base = round((precio_base + precio_base_calc * cant) / 1000) * 1000

    # Costo envío: usar recargo_flex del chat si se pasó, si no usar tabla
    es_z = sku.upper().endswith('Z')
    ancho = _sku_width(sku_buscar)
    if es_z or clave in ('bases', 'almohadas'):
        costo_envio = 0
    elif float(recargo_flex) > 0:
        costo_envio = float(recargo_flex)   # override por chat
    elif ancho <= 100:
        costo_envio = float(prod['costo_colecta'] or 0)
    else:
        costo_envio = float(prod['costo_flex'] or 0)

    precio_sc = round((precio_base + costo_envio) / 1000) * 1000

    pcts_row = _query("SELECT valor FROM configuracion WHERE clave='porcentajes_ml'", fetchall=False)
    pcts = json.loads(pcts_row['valor']) if pcts_row else {
        'cuota_simple': 5, 'cuotas_3': 8.8, 'cuotas_6': 13.3, 'cuotas_9': 18.9, 'cuotas_12': 21.3
    }

    def _pc(base, pct):
        return round(base * 0.76 / (0.76 - pct / 100) / 1000) * 1000

    return {
        "sku": sku,
        "descripcion": prod['descripcion'],
        "precio_lista_cannon": float(prod['precio_lista']),
        "modelo_key": clave,
        "desc_linea_pct": desc_linea,
        "costo_envio": costo_envio,
        "sin_cuotas":   precio_sc,
        "cuota_simple": _pc(precio_sc, pcts['cuota_simple']),
        "c3":           _pc(precio_sc, pcts['cuotas_3']),
        "c6":           _pc(precio_sc, pcts['cuotas_6']),
        "c9":           _pc(precio_sc, pcts['cuotas_9']),
        "c12":          _pc(precio_sc, pcts['cuotas_12']),
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
    """[{sku, recargo_flex}] → precios calculados por SKU"""
    return {"precios": [_calc_prices(i['sku'], i.get('recargo_flex', 0)) for i in skus_recargos]}

def tool_obtener_publis(skus):
    """Trae MLAs + datos de ML. Deduplica pares por item_relations."""
    resultado = {}
    for sku in skus:
        rows = _query("SELECT mla_id FROM sku_mla_mapeo WHERE sku=%s AND activo=1", (sku,))
        publis_raw = {}
        for row in rows:
            mla_id = row['mla_id']
            data = _ml_get(mla_id)
            if not data:
                publis_raw[mla_id] = None
                continue
            titulo = data.get('title', '')
            try:
                db = _db(); cur = db.cursor()
                cur.execute("UPDATE sku_mla_mapeo SET titulo_ml=%s WHERE mla_id=%s", (titulo, mla_id))
                db.commit(); cur.close(); db.close()
            except Exception:
                pass
            publis_raw[mla_id] = {
                'mla_id':          mla_id,
                'titulo':          titulo,
                'precio_actual':   data.get('price'),
                'status':          data.get('status', 'unknown'),
                'listing_type':    _listing_type_from_ml(data),
                'catalog_listing': data.get('catalog_listing', False),
                'item_relations':  [r['id'] for r in data.get('item_relations', [])],
                'tiene_almohada':  'almohada' in titulo.lower(),
                'skip':            False,
            }

        # Deduplicar pares A<->B
        # Regla: catálogo activa > catálogo pausada (usar la otra) > activa > cualquiera
        procesados = set()
        for mla_id, pub in publis_raw.items():
            if pub is None or mla_id in procesados:
                continue
            for rel_id in pub.get('item_relations', []):
                if rel_id not in publis_raw or publis_raw[rel_id] is None:
                    continue
                rel = publis_raw[rel_id]
                procesados.update([mla_id, rel_id])
                a_act = pub['status'] == 'active'
                b_act = rel['status'] == 'active'
                a_cat = pub['catalog_listing']
                b_cat = rel['catalog_listing']
                if a_cat and a_act:
                    rel['skip'] = True
                elif b_cat and b_act:
                    pub['skip'] = True
                elif a_cat and not a_act and b_act:
                    pub['skip'] = True
                elif b_cat and not b_act and a_act:
                    rel['skip'] = True
                elif a_act and not b_act:
                    rel['skip'] = True
                elif b_act and not a_act:
                    pub['skip'] = True

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

def tool_actualizar(cambios):
    """[{mla_id, sku, precio_nuevo, precio_anterior}] → actualiza en ML"""
    resultados = []
    for c in cambios:
        ok, code = _ml_put_price(c['mla_id'], c['precio_nuevo'])
        resultados.append({
            'mla_id':         c['mla_id'],
            'sku':            c.get('sku', ''),
            'precio_nuevo':   int(c['precio_nuevo']),
            'precio_anterior': c.get('precio_anterior'),
            'ok':             ok,
            'http_status':    code,
        })
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
            "Calcula los precios ML para una lista de SKUs con sus recargos Flex. "
            "Aplica la fórmula completa: "
            "precio_lista × 1.85 × (1−desc_linea%) × (1−desc_adicional%) × 0.90 ÷ 1.05 + recargo_flex = base. "
            "Luego para cuotas: round(0.76/(0.76−pct/100) × base / 1000) × 1000. "
            "Devuelve sin_cuotas, cuota_simple, c3, c6, c9, c12."
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
                                            "description": "Recargo en pesos por Flex. 0 si no aplica."}
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
2. SKU sin Z, colchón (empieza con C), ancho ≤ 100cm → sin recargo (Colecta lo cubre)
3. SKU sin Z, colchón (empieza con C), ancho > 100cm → recargo Flex (Manu lo indica)
4. SKU sin Z, sommier (empieza con S) → SIEMPRE recargo Flex (Manu lo indica)
5. Título de ML contiene "almohada" → recargo adicional (funcionalidad pendiente, avisá si aparece)
El ancho está en el SKU: CDOP140 → 140cm, CDOP80 → 80cm, CTR90 → 90cm

═══ IMPORTANTE SOBRE SKUs CON Z ═══
- Los SKUs con Z (ej: CDOP160Z, SDOP140Z) NO existen en cannon_productos — esa tabla solo tiene la versión sin Z
- Pero SÍ existen en sku_mla_mapeo (sus publicaciones están ahí)
- NUNCA busques un SKU con Z en cannon_productos — te va a dar error
- Para calcular precios de un SKU con Z, pasalo directamente a calcular_precios — la función internamente stripea la Z y busca el base
- Para buscar publicaciones de un SKU con Z, usá obtener_publicaciones — también lo maneja solo
- Si Manu pide "CDOP160Z", no busques en cannon_productos, andá directo a calcular_precios y obtener_publicaciones

═══ FÓRMULA ═══
base = precio_lista × mult × (1−desc_linea%) × (1−desc_adicional%) × 0.90 ÷ 1.05 + recargo_flex
→ redondeado a miles
precio con cuotas = round(0.76/(0.76−pct/100) × base / 1000) × 1000

═══ FLUJO OBLIGATORIO ═══
1. Buscar SKUs con sql_select
2. Identificar cuáles necesitan recargo Flex → si no te los dieron, PREGUNTAR antes de continuar
3. calcular_precios con los recargos correctos
4. obtener_publicaciones para saber MLAs, precios actuales y tipos de cuota
5. Mostrar tabla de preview SOLO con publis donde skip=False. Las que tienen skip=True son secundarias sincronizadas automáticamente por ML — NO incluirlas en el preview ni en los CAMBIOS.
   Columnas: SKU | MLA | Título | Cuotas | Precio actual | Precio nuevo | Δ
   Si hay publis skipeadas, indicar al final cuántas se omitieron y por qué (ej: "3 publis omitidas — se sincronizan automáticamente con su par de catálogo").
6. Al final del mensaje de preview, incluir EXACTAMENTE este marcador (sin espacios extra):
   <!--CAMBIOS:[{"mla_id":"MLA...","sku":"...","precio_nuevo":000000,"precio_anterior":000000,"titulo":"...","listing_type":"..."}]-->
7. ESPERAR confirmación explícita del usuario
8. Solo entonces llamar actualizar_precios

═══ IMPORTANTE ═══
- NUNCA llamar actualizar_precios sin confirmación explícita
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
            system=SYSTEM,
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
