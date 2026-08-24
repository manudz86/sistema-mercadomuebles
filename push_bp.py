"""Web Push (notificaciones) para la PWA instalada en el iPhone (home screen).
Solo se suscriben los dispositivos que instalaron la app; las PC con la web en
una pestaña NO se suscriben, así que no reciben push."""
import os
import json
import hashlib
import pymysql
from flask import Blueprint, request, jsonify

push_bp = Blueprint('push_bp', __name__)

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
VAPID_PRIVATE = os.path.join(_APP_DIR, 'config', 'vapid_private.pem')


def _db():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'inventario_cannon'),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _crear_tabla():
    try:
        db = _db(); cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                endpoint      TEXT NOT NULL,
                endpoint_hash CHAR(64) NOT NULL UNIQUE,
                p256dh        VARCHAR(255) NOT NULL,
                auth          VARCHAR(255) NOT NULL,
                ua            VARCHAR(255),
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.close(); db.close()
    except Exception as e:
        print(f"[PUSH] Error creando tabla: {e}")


_crear_tabla()


def enviar_push(titulo, cuerpo, url='/', tag='cannon', badge=None):
    """Envía una notificación a todas las suscripciones. Borra las muertas (404/410).
    Devuelve cuántas se enviaron OK. Es seguro llamarlo desde threads/background.
    badge: si se pasa, el service worker pone ese número en el ícono de la home (iOS)."""
    from pywebpush import webpush, WebPushException
    if not os.path.exists(VAPID_PRIVATE):
        print("[PUSH] Falta config/vapid_private.pem — no se envía.")
        return 0
    email = os.getenv('VAPID_ADMIN_EMAIL', 'mailto:admin@mercadomuebles.com.ar')
    _payload = {'title': titulo, 'body': cuerpo, 'url': url, 'tag': tag}
    if badge is not None:
        try:
            _payload['badge_count'] = int(badge)
        except (TypeError, ValueError):
            pass
    payload = json.dumps(_payload, ensure_ascii=False)
    enviados = 0
    try:
        db = _db(); cur = db.cursor()
        cur.execute("SELECT id, endpoint, p256dh, auth FROM push_subscriptions")
        subs = cur.fetchall()
        for s in subs:
            try:
                webpush(
                    subscription_info={'endpoint': s['endpoint'],
                                       'keys': {'p256dh': s['p256dh'], 'auth': s['auth']}},
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE,
                    vapid_claims={'sub': email},
                    ttl=3600,
                )
                enviados += 1
            except WebPushException as e:
                code = getattr(getattr(e, 'response', None), 'status_code', None)
                if code in (404, 410):     # suscripción vencida/borrada → limpiar
                    cur.execute("DELETE FROM push_subscriptions WHERE id=%s", (s['id'],))
                else:
                    print(f"[PUSH] error enviando a {s['id']}: {e}")
            except Exception as e:
                print(f"[PUSH] error {s['id']}: {e}")
        cur.close(); db.close()
    except Exception as e:
        print(f"[PUSH] enviar_push error: {e}")
    return enviados


def notificar_nueva_venta(venta_id):
    """Notifica una nueva venta a los iPhone suscriptos: canal + artículo + importe.
    Deriva el canal del campo 'canal' de la venta (ML / WEB / EXT). Corre en
    background y nunca rompe el flujo del que la llama."""
    import threading

    def _bg():
        try:
            db = _db(); cur = db.cursor()
            cur.execute("SELECT canal, importe_total FROM ventas WHERE id=%s", (venta_id,))
            v = cur.fetchone()
            if not v:
                cur.close(); db.close(); return
            cur.execute("""
                SELECT iv.cantidad, COALESCE(pb.nombre, pc.nombre, iv.sku) AS nombre
                FROM items_venta iv
                LEFT JOIN productos_base pb        ON pb.sku = iv.sku
                LEFT JOIN productos_compuestos pc  ON pc.sku = iv.sku
                WHERE iv.venta_id = %s AND iv.precio_unitario > 0
                ORDER BY iv.precio_unitario DESC
            """, (venta_id,))
            items = cur.fetchall()
            cur.close(); db.close()

            canal = (v.get('canal') or '').lower()
            if 'libre' in canal:
                lbl = 'ML'
            elif 'web' in canal or 'tienda' in canal:
                lbl = 'WEB'
            else:
                lbl = 'EXT'

            if items:
                p0 = items[0]
                resumen = f"{int(p0['cantidad'])} {p0['nombre']}"
                if len(items) > 1:
                    resumen += f" +{len(items) - 1} más"
            else:
                resumen = "venta"
            importe = float(v.get('importe_total') or 0)
            cuerpo = f"{resumen} por ${importe:,.0f}".replace(',', '.') if importe else resumen
            enviar_push(f"🛒 Nueva venta {lbl}", cuerpo, '/ventas/activas', f'venta-{venta_id}')
        except Exception as e:
            print(f"[PUSH] notificar_nueva_venta error: {e}")

    threading.Thread(target=_bg, daemon=True).start()


