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


def enviar_push(titulo, cuerpo, url='/', tag='cannon'):
    """Envía una notificación a todas las suscripciones. Borra las muertas (404/410).
    Devuelve cuántas se enviaron OK. Es seguro llamarlo desde threads/background."""
    from pywebpush import webpush, WebPushException
    if not os.path.exists(VAPID_PRIVATE):
        print("[PUSH] Falta config/vapid_private.pem — no se envía.")
        return 0
    email = os.getenv('VAPID_ADMIN_EMAIL', 'mailto:admin@mercadomuebles.com.ar')
    payload = json.dumps({'title': titulo, 'body': cuerpo, 'url': url, 'tag': tag},
                         ensure_ascii=False)
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
