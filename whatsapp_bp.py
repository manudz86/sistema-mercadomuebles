import os, json, time, re, threading
from datetime import datetime
import requests
import mysql.connector
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv('config/.env')

whatsapp_bp = Blueprint('whatsapp', __name__)

# ── Config ────────────────────────────────────────────────────────
WA_TOKEN      = os.getenv('WA_ACCESS_TOKEN')
WA_PHONE_ID   = os.getenv('WA_PHONE_NUMBER_ID')
WA_VERIFY_TOKEN = os.getenv('WA_VERIFY_TOKEN', 'mercadomuebles2025')
NUMERO_DERIVAR = '+5491126275185'
ANTHROPIC_KEY  = os.getenv('ANTHROPIC_API_KEY')

anthropic = Anthropic(api_key=ANTHROPIC_KEY)

# Conversaciones en memoria: {phone: [{"role": ..., "content": ...}]}
conversaciones = {}
# Lock por número para evitar respuestas duplicadas
processing = {}

# ── DB ────────────────────────────────────────────────────────────
def _db():
    return mysql.connector.connect(
        host='localhost', user='cannon',
        password=os.getenv('DB_PASSWORD', 'Sistema@32267845'),
        database='inventario_cannon'
    )

def _q(sql, params=None):
    db = _db(); cur = db.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close(); db.close()

def _exec(sql, params=None):
    db = _db(); cur = db.cursor()
    try:
        cur.execute(sql, params or ())
        db.commit()
    finally:
        cur.close(); db.close()