def notificar_nueva_pregunta(nuevas, total):
    """Notifica preguntas NUEVAS de ML y actualiza el badge del ícono (total sin responder).
    nuevas: lista de (texto, producto). total: cantidad sin responder tras el sync.
    Corre en background y nunca rompe el flujo del que la llama."""
    import threading

    def _bg():
        try:
            n = len(nuevas) if nuevas else 0
            if n <= 0:
                return
            if n == 1:
                texto, prod = nuevas[0]
                cuerpo = ('"' + (texto or '').strip()[:90] + '"') if (texto or '').strip() else 'Nueva pregunta'
                if prod:
                    cuerpo += ' · ' + str(prod)[:45]
                titulo = '❓ Nueva pregunta en ML'
            else:
                titulo = f'❓ {n} preguntas nuevas en ML'
                prods = [str(p)[:35] for (_, p) in nuevas[:3] if p]
                cuerpo = ' · '.join(prods) if prods else 'Tenés preguntas sin responder'
            enviar_push(titulo, cuerpo, '/preguntas', 'preguntas', badge=total)
        except Exception as e:
            print(f"[PUSH] notificar_nueva_pregunta error: {e}")

    threading.Thread(target=_bg, daemon=True).start()


@push_bp.route('/push/public-key')
def push_public_key():
    return jsonify({'key': os.getenv('VAPID_PUBLIC_KEY', '')})


@push_bp.route('/push/subscribe', methods=['POST'])
def push_subscribe():
    data = request.get_json(silent=True) or {}
    ep = data.get('endpoint')
    keys = data.get('keys') or {}
    if not ep or not keys.get('p256dh') or not keys.get('auth'):
        return jsonify({'ok': False, 'error': 'subscription inválida'}), 400
    h = hashlib.sha256(ep.encode('utf-8')).hexdigest()
    try:
        db = _db(); cur = db.cursor()
        cur.execute("""
            INSERT INTO push_subscriptions (endpoint, endpoint_hash, p256dh, auth, ua)
            VALUES (%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE p256dh=VALUES(p256dh), auth=VALUES(auth), ua=VALUES(ua)
        """, (ep, h, keys['p256dh'], keys['auth'], (request.headers.get('User-Agent', '')[:255])))
        cur.close(); db.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@push_bp.route('/push/unsubscribe', methods=['POST'])
def push_unsubscribe():
    data = request.get_json(silent=True) or {}
    ep = data.get('endpoint')
    if ep:
        try:
            h = hashlib.sha256(ep.encode('utf-8')).hexdigest()
            db = _db(); cur = db.cursor()
            cur.execute("DELETE FROM push_subscriptions WHERE endpoint_hash=%s", (h,))
            cur.close(); db.close()
        except Exception:
            pass
    return jsonify({'ok': True})


@push_bp.route('/push/test', methods=['POST'])
def push_test():
    n = enviar_push('🔔 Prueba Cannon', 'Si ves esto, las notificaciones andan 👌', '/', 'test')
    return jsonify({'ok': True, 'enviados': n})


@push_bp.route('/push/stats')
def push_stats():
    try:
        db = _db(); cur = db.cursor()
        cur.execute("SELECT COUNT(*) n FROM push_subscriptions")
        n = cur.fetchone()['n']; cur.close(); db.close()
        return jsonify({'suscripciones': n})
    except Exception as e:
        return jsonify({'error': str(e)})
