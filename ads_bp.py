"""Plataformas vs nosotros: lo que Meta Ads y Google Ads se adjudican contra nuestras ventas.

- sincronizar(): baja de Windsor.ai (API, solo GET) gasto, clics y compras por día × campaña ×
  conjunto/grupo, y los clics de Google con su gclid. Reescribe los últimos N días.
- job_ads_diario(): lo mismo una vez por día (candado en configuracion + GET_LOCK, corre en 5 workers).
- /tienda/admin/atribucion/plataformas: comparación por plataforma, semana y campaña, ventas que
  reclaman las dos plataformas y alertas. Permiso: módulo "atribucion" (permisos.py).

Nuestro lado sale de tienda_bp._atribucion_datos (último contacto no directo y clics 7 días).
Los datos son confiables desde INICIO_VALIDO (registro de contactos + CAPI + fin de los Purchase
del Pixel en pagos rechazados).
"""
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

import pymysql
import requests
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

ads_bp = Blueprint('ads', __name__)

INICIO_VALIDO = date(2026, 11, 12)
DIAS_SYNC = 14
WINDSOR = 'https://connectors.windsor.ai/'
CAMPOS_META = ('date,campaign_id,campaign,adset_id,adset_name,ad_id,ad_name,impressions,actions_link_click,spend,'
               'actions_offsite_conversion_fb_pixel_purchase,action_values_offsite_conversion_fb_pixel_purchase')
CAMPOS_GOOGLE = 'date,campaign_id,campaign,ad_group_id,ad_group_name,impressions,clicks,spend,conversions,conversions_value'
CAMPOS_CLICS = 'date,click_view_gclid,campaign_id,campaign,ad_group_id,ad_group_name'
PLATAFORMAS = {'meta': ('Meta Ads', 'meta_clic_7d'), 'google': ('Google Ads', 'google_ads_7d')}


