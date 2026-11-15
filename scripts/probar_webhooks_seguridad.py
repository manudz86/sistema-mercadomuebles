#!/usr/bin/env python3
"""Prueba la etapa 3 de seguridad con el test client (no escribe en la base, no llama APIs).

- WhatsApp: sin firma / firma mala → 401; firma buena con cuerpo vacío → 200 (no procesa nada).
- WhatsApp verify: token vacío o malo → 403.
- GetNet: sin credenciales configuradas → 401; credenciales malas → 401.
- Reset del sistema: contraseña equivocada → vuelve con aviso, NO resetea.
Uso: venv/bin/python scripts/probar_webhooks_seguridad.py
"""
import base64
import hashlib
import hmac
import json
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402

A.app.config['TESTING'] = True
A.login_manager.request_loader(
    lambda req: A.load_user(req.headers['X-Test-User']) if req.headers.get('X-Test-User') else None)
c = A.app.test_client()
fallas = 0


def chequear(ok, texto):
    global fallas
    fallas += not ok
    print(('OK    ' if ok else 'FALLA ') + texto)


cuerpo = json.dumps({'entry': [{'changes': [{'value': {}}]}]}).encode()
os.environ['WA_APP_SECRET'] = 'secreto-de-prueba'
r = c.post('/webhook/whatsapp', data=cuerpo, content_type='application/json')
chequear(r.status_code == 401, f'WA sin firma → {r.status_code}')
r = c.post('/webhook/whatsapp', data=cuerpo, content_type='application/json',
           headers={'X-Hub-Signature-256': 'sha256=' + '0' * 64})
chequear(r.status_code == 401, f'WA firma mala → {r.status_code}')
firma = 'sha256=' + hmac.new(b'secreto-de-prueba', cuerpo, hashlib.sha256).hexdigest()
r = c.post('/webhook/whatsapp', data=cuerpo, content_type='application/json', headers={'X-Hub-Signature-256': firma})
chequear(r.status_code == 200, f'WA firma buena → {r.status_code}')
del os.environ['WA_APP_SECRET']
r = c.post('/webhook/whatsapp', data=cuerpo, content_type='application/json')
chequear(r.status_code == 200, f'WA sin WA_APP_SECRET cargado → deja pasar ({r.status_code})')

r = c.get('/webhook/whatsapp?hub.mode=subscribe&hub.challenge=x')
chequear(r.status_code == 403, f'WA verify sin token → {r.status_code}')
r = c.get('/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=malo&hub.challenge=x')
chequear(r.status_code == 403, f'WA verify token malo → {r.status_code}')

u, p = os.environ.get('GETNET_WEBHOOK_USER'), os.environ.get('GETNET_WEBHOOK_PASS')
malas = 'Basic ' + base64.b64encode(b'x:y').decode()
r = c.post('/tienda/webhook/getnet', json={}, headers={'Authorization': malas})
chequear(r.status_code == 401, f'GetNet credenciales malas → {r.status_code}')
r = c.post('/tienda/webhook/getnet', json={})
chequear(r.status_code == 401, f'GetNet sin Authorization → {r.status_code}')
os.environ['GETNET_WEBHOOK_USER'] = ''
r = c.post('/tienda/webhook/getnet', json={})
chequear(r.status_code == 401, f'GetNet sin credenciales configuradas → {r.status_code}')
os.environ['GETNET_WEBHOOK_USER'], os.environ['GETNET_WEBHOOK_PASS'] = u or '', p or ''

r = c.post('/configuracion/resetear/ejecutar', data={'password': 'no-es-la-clave', 'confirmar': 'RESETEAR'},
           headers={'X-Test-User': '1'})
chequear(r.status_code == 302 and r.headers.get('Location', '').endswith('/configuracion/resetear'),
         f'reset con contraseña equivocada → {r.status_code} {r.headers.get("Location")}')
r = c.post('/configuracion/resetear/ejecutar', data={'password': '', 'confirmar': 'RESETEAR'},
           headers={'X-Test-User': '1'})
chequear(r.status_code == 302, f'reset sin contraseña → {r.status_code}')
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
