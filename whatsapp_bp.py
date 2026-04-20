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
        lines.append(
            f"  Payway 3c: ${round(pf*coef_3):,} | Payway 6c: ${round(pf*coef_6):,}"
        )

    lines.append("\n--- SOMMIERS (colchón + base) ---")
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
        lines.append(
            f"  Payway 3c: ${round(pf*coef_3):,} | Payway 6c: ${round(pf*coef_6):,}"
        )

    data = '\n'.join(lines)
    get_productos_context._cache = {'ts': time.time(), 'data': data}
    return data

# ── System prompt ─────────────────────────────────────────────────
CATALOGO_INFO = """
CATÁLOGO CANNON 2025 — CARACTERÍSTICAS DE PRODUCTOS:

COLCHONES DE ESPUMA:
• Tropical Matelaseado: espuma 22kg/m³, 18cm alto, sistema flip, sensación suave, soporte 70kg. Ideal para uso diario con mejor relación calidad/precio.
• Princess 20: espuma 24kg/m³, 20cm, flip, firme, soporte 80kg. Práctico y económico.
• Princess 23: espuma 24kg/m³, 23cm, flip, firme, tela Jacquard, soporte 80kg.
• Exclusive: espuma alta densidad 30kg/m³, 25cm, flip, firme, soporte 100kg. Máxima durabilidad.
• Exclusive Pillow Top: igual que Exclusive con capa pillow top para más suavidad, 29cm.
• Renovation: espuma altísima densidad 35kg/m³, 26cm, flip, extra firme, soporte 120kg.
• Renovation Euro Pillow: igual que Renovation con euro pillow, 33cm, extra firme.
• Compac: espuma multicapa 30kg/m³, 25cm, sistema NO flip (no se da vuelta), firme, soporte 100kg.

COLCHONES DE RESORTES:
• Soñar: resortes bicónicos reforzados, 23cm, flip, suave, soporte 80kg. Entrada de gama de resortes.
• Doral: resortes continuos Ultracoil, 27cm, flip, firme, soporte 100kg. Muy buena estabilidad.
• Doral Pillow Top: igual que Doral con pillow top, 33cm, firme.
• Sublime: resortes individuales Pocket, 32cm, flip, firme, soporte 120kg. Máxima calidad de resortes, no transmite movimiento entre personas.
• Sublime Euro Pillow: igual que Sublime con euro pillow, 35cm.

MEDIDAS DISPONIBLES (según modelo): 80x190, 90x190, 100x190, 130x190, 140x190, 150x190, 160x200, 180x200, 200x200

SOMMIERS: Colchón + base(s). Disponibles en los modelos Princess, Doral, Exclusive, Renovation, Sublime.

ENVÍOS:
• Colchones y sommiers: Zipnova (costo varía según ubicación, se calcula en el checkout)
• Almohadas: calculado por MercadoPago en el checkout
• El envío a CABA y GBA suele ser más económico que al interior

MEDIOS DE PAGO:
• MercadoPago: todas las opciones (tarjeta débito/crédito, transferencia, depósito, PagoFácil/RapiPago, dinero en cuenta MP). Cuotas según banco emisor.
• Payway: Visa o Mastercard bancarizadas. 3 cuotas o 6 cuotas sin interés (con recargo sobre el precio de lista, ya incluido en los precios que mostrás).

GARANTÍA: 5 años de garantía de fábrica en todos los productos.
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

COTIZACIONES:
- Cuando el cliente no especifica modelo exacto, siempre cotizá 2 opciones similares dentro del rango pedido
- "2 plazas" puede ser 140x190 O 150x190. SIEMPRE preguntá la medida exacta para que coincida con su base/cama
- "Con base" o "con box" = sommier (colchón + base). Cotizá el sommier correspondiente
- Cuando cotices con Payway, el formato correcto es: "3 cuotas fijas de $XX.XXX (total $XXX.XXX)"
  NUNCA digas "sin interés" — las cuotas de Payway tienen interés embebido en el precio
- No expliques cómo se calcula el recargo — solo mostrá el precio de cuota y el total

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

NUNCA:
- Inventes precios o características que no estén en la info provista
- Des información sobre pedidos ya realizados
- Prometás fechas de entrega exactas

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
            model='claude-sonnet-4-5',
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

    try:
        resp = anthropic.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=600,
            system=get_system_prompt(),
            messages=historial
        )
        respuesta = resp.content[0].text.strip()
    except Exception as e:
        print(f"[WA] Error Claude: {e}")
        respuesta = "Disculpá, tuve un problema técnico. Podés intentar de nuevo en unos minutos."

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

    return respuesta

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
                    respuesta = procesar_mensaje(ph, tx)
                    wa_send(ph, respuesta)
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
