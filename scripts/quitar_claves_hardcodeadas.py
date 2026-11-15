#!/usr/bin/env python3
"""Saca la contraseña de MySQL y el WA_VERIFY_TOKEN escritos en el código (one-off, etapa 3).

- DB_PASSWORD con valor por defecto escrito → os.getenv('DB_PASSWORD', '')
- password='...' / DB_PASS = '...' en scripts sueltos → os.getenv('DB_PASSWORD', '') + load_dotenv
- WA_VERIFY_TOKEN con valor por defecto → sin default; si config/.env no lo tiene, agrega uno
  NUEVO al azar (el viejo quedó en el historial de git). Meta solo lo usa al (re)verificar
  el webhook, así que no corta la recepción de mensajes.

Nunca imprime valores. Hacer el backup (cp -a) ANTES de correrlo.
Uso: venv/bin/python scripts/quitar_claves_hardcodeadas.py
"""
import re
import secrets

BASE = '/home/cannon/app/'
ARCHIVOS = ['whatsapp_bp.py', 'competencia_bp.py', 'competencia_v2_bp.py', 'competencia_scraper_bp.py',
            'bot_precios_bp.py', 'fix_nombres_ml.py', 'fixx_nombres_ml.py', 'fixxx_nombres_ml.py',
            'fix_comisiones_ml.py', 'tms_analisis/motor.py', 'tms_analisis/costos.py']
DOTENV = "import os\nfrom dotenv import load_dotenv\nload_dotenv('/home/cannon/app/config/.env')\n"

R_DEFAULT = re.compile(r"""os\.(?:getenv|environ\.get)\(\s*'DB_PASSWORD'\s*,\s*(['"])[^'"]+\1\s*\)""")
R_LITERAL = re.compile(r"""\bpassword\s*=\s*(['"])[^'"]+\1""")
R_DBPASS = re.compile(r"""^DB_PASS\s*=\s*(['"])[^'"]+\1""", re.M)
R_WA = re.compile(r"""os\.getenv\('WA_VERIFY_TOKEN'\s*,\s*(['"])[^'"]+\1\)""")

for nombre in ARCHIVOS:
    ruta = BASE + nombre
    txt = open(ruta, encoding='utf-8').read()
    nuevo, n1 = R_DEFAULT.subn("os.getenv('DB_PASSWORD', '')", txt)
    nuevo, n2 = R_LITERAL.subn("password=os.getenv('DB_PASSWORD', '')", nuevo)
    nuevo, n3 = R_DBPASS.subn("DB_PASS = os.getenv('DB_PASSWORD', '')", nuevo)
    nuevo, n4 = R_WA.subn("os.getenv('WA_VERIFY_TOKEN')", nuevo)
    agrego_env = False
    if (n2 or n3 or nombre.startswith('tms_')) and 'load_dotenv' not in nuevo:
        m = re.search(r'^import .*$', nuevo, re.M)
        nuevo = nuevo[:m.end() + 1] + DOTENV + nuevo[m.end() + 1:]
        agrego_env = True
    if nuevo != txt:
        open(ruta, 'w', encoding='utf-8').write(nuevo)
    print(f'{nombre:<28} default={n1} literal={n2} DB_PASS={n3} WA={n4} dotenv={agrego_env}')

env = BASE + 'config/.env'
contenido = open(env, encoding='utf-8').read()
if not re.search(r'^WA_VERIFY_TOKEN=.+', contenido, re.M):
    sep = '' if contenido.endswith('\n') else '\n'
    open(env, 'a', encoding='utf-8').write(f'{sep}WA_VERIFY_TOKEN={secrets.token_urlsafe(24)}\n')
    print('config/.env: WA_VERIFY_TOKEN nuevo agregado (valor no impreso)')
else:
    print('config/.env: WA_VERIFY_TOKEN ya estaba')