def _db():
    return pymysql.connect(host=os.environ.get('DB_HOST', 'localhost'), user=os.environ.get('DB_USER', 'cannon'),
                           password=os.environ.get('DB_PASSWORD', ''),
                           database=os.environ.get('DB_NAME', 'inventario_cannon'),
                           cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')


def _hoy_ar():
    return (datetime.utcnow() - timedelta(hours=3)).date()


def _windsor(conector, campos, desde, hasta):
    key = (os.getenv('WINDSOR_API_KEY') or '').strip()
    if not key:
        raise RuntimeError('falta WINDSOR_API_KEY en config/.env')
    try:
        r = requests.get(WINDSOR + conector, timeout=120,
                         params={'api_key': key, 'fields': campos, 'date_from': str(desde), 'date_to': str(hasta)})
    except requests.RequestException as e:
        raise RuntimeError(f'Windsor {conector}: error de red ({type(e).__name__})')  # sin la URL: lleva la key
    if r.status_code != 200:
        raise RuntimeError(f'Windsor {conector}: HTTP {r.status_code}')
    return r.json().get('data') or []


def _n(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _s(v, largo):
    return (str(v) if v is not None else '')[:largo]


def _guardar_estado(cur, estado):
    cur.execute("INSERT INTO configuracion (clave, valor) VALUES ('ads_sync_estado', %s) "
                "ON DUPLICATE KEY UPDATE valor=VALUES(valor)", (json.dumps(estado, ensure_ascii=False),))


def sincronizar(dias=DIAS_SYNC):
    """Baja y reescribe los últimos `dias` días. Devuelve un resumen (dict). Lanza si falla Windsor."""
    hasta = _hoy_ar()
    desde = hasta - timedelta(days=dias - 1)
    estado = {'ts': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), 'desde': str(desde), 'hasta': str(hasta)}
    try:
        meta = _windsor('facebook', CAMPOS_META, desde, hasta)
        google = _windsor('google_ads', CAMPOS_GOOGLE, desde, hasta)
        clics = _windsor('google_ads', CAMPOS_CLICS, desde, hasta)
    except Exception as e:
        estado.update(ok=False, error=str(e)[:300])
        db = _db()
        try:
            with db.cursor() as cur:
                _guardar_estado(cur, estado)
            db.commit()
        finally:
            db.close()
        raise

    filas = {}  # (fecha, plataforma, campana_id, grupo_id, anuncio_id) → dict

    def sumar(plat, f, grupo_id, grupo, clic, compras, valor, anuncio_id='', anuncio=''):
        k = (f.get('date'), plat, _s(f.get('campaign_id'), 40), _s(grupo_id, 40), _s(anuncio_id, 40))
        if not k[0] or not k[2]:
            return
        a = filas.setdefault(k, {'campana': _s(f.get('campaign'), 255), 'grupo': _s(grupo, 255), 'anuncio': _s(anuncio, 255),
                                 'imp': 0, 'clics': 0, 'gasto': 0.0, 'compras': 0.0, 'valor': 0.0})
        a['imp'] += int(_n(f.get('impressions'))); a['clics'] += int(_n(clic)); a['gasto'] += _n(f.get('spend'))
        a['compras'] += _n(compras); a['valor'] += _n(valor)

    for f in meta:
        sumar('meta', f, f.get('adset_id'), f.get('adset_name'), f.get('actions_link_click'),
              f.get('actions_offsite_conversion_fb_pixel_purchase'), f.get('action_values_offsite_conversion_fb_pixel_purchase'),
              f.get('ad_id'), f.get('ad_name'))
    for f in google:
        sumar('google', f, f.get('ad_group_id'), f.get('ad_group_name'), f.get('clicks'),
              f.get('conversions'), f.get('conversions_value'))

    db = _db()
    try:
        with db.cursor() as cur:
            for plat, datos in (('meta', meta), ('google', google)):
                cur.execute("DELETE FROM ads_metricas_diarias WHERE plataforma=%s AND fecha BETWEEN %s AND %s",
                            (plat, desde, hasta))
            cur.executemany(
                """INSERT INTO ads_metricas_diarias (fecha, plataforma, campana_id, campana, grupo_id, grupo,
                       anuncio_id, anuncio, impresiones, clics, gasto, compras, valor_compras)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [(k[0], k[1], k[2], a['campana'], k[3], a['grupo'], k[4], a['anuncio'], a['imp'], a['clics'], round(a['gasto'], 2),
                  round(a['compras'], 2), round(a['valor'], 2)) for k, a in filas.items()])
            g = [(_s(f.get('click_view_gclid'), 300), f.get('date'), _s(f.get('campaign_id'), 40), _s(f.get('campaign'), 255),
                  _s(f.get('ad_group_id'), 40), _s(f.get('ad_group_name'), 255))
                 for f in clics if f.get('click_view_gclid') and f.get('date')]
            if g:
                cur.executemany("""INSERT INTO ads_google_clics (gclid, fecha, campana_id, campana, grupo_id, grupo)
                                   VALUES (%s,%s,%s,%s,%s,%s)
                                   ON DUPLICATE KEY UPDATE fecha=VALUES(fecha), campana_id=VALUES(campana_id),
                                       campana=VALUES(campana), grupo_id=VALUES(grupo_id), grupo=VALUES(grupo)""", g)
            estado.update(ok=True, filas=len(filas), meta=len(meta), google=len(google), clics=len(g))
            _guardar_estado(cur, estado)
        db.commit()
    except Exception as e:
        db.rollback()
        estado.update(ok=False, error=f'DB: {e}'[:300])
        try:
            with db.cursor() as cur:
                _guardar_estado(cur, estado)
            db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
    return estado


def job_ads_diario():
    """Una sola vez por día entre los 5 workers: candado en configuracion['ads_sync_dia']."""
    hoy = str(_hoy_ar())
    try:
        db = _db()
        try:
            with db.cursor() as cur:
                cur.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('ads_sync_dia', '')")
                cur.execute("UPDATE configuracion SET valor=%s WHERE clave='ads_sync_dia' AND valor<>%s", (hoy, hoy))
                tomado = cur.rowcount == 1
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f'[ADS] error tomando el candado: {e}', flush=True)
        return
    if not tomado:
        return
    try:
        r = sincronizar()
        print(f"[ADS] sincronizado: {r.get('filas')} filas, {r.get('clics')} clics de Google", flush=True)
    except Exception as e:
        print(f'[ADS] error sincronizando: {e}', flush=True)


# ─────────────────────────── Comparación ───────────────────────────

def _lunes(d):
    return d - timedelta(days=d.weekday())


def _vacio():
    return {'gasto': 0.0, 'imp': 0, 'clics': 0, 'compras': 0.0, 'valor': 0.0,
            'ult_n': 0, 'ult_v': 0.0, 'c7_n': 0, 'c7_v': 0.0}


def _derivar(a):
    a['cpc'] = a['gasto'] / a['clics'] if a['clics'] else None
    a['ctr'] = 100.0 * a['clics'] / a['imp'] if a['imp'] else None
    a['roas_plat'] = a['valor'] / a['gasto'] if a['gasto'] else None
    a['roas_real'] = a['ult_v'] / a['gasto'] if a['gasto'] else None
    a['cpa_real'] = a['gasto'] / a['ult_n'] if a['ult_n'] else None
    base = max(a['c7_n'], a['ult_n'])
    a['veces'] = a['compras'] / base if base else None
    return a


def comparar(desde, hasta):
    import tienda_bp as T
    db = _db()
    try:
        with db.cursor() as cur:
            cur.execute("""SELECT * FROM ads_metricas_diarias WHERE fecha BETWEEN %s AND %s""", (desde, hasta))
            plat_rows = cur.fetchall()
            cur.execute("SELECT valor FROM configuracion WHERE clave='ads_sync_estado'")
            r = cur.fetchone()
            estado = json.loads(r['valor']) if r and r['valor'] else None
    finally:
        db.close()
    ventas, _, _ = T._atribucion_datos(desde, hasta)
    ventas = [v for v in ventas if not v['cancelada']]

    gclids = sorted({v['google_gclid'] for v in ventas if v.get('google_gclid')})
    camp_gclid = {}
    if gclids:
        db = _db()
        try:
            with db.cursor() as cur:
                cur.execute(f"SELECT gclid, campana_id, campana, grupo_id, grupo FROM ads_google_clics WHERE gclid IN ({','.join(['%s'] * len(gclids))})",
                            gclids)
                camp_gclid = {x['gclid']: x for x in cur.fetchall()}
        finally:
            db.close()

    total = {p: _vacio() for p in PLATAFORMAS}
    semanas = defaultdict(lambda: {p: _vacio() for p in PLATAFORMAS})
    campanas = {}
    anuncios = {}  # Meta: por anuncio; Google: por grupo de anuncios
    nombres = {}
    meta_sin_valor = defaultdict(float)

    def camp(p, cid, nombre=''):
        a = campanas.setdefault((p, cid), dict(_vacio(), plataforma=p, campana_id=cid, campana=nombre, ventas=[]))
        if nombre and not a['campana']:
            a['campana'] = nombre
        return a

    def anun(p, cid, gid, aid, campana='', grupo='', anuncio=''):
        a = anuncios.setdefault((p, cid, gid, aid), dict(_vacio(), plataforma=p, campana_id=cid, grupo_id=gid, anuncio_id=aid,
                                                         campana=campana, grupo=grupo, anuncio=anuncio, ventas=[]))
        for k, v in (('campana', campana), ('grupo', grupo), ('anuncio', anuncio)):
            if v and not a[k]:
                a[k] = v
        return a

    for r in plat_rows:
        p = r['plataforma']
        if p not in total:
            continue
        nombres[(p, r['campana_id'])] = r['campana']
        clave_a = (p, r['campana_id'], r['grupo_id'] or '', r.get('anuncio_id') or '')
        nombres[clave_a] = (r['grupo'], r.get('anuncio'))
        for a in (total[p], semanas[_lunes(r['fecha'])][p], camp(p, r['campana_id'], r['campana']),
                  anun(*clave_a, r['campana'], r['grupo'], r.get('anuncio'))):
            a['gasto'] += float(r['gasto']); a['clics'] += r['clics']; a['imp'] += r['impresiones']
            a['compras'] += float(r['compras']); a['valor'] += float(r['valor_compras'])
        if p == 'meta' and float(r['compras']) > 0 and float(r['valor_compras']) == 0:
            meta_sin_valor[r['fecha']] += float(r['compras'])

    ambas = []
    for v in ventas:
        dia = datetime.strptime(v['dia'], '%Y-%m-%d').date()
        for p, (canal, clave7) in PLATAFORMAS.items():
            ult = v['canal_ultimo'] == canal
            c7 = bool(v.get(clave7))
            if not (ult or c7):
                continue
            if p == 'meta':
                cid = v.get('meta_campana') or '(sin identificar)'
                gid, aid = (v.get('meta_adset') or '', v.get('meta_ad') or '') if v.get('meta_campana') else ('', '')
            else:
                gc = camp_gclid.get(v.get('google_gclid')) or {}
                cid = gc.get('campana_id') or '(sin identificar)'
                gid, aid = gc.get('grupo_id') or '', ''
            g_n, a_n = nombres.get((p, cid, gid, aid)) or ('', '')
            for a in (total[p], semanas[_lunes(dia)][p], camp(p, cid, nombres.get((p, cid), '')),
                      anun(p, cid, gid, aid, nombres.get((p, cid), ''), g_n, a_n)):
                if ult:
                    a['ult_n'] += 1; a['ult_v'] += v['importe']
                if c7:
                    a['c7_n'] += 1; a['c7_v'] += v['importe']
            camp(p, cid)['ventas'].append(v['numero_venta'])
            anun(p, cid, gid, aid)['ventas'].append(v['numero_venta'])
        if v.get('meta_clic_7d') and v.get('google_ads_7d'):
            ambas.append(v)

    for a in (list(total.values()) + [x for s in semanas.values() for x in s.values()] + list(campanas.values())
              + list(anuncios.values())):
        _derivar(a)

    alertas = []
    if not estado:
        alertas.append(('danger', 'Todavía no se sincronizó nunca con Windsor.'))
    else:
        if not estado.get('ok'):
            alertas.append(('danger', f"La última sincronización falló: {estado.get('error')}"))
        try:
            hace = (datetime.utcnow() - datetime.strptime(estado['ts'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            if hace > 36:
                alertas.append(('warning', f'Los datos de las plataformas tienen {hace:.0f} horas.'))
        except Exception:
            pass
    for lunes in sorted(semanas):
        for p, a in semanas[lunes].items():
            base = max(a['c7_n'], a['ult_n'])
            if a['compras'] >= 2 and a['compras'] > 2 * max(base, 0.5):
                alertas.append(('warning', f"Semana del {lunes:%d/%m}: {PLATAFORMAS[p][0]} se adjudica "
                                           f"{a['compras']:.1f} compras y nosotros le vemos {base}."))
    if meta_sin_valor:
        dias = ', '.join(f'{d:%d/%m} ({n:.0f})' for d, n in sorted(meta_sin_valor.items()))
        alertas.append(('warning', f'Meta registró compras con valor $0: {dias}. Suele ser un Purchase del Pixel mal disparado.'))
    for a in campanas.values():
        if a['gasto'] >= 50000 and a['ult_n'] == 0 and a['c7_n'] == 0:
            alertas.append(('info', f"{PLATAFORMAS[a['plataforma']][0]} · {a['campana'] or a['campana_id']}: "
                                    f"${a['gasto']:,.0f} de gasto sin ventas nuestras en el período.".replace(',', '.')))

    return {
        'total': total,
        'semanas': [(l, semanas[l]) for l in sorted(semanas)],
        'campanas': sorted(campanas.values(), key=lambda a: (a['plataforma'], -a['gasto'])),
        'anuncios': sorted((a for a in anuncios.values() if a['gasto'] or a['ult_n'] or a['c7_n']),
                           key=lambda a: (a['plataforma'], a['campana'] or '', -a['gasto'])),
        'ambas': ambas,
        'alertas': alertas,
        'estado': estado,
        'n_ventas': len(ventas),
        'v_ventas': sum(v['importe'] for v in ventas),
    }


def _pesos(x):
    return '—' if x is None else '$' + f'{x:,.0f}'.replace(',', '.')


@ads_bp.route('/tienda/admin/atribucion/plataformas')
@login_required
def plataformas():
    hoy = _hoy_ar()
    try:
        hasta = datetime.strptime(request.args.get('hasta', ''), '%Y-%m-%d').date()
    except ValueError:
        hasta = hoy - timedelta(days=1)
    try:
        desde = datetime.strptime(request.args.get('desde', ''), '%Y-%m-%d').date()
    except ValueError:
        desde = hasta - timedelta(days=27)
    desde = max(desde, INICIO_VALIDO)
    hasta = max(hasta, desde)
    error = None
    try:
        datos = comparar(desde, hasta)
    except pymysql.err.ProgrammingError as e:
        datos, error = None, f'Faltan las tablas (migración 022): {e}'
    return render_template('ads_plataformas.html', d=datos, error=error, desde=desde, hasta=hasta,
                           inicio=INICIO_VALIDO, nombres=PLATAFORMAS, pesos=_pesos)


@ads_bp.route('/tienda/admin/atribucion/plataformas/actualizar', methods=['POST'])
@login_required
def plataformas_actualizar():
    try:
        r = sincronizar()
        flash(f"Datos actualizados: {r.get('filas')} filas de campañas y {r.get('clics')} clics de Google.", 'success')
    except Exception as e:
        flash(f'No se pudo actualizar: {e}', 'error')
    return redirect(url_for('ads.plataformas', desde=request.form.get('desde') or None,
                            hasta=request.form.get('hasta') or None))
