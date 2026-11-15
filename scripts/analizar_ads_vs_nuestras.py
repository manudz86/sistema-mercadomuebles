#!/usr/bin/env python3
"""Compara, por día, lo que Meta y Google Ads se adjudican (vía Windsor, GET) contra las ventas
de la tienda y nuestra atribución (tienda_bp._atribucion_datos). Solo lectura, sin datos personales.

Uso: venv/bin/python scripts/analizar_ads_vs_nuestras.py 2026-11-08 2026-11-14
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402

desde, hasta = sys.argv[1], sys.argv[2]
KEY = os.getenv('WINDSOR_API_KEY', '').strip()


def windsor(conector, campos):
    r = requests.get(f'https://connectors.windsor.ai/{conector}', timeout=90,
                     params={'api_key': KEY, 'fields': campos, 'date_from': desde, 'date_to': hasta})
    r.raise_for_status()
    return r.json().get('data') or []


plat = defaultdict(lambda: defaultdict(float))
for f in windsor('facebook', 'date,spend,actions_offsite_conversion_fb_pixel_purchase,'
                             'action_values_offsite_conversion_fb_pixel_purchase'):
    d = plat[f['date']]
    d['meta_gasto'] += f.get('spend') or 0
    d['meta_n'] += f.get('actions_offsite_conversion_fb_pixel_purchase') or 0
    d['meta_v'] += f.get('action_values_offsite_conversion_fb_pixel_purchase') or 0
for f in windsor('google_ads', 'date,spend,conversions,conversions_value'):
    d = plat[f['date']]
    d['g_gasto'] += f.get('spend') or 0
    d['g_n'] += f.get('conversions') or 0
    d['g_v'] += f.get('conversions_value') or 0

with A.app.app_context():
    filas, _, ok = T._atribucion_datos(desde, hasta)
nos = defaultdict(lambda: defaultdict(float))
canales = defaultdict(lambda: defaultdict(int))
for f in filas:
    if f['cancelada']:
        continue
    d = nos[f['dia']]
    d['n'] += 1; d['v'] += f['importe']
    canales[f['dia']][f['canal_ultimo']] += 1
    if f['meta_clic_7d']:
        d['meta7_n'] += 1; d['meta7_v'] += f['importe']
    if f['google_ads_7d']:
        d['g7_n'] += 1; d['g7_v'] += f['importe']
    if f['canal_ultimo'] == 'Meta Ads':
        d['meta_ult_n'] += 1; d['meta_ult_v'] += f['importe']
    if f['canal_ultimo'] == 'Google Ads':
        d['g_ult_n'] += 1; d['g_ult_v'] += f['importe']


def m(x):
    return f'{x / 1000:,.0f}k'.replace(',', '.')


print(f'tablas de atribución OK: {ok} | ventas tienda no canceladas: {sum(int(v["n"]) for v in nos.values())}\n')
print(f'{"día":<11}{"tienda":>13} | {"META dice":>14}{"clic7d nuestro":>16}{"último nuestro":>16}{"gasto":>9}'
      f' | {"GOOGLE dice":>14}{"clic7d nuestro":>16}{"último nuestro":>16}{"gasto":>9}')
tot = defaultdict(float)
for dia in sorted(set(plat) | set(nos)):
    p, n = plat[dia], nos[dia]
    for k, v in list(p.items()) + [('t_' + k, v) for k, v in n.items()]:
        tot[k] += v
    print(f'{dia:<11}{int(n["n"]):>3} {m(n["v"]):>9} | {p["meta_n"]:>4.0f} {m(p["meta_v"]):>9}'
          f'{int(n["meta7_n"]):>6} {m(n["meta7_v"]):>9}{int(n["meta_ult_n"]):>6} {m(n["meta_ult_v"]):>9}{m(p["meta_gasto"]):>9}'
          f' | {p["g_n"]:>4.1f} {m(p["g_v"]):>9}{int(n["g7_n"]):>6} {m(n["g7_v"]):>9}{int(n["g_ult_n"]):>6} {m(n["g_ult_v"]):>9}{m(p["g_gasto"]):>9}')
print(f'{"TOTAL":<11}{int(tot["t_n"]):>3} {m(tot["t_v"]):>9} | {tot["meta_n"]:>4.0f} {m(tot["meta_v"]):>9}'
      f'{int(tot["t_meta7_n"]):>6} {m(tot["t_meta7_v"]):>9}{int(tot["t_meta_ult_n"]):>6} {m(tot["t_meta_ult_v"]):>9}{m(tot["meta_gasto"]):>9}'
      f' | {tot["g_n"]:>4.1f} {m(tot["g_v"]):>9}{int(tot["t_g7_n"]):>6} {m(tot["t_g7_v"]):>9}{int(tot["t_g_ult_n"]):>6} {m(tot["t_g_ult_v"]):>9}{m(tot["g_gasto"]):>9}')
print('\nCanal (último no directo) por día:')
for dia in sorted(canales):
    print(f'  {dia}: ' + ', '.join(f'{k} {v}' for k, v in sorted(canales[dia].items(), key=lambda x: -x[1])))