def _crear_tablas():
    db = _db(); cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wa_mensajes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            fecha       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            phone       VARCHAR(30),
            rol         ENUM('user','assistant'),
            contenido   TEXT,
            derivado    TINYINT(1) DEFAULT 0,
            INDEX idx_phone_fecha (phone, fecha)
        )
    """)
    db.commit(); cur.close(); db.close()

try:
    _crear_tablas()
except Exception as e:
    print(f"[WA] Error creando tablas: {e}")

# ── Zipnova ───────────────────────────────────────────────────────
ZIPNOVA_BASE_URL   = 'https://api.zipnova.com.ar/v2'
ZIPNOVA_ACCOUNT_ID = os.getenv('ZIPNOVA_ACCOUNT_ID', '5786')
ZIPNOVA_ORIGIN_ID  = os.getenv('ZIPNOVA_ORIGIN_ID', '374397')
ZIPNOVA_API_KEY    = os.getenv('ZIPNOVA_API_KEY', '')
ZIPNOVA_API_SECRET = os.getenv('ZIPNOVA_API_SECRET', '')
ZIPNOVA_PATAS_PESO = 2000

def _armar_bultos_bot(sku):
    """Arma bultos para un único SKU (colchon o sommier)."""
    bultos = []
    peso_patas = 0
    hay_patas  = False
    SKUS_ALM   = {'CLASICA','SUBLIME','CERVICAL','RENOVATION','PLATINO','DORAL','DUAL','EXCLUSIVE'}

    # ¿Es sommier?
    comp = _q("SELECT id FROM productos_compuestos WHERE sku=%s LIMIT 1", (sku,))
    if comp:
        comp_id = comp[0]['id']
        rows = _q("""
            SELECT pb.sku, pb.nombre, pb.alto_cm, pb.ancho_cm, pb.largo_cm,
                   pb.peso_gramos, c.cantidad_necesaria
            FROM componentes c
            JOIN productos_base pb ON c.producto_base_id = pb.id
            WHERE c.producto_compuesto_id = %s
        """, (comp_id,))
        for r in rows:
            csku = r['sku']; cant = r['cantidad_necesaria']
            if csku in SKUS_ALM:
                peso_patas += (r['peso_gramos'] or 0) * cant
            else:
                for _ in range(cant):
                    bultos.append({
                        'sku': csku, 'description': r['nombre'],
                        'weight': max(10, r['peso_gramos'] or 20000),
                        'height': r['alto_cm'] or 27,
                        'width':  r['ancho_cm'] or 100,
                        'length': r['largo_cm'] or 190,
                    })
        peso_patas += ZIPNOVA_PATAS_PESO
        hay_patas = True
    else:
        row = _q("SELECT nombre, alto_cm, ancho_cm, largo_cm, peso_gramos FROM productos_base WHERE sku=%s", (sku,))
        if row:
            r = row[0]
            bultos.append({
                'sku': sku, 'description': r['nombre'],
                'weight': max(10, r['peso_gramos'] or 20000),
                'height': r['alto_cm'] or 27,
                'width':  r['ancho_cm'] or 100,
                'length': r['largo_cm'] or 190,
            })

    if hay_patas:
        bultos.append({'sku':'PATAS','description':'Patas y accesorios',
                       'weight': max(10, int(peso_patas)), 'height':30,'width':20,'length':10})
    return bultos

CP_CIUDADES = {
    '1000': ('Buenos Aires', 'Buenos Aires'), '1425': ('Buenos Aires', 'Buenos Aires'),
    '1640': ('Martínez', 'Buenos Aires'), '1602': ('Florida', 'Buenos Aires'),
    '1706': ('Ituzaingó', 'Buenos Aires'), '1832': ('Lomas de Zamora', 'Buenos Aires'),
    '1900': ('La Plata', 'Buenos Aires'), '2000': ('Rosario', 'Santa Fe'),
    '2400': ('San Francisco', 'Córdoba'), '3000': ('Santa Fe', 'Santa Fe'),
    '3500': ('Resistencia', 'Chaco'), '4000': ('San Miguel de Tucumán', 'Tucumán'),
    '5000': ('Córdoba', 'Córdoba'), '5500': ('Mendoza', 'Mendoza'),
    '6000': ('Junín', 'Buenos Aires'), '7000': ('Tandil', 'Buenos Aires'),
    '8000': ('Bahía Blanca', 'Buenos Aires'), '9000': ('Comodoro Rivadavia', 'Chubut'),
}

def _cp_a_ciudad(cp):
    """Intenta resolver ciudad y provincia desde CP conocidos."""
    return CP_CIUDADES.get(cp, (cp, 'Buenos Aires'))

def cotizar_envio_bot(sku, cp, ciudad, provincia, precio_producto):
    """Cotiza envío con Zipnova. Retorna string listo para enviar al cliente."""
    try:
        bultos = _armar_bultos_bot(sku)
        if not bultos:
            return None
        payload = {
            'account_id':     ZIPNOVA_ACCOUNT_ID,
            'origin_id':      ZIPNOVA_ORIGIN_ID,
            'declared_value': int(precio_producto),
            'destination':    {'zipcode': cp, 'city': ciudad, 'state': provincia},
            'items':          bultos,
        }
        resp = requests.post(
            f"{ZIPNOVA_BASE_URL}/shipments/quote",
            json=payload,
            auth=(ZIPNOVA_API_KEY, ZIPNOVA_API_SECRET),
            timeout=15
        )
        if resp.status_code != 200:
            return None
        resultados = resp.json().get('all_results') or resp.json().get('results') or []
        if not resultados:
            return None
        # Tomar la opción más barata
        mejor = min(resultados, key=lambda x: x.get('price', 9999999))
        costo = mejor.get('price', 0)
        dias  = mejor.get('estimated_days', '?')
        carrier = mejor.get('carrier', {})
        carrier_name = carrier.get('name', '') if isinstance(carrier, dict) else str(carrier)
        return f"Envío a CP {cp}: ${int(costo):,} ({carrier_name}, {dias} días hábiles aprox.)"
    except Exception as e:
        print(f"[WA] Error Zipnova: {e}")
        return None

# ── Fotos ──────────────────────────────────────────────────────────
FOTO_BASE_URL = "https://sistema.mercadomuebles.com.ar/static/img/productos"

def wa_send_foto(to, sku, caption=""):
    """Envía foto del producto por WhatsApp."""
    foto_url = f"{FOTO_BASE_URL}/{sku}/1.jpg"
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
            headers={'Authorization': f'Bearer {WA_TOKEN}', 'Content-Type': 'application/json'},
            json={
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'image',
                'image': {'link': foto_url, 'caption': caption}
            },
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[WA] Error enviando foto: {e}")
        return False

# ── Productos ─────────────────────────────────────────────────────
def get_productos_context():
    """Devuelve contexto de productos para el system prompt (cacheado 10 min)."""
    cache = getattr(get_productos_context, '_cache', None)
    if cache and time.time() - cache['ts'] < 600:
        return cache['data']

    # Colchones
    colchones = _q("""
        SELECT p.sku, p.nombre, p.modelo, p.medida, p.linea, p.tipo_base,
               p.precio_base, p.descuento_catalogo, p.stock_actual,
               p.alto_cm, p.ancho_cm, p.largo_cm,
               COALESCE(o.descuento_pct, 0) as oferta_pct
        FROM productos_base p
        LEFT JOIN ofertas_home o ON o.sku = p.sku AND o.activo = 1
        WHERE p.activo = 1
        ORDER BY p.modelo, p.medida
    """)

    # Sommiers
    sommiers = _q("""
        SELECT pc.sku, pc.nombre, pc.precio_base, pc.descuento_catalogo,
               COALESCE(o.descuento_pct, 0) as oferta_pct
        FROM productos_compuestos pc
        LEFT JOIN ofertas_home o ON o.sku = pc.sku AND o.activo = 1
        WHERE pc.activo = 1
        ORDER BY pc.nombre
    """)

    # Recargos Payway
    coefs = _q("SELECT clave, valor FROM configuracion WHERE clave LIKE 'cuotas_%_coef'")
    payway = {r['clave']: float(r['valor']) for r in coefs}
    coef_3 = payway.get('cuotas_3_coef', 1.2)
    coef_6 = payway.get('cuotas_6_coef', 1.4)

    def precio_final(precio_base, desc_cat, oferta):
        desc = max(float(desc_cat or 0), float(oferta or 0))
        return round(float(precio_base) * (1 - desc / 100))

    lines = ["=== PRODUCTOS Y PRECIOS WEB (actualizados) ===\n"]

    lines.append("--- COLCHONES ---")
    for p in colchones:
        if not p['precio_base']:
            continue
        pf = precio_final(p['precio_base'], p['descuento_catalogo'], p['oferta_pct'])
        desc = max(float(p['descuento_catalogo'] or 0), float(p['oferta_pct'] or 0))
        stock = "Con stock" if p['stock_actual'] and p['stock_actual'] > 0 else "Sin stock"
        link = f"https://www.mercadomuebles.com.ar/tienda/producto/{p['sku']}"
        lines.append(
            f"• {p['nombre']} (SKU:{p['sku']}) | Precio: ${pf:,} "
            f"{'(-'+str(int(desc))+'%)' if desc > 0 else ''} | {stock} | {link}"
        )
        total_3 = round(pf * coef_3)
        total_6 = round(pf * coef_6)
        cuota_3 = round(total_3 / 3)
        cuota_6 = round(total_6 / 6)
        lines.append(
            f"  Payway 3 cuotas: ${cuota_3:,} x3 (total ${total_3:,}) | "
            f"Payway 6 cuotas: ${cuota_6:,} x6 (total ${total_6:,})"
        )

    lines.append("\n--- SOMMIERS / CONJUNTOS (colchón + base) ---")
    for p in sommiers:
        if not p['precio_base']:
            continue
        pf = precio_final(p['precio_base'], p['descuento_catalogo'], p['oferta_pct'])
        desc = max(float(p['descuento_catalogo'] or 0), float(p['oferta_pct'] or 0))
        link = f"https://www.mercadolibre.com.ar/tienda/producto/{p['sku']}"
        lines.append(
            f"• {p['nombre']} (SKU:{p['sku']}) | Precio: ${pf:,} "
            f"{'(-'+str(int(desc))+'%)' if desc > 0 else ''} | {link}"
        )
        total_3 = round(pf * coef_3)
        total_6 = round(pf * coef_6)
        cuota_3 = round(total_3 / 3)
        cuota_6 = round(total_6 / 6)
        lines.append(
            f"  Payway 3 cuotas: ${cuota_3:,} x3 (total ${total_3:,}) | "
            f"Payway 6 cuotas: ${cuota_6:,} x6 (total ${total_6:,})"
        )

    # Bases sueltas
    bases = _q("""
        SELECT sku, nombre, precio_base FROM productos_base
        WHERE sku LIKE 'BASE%' AND activo=1 ORDER BY nombre
    """)
    if bases:
        lines.append("\n--- BASES SUELTAS (precio por unidad, color fijo por modelo) ---")
        for b in bases:
            if b['precio_base']:
                lines.append(f"• {b['nombre']} (SKU:{b['sku']}) | ${int(b['precio_base']):,}")

    data = '\n'.join(lines)
    get_productos_context._cache = {'ts': time.time(), 'data': data}
    return data

# ── System prompt ─────────────────────────────────────────────────
CATALOGO_INFO = """
CATÁLOGO CANNON 2025 — CARACTERÍSTICAS DE PRODUCTOS:

