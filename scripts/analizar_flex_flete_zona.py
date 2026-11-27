#!/usr/bin/env python3
"""Solo lectura. Flex y Flete Propio de los últimos N meses completos (excluye canceladas):
% CABA vs AMBA (fuera de CABA) y cubicaje promedio por envío (m³, de alto×ancho×largo de
productos_base; los compuestos suman sus componentes).
Zona: Flete Propio usa zona_envio (Capital = CABA); si falta, y en Flex, la localidad que
va después de la última coma de direccion_entrega contra los 48 barrios de CABA.
Uso: venv/bin/python scripts/analizar_flex_flete_zona.py [MESES=4]
"""
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, '/home/cannon/app')
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import pymysql  # noqa: E402

BARRIOS = ['Agronomía', 'Almagro', 'Balvanera', 'Barracas', 'Belgrano', 'Boedo', 'Caballito', 'Chacarita',
           'Coghlan', 'Colegiales', 'Constitución', 'Flores', 'Floresta', 'La Boca', 'La Paternal', 'Liniers',
           'Mataderos', 'Monte Castro', 'Montserrat', 'Nueva Pompeya', 'Núñez', 'Palermo', 'Parque Avellaneda',
           'Parque Chacabuco', 'Parque Chas', 'Parque Patricios', 'Puerto Madero', 'Recoleta', 'Retiro',
           'Saavedra', 'San Cristóbal', 'San Nicolás', 'San Telmo', 'Vélez Sársfield', 'Versalles',
           'Villa Crespo', 'Villa del Parque', 'Villa Devoto', 'Villa General Mitre', 'Villa Lugano',
           'Villa Luro', 'Villa Ortúzar', 'Villa Pueyrredón', 'Villa Real', 'Villa Riachuelo',
           'Villa Santa Rita', 'Villa Soldati', 'Villa Urquiza']
ALIAS = ['Capital Federal', 'CABA', 'Ciudad Autonoma', 'Ciudad de Buenos Aires', 'Lugano', 'Pompeya', 'Paternal',
         'Boca', 'Monserrat', 'Soldati', 'Urquiza', 'Devoto', 'Velez Sarsfield', 'Barrio Norte', 'Once',
         'Abasto', 'Congreso', 'Microcentro', 'Tribunales', 'Palermo Soho', 'Palermo Hollywood', 'Las Canitas',
         'Belgrano R', 'Belgrano C', 'Villa Pueyrredon', 'Parque Centenario', 'Agronomia', 'Nunez',
         'Constitucion', 'San Cristobal', 'San Nicolas', 'Villa Ortuzar', 'Caballito Norte', 'Caballito Sur',
         'Cap Fed', 'Capital', 'C A B A', 'Cdad Autonoma De Buenos Aires', 'Capital Federal Caba',
         'Versailles', 'Santa Rita', 'Villa Gral Mitre', 'Nunes']


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', s).split()


CABA = {' '.join(norm(b)) for b in BARRIOS + ALIAS}


def es_caba(localidad):
    t = ' '.join(norm(localidad))
    return t in CABA or any(t.startswith(b + ' ') for b in CABA if len(b) > 5)


arg = sys.argv[1] if len(sys.argv) > 1 else '4'
hoy = date.today()
if arg.endswith('d'):  # "90d" = últimos N días corridos hasta ayer inclusive
    desde, hasta = hoy - timedelta(days=int(arg[:-1])), hoy
else:
    meses = int(arg)
    y, m = hoy.year, hoy.month - meses
    while m <= 0:
        m += 12
        y -= 1
    desde, hasta = date(y, m, 1), date(hoy.year, hoy.month, 1)
dias = (hasta - desde).days
dias_hab = sum(1 for i in range(dias) if (desde + timedelta(days=i)).weekday() < 5)  # lun-vie
meses = dias / 30.4

con = pymysql.connect(host=os.getenv('DB_HOST', 'localhost'), user=os.getenv('DB_USER'),
                      password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME', 'inventario_cannon'),
                      cursorclass=pymysql.cursors.DictCursor)
cur = con.cursor()
cur.execute("SELECT id, sku, tipo, alto_cm, ancho_cm, largo_cm FROM productos_base")
BASE = {r['sku'].upper(): r for r in cur.fetchall()}
BASE_ID = {r['id']: r for r in BASE.values()}
cur.execute("""SELECT pc.sku, c.producto_base_id, c.cantidad_necesaria FROM productos_compuestos pc
               JOIN componentes c ON c.producto_compuesto_id = pc.id""")
