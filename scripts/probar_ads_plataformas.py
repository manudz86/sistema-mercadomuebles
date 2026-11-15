#!/usr/bin/env python3
"""Prueba ads_bp de punta a punta SIN escribir en la base: las tablas nuevas se simulan en memoria
(se bajan datos reales de Windsor con GET; nuestras ventas se leen de la base real, solo SELECT).

1. sincronizar() con DB simulada → cuántas filas/clics guardaría.
2. comparar() desde el 12/11 → totales, semanas, campañas, alertas, ventas en ambas.
3. Render de la página como admin; permisos: vendedor/viewer/agencia sin acceso.
Uso: venv/bin/python scripts/probar_ads_plataformas.py
"""
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402
import ads_bp as B  # noqa: E402

MEM = {'metricas': [], 'clics': {}, 'estado': None}


class Cur:
    def __init__(self):
        self.res, self.rowcount = [], 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def execute(self, sql, p=()):
        s = ' '.join(sql.split())
        if s.startswith('DELETE FROM ads_metricas_diarias'):
            MEM['metricas'] = [r for r in MEM['metricas'] if not (r['plataforma'] == p[0] and p[1] <= r['fecha'] <= p[2])]
        elif "ads_sync_estado" in s and s.startswith('INSERT'):
            MEM['estado'] = p[0]
        elif s.startswith('SELECT * FROM ads_metricas_diarias'):
            self.res = [r for r in MEM['metricas'] if p[0] <= r['fecha'] <= p[1]]
        elif "clave='ads_sync_estado'" in s:
            self.res = [{'valor': MEM['estado']}] if MEM['estado'] else []
        elif s.startswith('SELECT gclid'):
            self.res = [MEM['clics'][g] for g in p if g in MEM['clics']]
        else:
            raise AssertionError('SQL no esperado: ' + s[:80])

    def executemany(self, sql, filas):
        if 'ads_metricas_diarias' in sql:
            for f in filas:
                MEM['metricas'].append(dict(zip(['fecha', 'plataforma', 'campana_id', 'campana', 'grupo_id', 'grupo', 'impresiones',
                                                 'clics', 'gasto', 'compras', 'valor_compras'], f)))
                MEM['metricas'][-1]['fecha'] = datetime.strptime(f[0], '%Y-%m-%d').date()
        else:
            for f in filas:
                MEM['clics'][f[0]] = {'gclid': f[0], 'campana_id': f[2], 'campana': f[3]}

    def fetchall(self):
        return self.res

    def fetchone(self):
        return self.res[0] if self.res else None


class Conn:
    def cursor(self):
        return Cur()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


B._db = lambda: Conn()
fallas = 0


def chequear(ok, txt):
    global fallas
    fallas += not ok
    print(('OK    ' if ok else 'FALLA ') + txt)


r = B.sincronizar()
chequear(r.get('ok') and r['filas'] > 0, f"sincronizar: {r.get('filas')} filas (meta {r.get('meta')}, google {r.get('google')}), {r.get('clics')} clics")

hasta = B._hoy_ar() - timedelta(days=1)
with A.app.app_context():
    d = B.comparar(B.INICIO_VALIDO, hasta)
print(f"\nventas tienda {B.INICIO_VALIDO}..{hasta}: {d['n_ventas']} por {B._pesos(d['v_ventas'])}")
for p, a in d['total'].items():
    print(f"  {p:<7} gasto {B._pesos(a['gasto'])} | dice {a['compras']:.1f} / {B._pesos(a['valor'])} | nuestras {a['ult_n']} / "
          f"{B._pesos(a['ult_v'])} | clic7d {a['c7_n']} | ROAS dice {a['roas_plat'] or 0:.1f} real {a['roas_real'] or 0:.1f} | "
          f"costo/venta {B._pesos(a['cpa_real'])}")
print('campañas:')
for a in d['campanas']:
    print(f"  {a['plataforma']:<7} {(a['campana'] or '')[:45]:<45} gasto {B._pesos(a['gasto']):>10} dice {a['compras']:>4.1f} "
          f"nuestras {a['ult_n']} clic7d {a['c7_n']}")
print(f"ventas con clic en ambas: {len(d['ambas'])}")
print('alertas:')
for n, t in d['alertas']:
    print(f'  [{n}] {t}')
g_c7 = d['total']['google']['c7_n']
sin_id = sum(a['c7_n'] for a in d['campanas'] if a['plataforma'] == 'google' and a['campana_id'] == '(sin identificar)')
chequear(g_c7 == 0 or sin_id < g_c7, f'gclid → campaña de Google: {g_c7 - sin_id} de {g_c7} identificadas')

A.app.config['TESTING'] = True
A.login_manager.request_loader(
    lambda req: A.load_user(req.headers['X-Test-User']) if req.headers.get('X-Test-User') else None)
c = A.app.test_client()
resp = c.get('/tienda/admin/atribucion/plataformas', headers={'X-Test-User': '1'})
html = resp.get_data(as_text=True)
chequear(resp.status_code == 200 and 'Total del período' in html and 'Por campaña' in html, f'página admin → {resp.status_code}')
for rol, uid in (('vendedor', 2), ('viewer', 3), ('agencia', 4)):
    resp = c.get('/tienda/admin/atribucion/plataformas', headers={'X-Test-User': str(uid)})
    chequear(resp.status_code in (302, 403), f'página {rol} → {resp.status_code}')
    resp = c.post('/tienda/admin/atribucion/plataformas/actualizar', json={}, headers={'X-Test-User': str(uid)})
    chequear(resp.status_code == 403, f'actualizar {rol} → {resp.status_code}')
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