VOCABULARIO IMPORTANTE:
- "Sommier", "conjunto" o "sommier conjunto" = colchón + base/box. Son sinónimos.
- "Colchón solo" = solo el colchón, sin base.
- "Base" o "box" = la base del sommier (se vende sola o en conjunto).
- "2 plazas" puede ser 140x190 cm O 150x190 cm — siempre confirmar medida exacta.

COLCHONES DE ESPUMA:
- Tropical Matelaseado: espuma 22kg/m³, 18cm alto, sistema flip, sensación suave, soporte 70kg. Color: diseño tropical multicolor. Ideal para uso diario.
- Princess 20: espuma 24kg/m³, 20cm, flip, firme, soporte 80kg. Color: diseño floral lila/gris. Tela sábana matelaseada.
- Princess 23: espuma 24kg/m³, 23cm, flip, firme, soporte 80kg. Color: blanco con banda gris oscura. Tela Jacquard.
- Exclusive: espuma alta densidad 30kg/m³, 25cm, flip, firme, soporte 100kg. Color: blanco con banda marrón oscuro. Máxima durabilidad.
- Exclusive Pillow Top: igual que Exclusive con capa pillow top, 29cm. Más suavidad al tacto.
- Renovation: espuma altísima densidad 35kg/m³, 26cm, flip, extra firme, soporte 120kg. Color: blanco/gris neutro.
- Renovation Euro Pillow: igual que Renovation con euro pillow, 33cm, extra firme.
- Compac: espuma multicapa 30kg/m³, 25cm, sistema NO flip, firme, soporte 100kg.

