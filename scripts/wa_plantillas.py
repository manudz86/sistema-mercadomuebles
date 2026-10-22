#!/usr/bin/env python3
"""Plantillas de WhatsApp Business: listar (solo lectura) y crear.

Uso:
    venv/bin/python3 scripts/wa_plantillas.py listar
    venv/bin/python3 scripts/wa_plantillas.py ver <nombre>

Crear una plantilla la envia a aprobacion de Meta bajo la cuenta de negocio
del comercio, asi que NO se hace desde aca sin pedirlo explicitamente: para
eso esta el comando 'crear', que exige --confirmar.

    venv/bin/python3 scripts/wa_plantillas.py crear <archivo.json> --confirmar

Nunca imprime el token.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests as req_lib  # noqa: E402
from _common import cargar_env  # noqa: E402

ENV = cargar_env()
TOKEN = ENV.get('WA_ACCESS_TOKEN', '')
WABA = ENV.get('WA_BUSINESS_ACCOUNT_ID', '')
API = 'https://graph.facebook.com/v25.0'


def _headers():
    return {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}


def listar(filtro=None):
    r = req_lib.get(f'{API}/{WABA}/message_templates',
                    params={'limit': 100,
                            'fields': 'name,status,category,language,components'},
                    headers=_headers(), timeout=30)
    if r.status_code != 200:
        print(f'HTTP {r.status_code}: {r.text[:500]}')
        return 1
    datos = (r.json() or {}).get('data', [])
    print(f'{len(datos)} plantilla(s)\n')
    print(f'{"NOMBRE":<32} {"ESTADO":<12} {"CATEGORIA":<16} IDIOMA')
    print('-' * 78)
    for t in sorted(datos, key=lambda x: x.get('name', '')):
        if filtro and filtro.lower() not in t.get('name', '').lower():
            continue
        print(f'{t.get("name",""):<32} {t.get("status",""):<12} '
              f'{t.get("category",""):<16} {t.get("language","")}')
    return 0


def ver(nombre):
    r = req_lib.get(f'{API}/{WABA}/message_templates',
                    params={'limit': 100,
                            'fields': 'name,status,category,language,components'},
                    headers=_headers(), timeout=30)
    r.raise_for_status()
    for t in (r.json() or {}).get('data', []):
        if t.get('name') == nombre:
            print(json.dumps(t, ensure_ascii=False, indent=2))
            return 0
    print(f'No existe la plantilla {nombre!r}')
    return 1


def crear(ruta):
    with open(ruta) as f:
        cuerpo = json.load(f)
    print(json.dumps(cuerpo, ensure_ascii=False, indent=2))
    r = req_lib.post(f'{API}/{WABA}/message_templates',
                     json=cuerpo, headers=_headers(), timeout=30)
    print(f'\nHTTP {r.status_code}')
    print(r.text[:800])
    return 0 if r.status_code in (200, 201) else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if not TOKEN or not WABA:
        print('Faltan WA_ACCESS_TOKEN o WA_BUSINESS_ACCOUNT_ID en config/.env')
        return 2
    cmd = sys.argv[1]
    if cmd == 'listar':
        return listar(sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == 'ver' and len(sys.argv) > 2:
        return ver(sys.argv[2])
    if cmd == 'crear' and len(sys.argv) > 2:
        if '--confirmar' not in sys.argv:
            print('Crear una plantilla la manda a aprobacion de Meta.')
            print('Agregá --confirmar si es lo que querés hacer.')
            return 2
        return crear(sys.argv[2])
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