COMP = defaultdict(list)
for r in cur.fetchall():
    COMP[r['sku'].upper()].append((BASE_ID.get(r['producto_base_id']), int(r['cantidad_necesaria'] or 1)))


def vol_m3(b):
    if not b or not (b['alto_cm'] and b['ancho_cm'] and b['largo_cm']):
        return None
    return b['alto_cm'] * b['ancho_cm'] * b['largo_cm'] / 1e6


def vol_sku(sku):
    s = (sku or '').upper()
    for cand in (s, s.rstrip('Z+'), s[:-1] if s.endswith('Z') else s):
        if cand in BASE:
            return vol_m3(BASE[cand])
        if cand in COMP:
            vs = [vol_m3(b) for b, _ in COMP[cand]]
            if any(v is None for v in vs):
                return None
            return sum(v * q for v, (_, q) in zip(vs, COMP[cand]))
    return None


cur.execute("""SELECT v.id, v.metodo_envio met, v.zona_envio zona, v.direccion_entrega dir, v.canal,
                      iv.sku, iv.cantidad
               FROM ventas v LEFT JOIN items_venta iv ON iv.venta_id = v.id
               WHERE v.fecha_venta >= %s AND v.fecha_venta < %s AND v.metodo_envio IN ('Flex','Flete Propio')
                 AND IFNULL(v.estado_entrega,'') <> 'cancelada' AND IFNULL(v.estado,'') <> 'cancelada'""",
            (desde, hasta))
V = {}
for r in cur.fetchall():
    v = V.setdefault(r['id'], {'met': r['met'], 'zona': r['zona'] or '', 'dir': r['dir'] or '',
                               'canal': r['canal'], 'vol': 0.0, 'sin_medida': False, 'items': 0})
    if r['sku'] and r['sku'].upper() != 'FLETE':
        vv = vol_sku(r['sku'])
        if vv is None:
            v['sin_medida'] = True
        else:
            v['vol'] += vv * int(r['cantidad'] or 1)
        v['items'] += int(r['cantidad'] or 1)

agg = defaultdict(lambda: {'n': 0, 'vol': 0.0, 'nvol': 0})
no_caba = Counter()
sin_med = 0
for v in V.values():
    loc = v['dir'].rsplit(',', 1)[-1].strip() if ',' in v['dir'] else ''
    if v['met'] == 'Flete Propio' and v['zona']:
        zona = 'CABA' if v['zona'] == 'Capital' else 'AMBA'
    elif not loc:
        zona = 'sin dato'
    else:
        zona = 'CABA' if es_caba(loc) else 'AMBA'
        if zona == 'AMBA':
            no_caba[loc.title()] += 1
    for k in ((v['met'], zona), (v['met'], 'TOTAL')):
        a = agg[k]
        a['n'] += 1
        if not v['sin_medida'] and v['items']:
            a['vol'] += v['vol']
            a['nvol'] += 1
    sin_med += v['sin_medida']

print(f"{desde} a {hasta} (sin incluir {hasta}): {dias} días, {dias_hab} hábiles lun-vie. "
      f"Ventas sin medida completa (m³ estimado con el promedio del grupo): {sin_med}")
gran_tot = agg[('Flex', 'TOTAL')]['n'] + agg[('Flete Propio', 'TOTAL')]['n']
print(f"{'método':<13}{'zona':<10}{'envíos':>7}{'%met':>7}{'%tot':>7}{'env/día háb':>12}{'m³ prom':>9}"
      f"{'m³ total':>10}{'m³/día háb':>11}{'m³/día cal':>11}")
for met in ('Flex', 'Flete Propio'):
    tot = agg[(met, 'TOTAL')]['n']
    for z in ('CABA', 'AMBA', 'sin dato', 'TOTAL'):
        a = agg[(met, z)]
        if not a['n']:
            continue
        mv = a['vol'] / a['nvol'] if a['nvol'] else 0
        m3 = mv * a['n']
        print(f"{met:<13}{z:<10}{a['n']:>7}{100 * a['n'] / tot:>6.1f}%{100 * a['n'] / gran_tot:>6.1f}%"
              f"{a['n'] / dias_hab:>12.1f}{mv:>9.3f}{m3:>10.1f}{m3 / dias_hab:>11.2f}{m3 / dias:>11.2f}")
print('\nLocalidades contadas como AMBA (top 40, para revisar que no se cuele un barrio porteño):')
print(', '.join(f'{k} {n}' for k, n in no_caba.most_common(400)))