COLCHONES DE RESORTES:
- Soñar: resortes bicónicos reforzados, 23cm, flip, suave, soporte 80kg. Entrada de gama resortes.
- Doral: resortes continuos Ultracoil, 27cm, flip, firme, soporte 100kg. Color: diseño gris jaspeado con banda gris. Muy buena estabilidad.
- Doral Pillow Top: igual que Doral con pillow top, 33cm, firme.
- Sublime: resortes individuales Pocket, 32cm, flip, firme, soporte 120kg. Color: blanco perla con detalles dorados. No transmite movimiento entre personas.
- Sublime Euro Pillow: igual que Sublime con euro pillow, 35cm.

BASES / BOX — COLORES FIJOS POR MODELO (no son intercambiables):
Los colores de las bases hacen juego con la banda lateral del colchón correspondiente. NO se puede elegir color — cada modelo tiene su base específica.
- Base Sábana: color gris claro suave. Va con modelos Princess, Soñar, Tropical.
- Base Chocolate: color marrón oscuro. Va con modelos Exclusive, Doral.
- Base Gris: color gris oscuro. Va con Renovation, algunos Doral.
- Base Sublime: color beige/crema. Va exclusivamente con el Sublime.
Cada base tiene precio propio según modelo y medida (NO son todas al mismo precio).

MEDIDAS DISPONIBLES (según modelo): 80x190, 90x190, 100x190, 140x190, 150x190, 160x200, 180x200, 200x200

ENVÍOS:
- Colchones y sommiers: Zipnova. Costo exacto se puede calcular con el código postal del cliente.
- Almohadas: calculado por MercadoPago en el checkout.
- CABA y GBA suelen ser más económicos que el interior del país.

MEDIOS DE PAGO:
- MercadoPago: todas las formas (débito, crédito, transferencia, depósito, PagoFácil/RapiPago, dinero en cuenta MP).
- Payway: Visa o Mastercard bancarizadas. 3 o 6 cuotas fijas (con interés embebido).

GARANTÍA: 5 años de garantía de fábrica.
"""

def get_system_prompt():
    productos = get_productos_context()
    # Horario de atención
    now = datetime.now()
    # Argentina es UTC-3
    hora_arg = (now.hour - 3) % 24
    dia_semana = now.weekday()  # 0=lunes, 6=domingo
    en_horario = (dia_semana < 5 and 8 <= hora_arg < 17)
    horario_txt = (
        "Estamos dentro del horario de atención (L-V 8-17hs)."
        if en_horario else
        "Estamos FUERA del horario de atención. El horario es lunes a viernes de 8 a 17hs. "
        "Cuando derives o el cliente pida hablar con alguien, avisale que un asesor lo va a contactar en ese horario."
    )

    return f"""Sos el asistente virtual de Mercado Muebles, distribuidora oficial de colchones Cannon en Buenos Aires.
Atendés consultas de clientes por WhatsApp.

PERSONALIDAD Y FORMATO:
- Amable y cercano, sin ser exagerado ni adulador
- Usás el voseo rioplatense (vos, tenés, podés)
- Respuestas concisas, máximo 4 párrafos
- NUNCA uses asteriscos (*), guiones (-) al inicio, ni ningún formato markdown
- Es WhatsApp: texto plano solamente. Usá saltos de línea para separar ideas.
- Podés usar emojis con moderación si viene al caso
- NUNCA te presentes como bot, agente virtual, IA o asistente automático a menos que el cliente lo pregunte explícitamente
- Si el cliente pregunta si sos un bot o una persona, podés responder honestamente que sos un asistente virtual

COTIZACIONES:
- Cuando el cliente no especifica modelo exacto, siempre cotizá 2 opciones similares dentro del rango pedido
- "2 plazas" puede ser 140x190 O 150x190. SIEMPRE preguntá la medida exacta para que coincida con su base/cama
- "Con base" o "con box" = sommier (colchón + base). Cotizá el sommier correspondiente
- Cuando cotices con Payway, el formato correcto es: "3 cuotas fijas de $XX.XXX (total $XXX.XXX)"
  NUNCA digas "sin interés" — las cuotas de Payway tienen interés embebido en el precio
- No expliques cómo se calcula el recargo — solo mostrá el precio de cuota y el total

ENVÍOS:
- Podés calcular el costo de envío exacto si el cliente te da su código postal
- Cuando el cliente pida el costo de envío, pedile el código postal si no lo tenés
- Una vez que tengas SKU + CP, usá el comando [COTIZAR_ENVIO:SKU:CP:CIUDAD:PROVINCIA] en tu respuesta
  Ejemplo: "Te calculo el envío ahora. [COTIZAR_ENVIO:CDO140:2000:Rosario:Santa Fe]"
  El sistema reemplaza ese comando con el costo real antes de enviarlo al cliente
- Si no sabés la ciudad o provincia, podés usar el CP solo y la ciudad como "N/A"

FOTOS:
- Cuando recomendés o cotices un producto específico, podés enviar la foto usando [FOTO:SKU]
  Ejemplo: "Acá te muestro cómo es. [FOTO:CDOP160]"
- Usá solo la primera foto (orden 1) — no mandes varias fotos seguidas
- Solo enviá foto cuando el cliente pregunta por un modelo específico o cuando lo recomendás puntualmente

MEDIOS DE PAGO:
- MercadoPago: precio de lista, todas las formas (débito, crédito, transferencia, PagoFácil/RapiPago)
- Payway: Visa o Mastercard bancarizadas. Formato: "3 cuotas fijas de $X (total $Y)" o "6 cuotas fijas de $X (total $Y)"

HORARIO: {horario_txt}

DERIVAR A HUMANO cuando:
- El cliente pide hablar con una persona
- El cliente consulta por una compra ya realizada (pedido, entrega, reclamo)
- Detectás frustración (frases como "no entendés", "no me ayudás", más de 2 intentos fallidos)
- Pregunta algo fuera de tu alcance
Cuando derivés, usá EXACTAMENTE: [DERIVAR] seguido de tu mensaje.
Ejemplo: "[DERIVAR] Entiendo, te voy a conectar con un asesor que te va a atender."
Si estás fuera de horario, avisale que lo van a contactar en el próximo horario hábil.

REGLAS CRÍTICAS — INCUMPLIRLAS ES UN ERROR GRAVE:
1. NUNCA preguntes algo que el cliente ya respondió en esta conversación
2. NUNCA hagas más de UNA pregunta por mensaje
3. Si el cliente dijo "colchón solo" → NUNCA vuelvas a preguntar si quiere con base
4. Si el cliente dio una medida → NUNCA vuelvas a preguntar la medida
5. Si el cliente dio un CP → calculá el envío directamente, no preguntes de qué producto
6. Si el cliente mencionó un modelo → no preguntes el modelo de nuevo
7. Leé el bloque "DATOS YA CONFIRMADOS" al inicio y úsalos como hechos firmes
8. Cuando tengas producto + medida + CP → ejecutá [COTIZAR_ENVIO:SKU:CP:CIUDAD:PROVINCIA] sin preguntar nada

NUNCA:
- Inventes precios o características que no estén en la info provista
- Des información sobre pedidos ya realizados
- Prometás fechas de entrega exactas
- Digas "no recibí mensajes anteriores" — el historial completo está disponible

{CATALOGO_INFO}

{productos}"""

# ── WhatsApp API ──────────────────────────────────────────────────
def wa_send(to, text):
    """Envía mensaje de texto por WhatsApp."""
    if not WA_TOKEN or not WA_PHONE_ID:
        print(f"[WA] Sin credenciales. Mensaje para {to}: {text[:50]}")
        return False
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
            headers={
                'Authorization': f'Bearer {WA_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': text}
            },
            timeout=10
        )
        if r.status_code != 200:
            print(f"[WA] Error enviando a {to}: {r.status_code} {r.text[:100]}")
        return r.status_code == 200
    except Exception as e:
        print(f"[WA] Excepción enviando a {to}: {e}")
        return False

def wa_mark_read(phone, msg_id):
    """Marca mensaje como leído."""
    try:
        requests.post(
            f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
            headers={'Authorization': f'Bearer {WA_TOKEN}', 'Content-Type': 'application/json'},
            json={'messaging_product': 'whatsapp', 'status': 'read', 'message_id': msg_id},
            timeout=5
        )
    except Exception:
        pass

# ── Derivación ────────────────────────────────────────────────────
def derivar_a_humano(phone_cliente, historial):
    """Manda resumen al número de derivación."""
    try:
        msgs_texto = '\n'.join(
            f"{'Cliente' if m['role']=='user' else 'Bot'}: {m['content']}"
            for m in historial[-10:]
        )
        resumen_resp = anthropic.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=200,
            messages=[{
                'role': 'user',
                'content': f"""Resumí esta conversación en 2 líneas máximo:
1. Qué buscaba el cliente
2. Por qué se derivó

{msgs_texto}

Solo el resumen, sin introducción."""
            }]
        )
        resumen = resumen_resp.content[0].text.strip()
    except Exception as e:
        print(f"[WA] Error generando resumen: {e}")
        resumen = "No se pudo generar resumen."

    ultima = historial[-1]['content'][:120] if historial else '-'
    msg = (
        f"Derivacion WA\n"
        f"Cliente: +{phone_cliente}\n"
        f"Resumen: {resumen}\n"
        f"Ultima consulta: {ultima}"
    )

    ok = wa_send(NUMERO_DERIVAR.replace('+', ''), msg)
    print(f"[WA] Derivacion {'OK' if ok else 'FALLO'} para {phone_cliente} → {NUMERO_DERIVAR}")
    if not ok:
        # Segundo intento sin el +
        num = NUMERO_DERIVAR.lstrip('+')
        wa_send(num, msg)

# ── Claude ────────────────────────────────────────────────────────
def _extraer_contexto(historial):
    """
    Extractor rápido basado en reglas. Busca datos clave en el historial
    y los inyecta como contexto explícito para evitar re-preguntas.
    """
    if not historial or len(historial) < 2:
        return ""

    import re as _re

    # Texto completo del cliente (mensajes user)
    texto_cliente = ' '.join(
        m['content'].lower() for m in historial if m['role'] == 'user'
    )
    # Texto completo de toda la conv
    texto_todo = ' '.join(m['content'].lower() for m in historial)

    datos = {}

    # Medida
    medida_match = _re.search(r'\b(80|90|100|130|140|150|160|180|200)\s*[xX×]\s*1[89]0\b', texto_cliente)
    if medida_match:
        datos['Medida confirmada'] = medida_match.group(0).replace(' ','').upper()
    elif _re.search(r'\b80\b', texto_cliente) and _re.search(r'plaza', texto_cliente):
        datos['Medida confirmada'] = '80x190'
    elif _re.search(r'\b(140|150)\b', texto_cliente) and not medida_match:
        n = _re.search(r'\b(140|150)\b', texto_cliente).group(1)
        datos['Medida confirmada'] = f'{n}x190 (confirmar si es x190 o x200)'

    # Tipo de producto
    if _re.search(r'\b(solo colch[oó]n|colch[oó]n solo|sin base|sin box|solo el colch[oó]n)\b', texto_cliente):
        datos['Tipo'] = 'solo colchón (SIN base/sommier)'
    elif _re.search(r'\b(con base|con box|sommier|conjunto|set)\b', texto_cliente):
        datos['Tipo'] = 'sommier/conjunto (colchón + base)'

    # Modelo mencionado
    modelos = {
        'tropical': 'Tropical', 'princess': 'Princess',
        'exclusive': 'Exclusive', 'renovation': 'Renovation',
        'doral': 'Doral', 'sublime': 'Sublime', 'soñar': 'Soñar',
        'sonar': 'Soñar', 'compac': 'Compac',
    }
    for k, v in modelos.items():
        if k in texto_cliente:
            datos['Modelo mencionado'] = v
            break

    # Pillow top
    if _re.search(r'\b(pillow|euro pillow|con pillow)\b', texto_cliente):
        datos['Variante'] = 'con Pillow Top'

    # Densidad
    dens = _re.search(r'\b(22|24|30|35)\s*kg\b', texto_cliente)
    if dens:
        datos['Densidad requerida'] = f'{dens.group(1)} kg/m³'

    # Código postal
    cp_match = _re.search(r'\bcp\s*(\d{4})\b|\b(\d{4})\b(?=.*rosario|.*córdoba|.*mendoza|.*tucumán)', texto_cliente)
    if not cp_match:
        cp_match = _re.search(r'(?:cp|código postal|codigo postal)[:\s]*(\d{4})', texto_cliente)
    if cp_match:
        cp = cp_match.group(1) or cp_match.group(2)
        datos['CP destino'] = cp

    # Ciudad mencionada
    ciudades = ['rosario', 'córdoba', 'cordoba', 'mendoza', 'tucumán', 'tucuman',
                'la plata', 'mar del plata', 'santa fe', 'bahía blanca', 'bahia blanca',
                'salta', 'neuquén', 'neuquen', 'resistencia', 'posadas']
    for c in ciudades:
        if c in texto_cliente:
            datos['Ciudad destino'] = c.title()
            break

    # Presupuesto
    if _re.search(r'\b(econ[oó]mico|barato|lo m[aá]s barato|precio bajo|entry)\b', texto_cliente):
        datos['Preferencia'] = 'económico'
    elif _re.search(r'\b(gama media|intermedio|relaci[oó]n calidad)\b', texto_cliente):
        datos['Preferencia'] = 'gama media'
    elif _re.search(r'\b(lo mejor|premium|alta gama|el mejor)\b', texto_cliente):
        datos['Preferencia'] = 'premium'

    if not datos:
        return ""

    lineas = ['\n⚠️ DATOS YA CONFIRMADOS (NO volver a preguntar):']
    for k, v in datos.items():
        lineas.append(f'  {k}: {v}')
    lineas.append('  → Usá estos datos directamente sin pedir confirmación.\n')
    return '\n'.join(lineas)

def _guardar_mensaje(phone, rol, contenido, derivado=False):
    """Guarda mensaje en BD para historial persistente."""
    try:
        _exec(
            "INSERT INTO wa_mensajes (phone, rol, contenido, derivado) VALUES (%s,%s,%s,%s)",
            (phone, rol, contenido, 1 if derivado else 0)
        )
    except Exception as e:
        print(f"[WA] Error guardando mensaje: {e}")

def procesar_mensaje(phone, texto):
    """Procesa mensaje del cliente y genera respuesta."""
    if phone not in conversaciones:
        conversaciones[phone] = []

    historial = conversaciones[phone]
    historial.append({'role': 'user', 'content': texto})
    _guardar_mensaje(phone, 'user', texto)

    # Limitar historial a 20 mensajes
    if len(historial) > 20:
        historial = historial[-20:]
        conversaciones[phone] = historial

    # Extraer contexto acumulado e inyectarlo al system prompt
    ctx_acumulado = _extraer_contexto(historial[:-1])  # sin el último mensaje del usuario
    system = get_system_prompt() + ctx_acumulado

    try:
        resp = anthropic.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            system=system,
            messages=historial
        )
        respuesta = resp.content[0].text.strip()
    except Exception as e:
        print(f"[WA] Error Claude: {e}")
        respuesta = "Disculpá, tuve un problema técnico. Podés intentar de nuevo en unos minutos."

    # Limpiar markdown que no funciona en WhatsApp
    import re as _re
    respuesta = _re.sub(r'\*\*(.+?)\*\*', r'\1', respuesta)
    respuesta = _re.sub(r'\*(.+?)\*', r'\1', respuesta)
    respuesta = _re.sub(r'^[•\-]\s+', '', respuesta, flags=_re.MULTILINE)
    respuesta = _re.sub(r'^\d+\.\s+', '', respuesta, flags=_re.MULTILINE)

    # Procesar [COTIZAR_ENVIO:SKU:CP:CIUDAD:PROVINCIA]
    envio_match = _re.search(r'\[COTIZAR_ENVIO:([^:\]]+):([^:\]]+):([^:\]]+):([^:\]]+)\]', respuesta)
    if envio_match:
        sku_env, cp_env, ciudad_env, prov_env = envio_match.groups()
        sku_env = sku_env.strip(); cp_env = cp_env.strip()
        # Auto-resolver ciudad/provincia si no se conocen
        if not ciudad_env.strip() or ciudad_env.strip() in ('N/A', '?', 'desconocida'):
            ciudad_env, prov_env = _cp_a_ciudad(cp_env)
        else:
            ciudad_env = ciudad_env.strip(); prov_env = prov_env.strip()
        # Buscar precio del producto
        prod = _q("SELECT precio_base, descuento_catalogo FROM productos_base WHERE sku=%s", (sku_env,))
        if not prod:
            prod = _q("SELECT precio_base, descuento_catalogo FROM productos_compuestos WHERE sku=%s", (sku_env,))
        precio_env = 0
        if prod:
            pb = float(prod[0]['precio_base'] or 0)
            desc = float(prod[0]['descuento_catalogo'] or 0)
            precio_env = round(pb * (1 - desc/100))
        costo_txt = cotizar_envio_bot(sku_env, cp_env, ciudad_env, prov_env, precio_env)
        if costo_txt:
            respuesta = respuesta.replace(envio_match.group(0), costo_txt)
        else:
            respuesta = respuesta.replace(envio_match.group(0), "No pude calcular el envío ahora. Podés consultarlo en el checkout de la tienda.")

    # Extraer comandos [FOTO:SKU] para enviarlos después
    fotos_a_enviar = _re.findall(r'\[FOTO:([A-Z0-9]+)\]', respuesta)
    respuesta = _re.sub(r'\[FOTO:[A-Z0-9]+\]', '', respuesta).strip()

    # Detectar derivación
    derivar = '[DERIVAR]' in respuesta
    if derivar:
        respuesta = respuesta.replace('[DERIVAR]', '').strip()

    historial.append({'role': 'assistant', 'content': respuesta})
    _guardar_mensaje(phone, 'assistant', respuesta, derivado=derivar)

    if derivar:
        threading.Thread(
            target=derivar_a_humano,
            args=(phone, historial.copy()),
            daemon=True
        ).start()

    return respuesta, fotos_a_enviar

# ── Webhook ───────────────────────────────────────────────────────
@whatsapp_bp.route('/webhook/whatsapp', methods=['GET'])
def webhook_verify():
    """Verificación del webhook por Meta."""
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == WA_VERIFY_TOKEN:
        print("[WA] Webhook verificado OK")
        return challenge, 200
    return 'Forbidden', 403

@whatsapp_bp.route('/webhook/whatsapp', methods=['POST'])
def webhook_message():
    """Recibe mensajes entrantes."""
    data = request.get_json(silent=True)
    if not data:
        return 'OK', 200

    try:
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        for msg in messages:
            phone  = msg.get('from', '')
            msg_id = msg.get('id', '')
            tipo   = msg.get('type', '')

            # Solo texto por ahora
            if tipo != 'text':
                wa_send(phone, "Por el momento solo puedo responder mensajes de texto. ¿En qué te puedo ayudar?")
                continue

            texto = msg.get('text', {}).get('body', '').strip()
            if not texto:
                continue

            # Evitar procesamiento duplicado
            if processing.get(msg_id):
                continue
            processing[msg_id] = True

            # Marcar como leído
            wa_mark_read(phone, msg_id)

            # Procesar en thread para no bloquear
            def responder(ph=phone, tx=texto, mid=msg_id):
                try:
                    respuesta, fotos = procesar_mensaje(ph, tx)
                    wa_send(ph, respuesta)
                    # Enviar fotos después del texto
                    for sku_foto in fotos:
                        wa_send_foto(ph, sku_foto)
                except Exception as e:
                    print(f"[WA] Error procesando {ph}: {e}")
                finally:
                    processing.pop(mid, None)

            threading.Thread(target=responder, daemon=True).start()

    except Exception as e:
        print(f"[WA] Error en webhook: {e}")

    return 'OK', 200

# ── Panel de conversaciones (admin) ──────────────────────────────
@whatsapp_bp.route('/admin/whatsapp/conversaciones')
def wa_conversaciones():
    """Vista rápida de conversaciones activas."""
    resumen = []
    for phone, msgs in conversaciones.items():
        if msgs:
            ultimo = msgs[-1]
            resumen.append({
                'phone': phone,
                'mensajes': len(msgs),
                'ultimo_rol': ultimo['role'],
                'ultimo_texto': ultimo['content'][:80],
            })
    return jsonify({'conversaciones': resumen, 'total': len(resumen)})

@whatsapp_bp.route('/admin/whatsapp/limpiar', methods=['POST'])
def wa_limpiar():
    data = request.get_json() or {}
    phone = data.get('phone')
    if phone and phone in conversaciones:
        del conversaciones[phone]
    return jsonify({'ok': True})

@whatsapp_bp.route('/admin/whatsapp')
def wa_admin():
    from flask import render_template
    return render_template('whatsapp_admin.html')

@whatsapp_bp.route('/admin/whatsapp/chats')
def wa_chats():
    """Lista de conversaciones con último mensaje."""
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    rows = _q("""
        SELECT phone,
               COUNT(*) as total_msgs,
               SUM(rol='user') as msgs_cliente,
               MAX(fecha) as ultimo_msg,
               MAX(derivado) as fue_derivado,
               (SELECT contenido FROM wa_mensajes m2
                WHERE m2.phone = m.phone ORDER BY fecha DESC LIMIT 1) as ultimo_texto
        FROM wa_mensajes m
        WHERE DATE(fecha) = %s
        GROUP BY phone
        ORDER BY MAX(fecha) DESC
    """, [fecha])
    def fix(r):
        return {k: (str(v) if hasattr(v,'strftime') else v) for k,v in r.items()}
    return jsonify({'chats': [fix(r) for r in rows], 'fecha': fecha})

@whatsapp_bp.route('/admin/whatsapp/chat/<phone>')
def wa_chat_detalle(phone):
    """Mensajes de una conversación."""
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    rows = _q("""
        SELECT id, fecha, rol, contenido, derivado
        FROM wa_mensajes
        WHERE phone = %s AND DATE(fecha) = %s
        ORDER BY fecha ASC
    """, [phone, fecha])
    def fix(r):
        return {k: (str(v) if hasattr(v,'strftime') else v) for k,v in r.items()}
    return jsonify({'mensajes': [fix(r) for r in rows], 'phone': phone})

@whatsapp_bp.route('/admin/whatsapp/fechas')
def wa_fechas():
    """Fechas con actividad."""
    rows = _q("""
        SELECT DATE(fecha) as fecha, COUNT(DISTINCT phone) as chats, COUNT(*) as msgs
        FROM wa_mensajes
        GROUP BY DATE(fecha)
        ORDER BY fecha DESC
        LIMIT 30
    """)
    return jsonify({'fechas': [{'fecha': str(r['fecha']), 'chats': r['chats'], 'msgs': r['msgs']} for r in rows]})
