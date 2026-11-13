"""Zipnova: recolecciones (mail + PDF), estado de envíos (API) y mensajes de ML sin leer.

- Recolecciones: lee la casilla (IMAP, solo lectura) y toma
    · "Nueva recolección de ZIPNOVA programada para el dd/mm/aa" → PDF adjunto (PICKUP #, envíos, bultos)
    · "Resumen de recolecciones del día dd/mm/aaaa" → qué envíos se llevaron efectivamente
  Los mails NO se marcan como leídos ni se mueven (select readonly + BODY.PEEK).
- Envíos: GET /shipments de Zipnova → estado, guía y links de seguimiento, enlazados a la venta
  (web: external_id = numero_venta; ML: external_id = id de envío de ML → orden vía API de ML).
- Mensajes ML: GET /messages/unread → órdenes con mensajes del comprador sin leer (puntito rojo).

Los jobs corren en los 5 workers: cada uno toma un GET_LOCK y respeta un intervalo mínimo
guardado en zipnova_jobs, así trabaja uno solo por vez.
"""
import email
import imaplib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

import requests
from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

zipnova_bp = Blueprint('zipnova', __name__)

ZN_BASE = 'https://api.zipnova.com.ar/v2'
ZN_PANEL_URL = 'https://app.zipnova.com.ar/shipments/{id}'
ML_API = 'https://api.mercadolibre.com'
ML_SELLER_ID = 29563319
PDF_DIR = '/home/cannon/app/data/zipnova_recolecciones'
ESTADOS_FINALES = ('delivered', 'cancelled', 'returned', 'expired')


# ─────────────────────────── utilidades ───────────────────────────

def _db():
    from app import query_db, query_one, execute_db, get_db_connection
    return query_db, query_one, execute_db, get_db_connection


def _zn_auth():
    return (os.getenv('ZIPNOVA_API_KEY', ''), os.getenv('ZIPNOVA_API_SECRET', ''))


def _utc_naive(txt):
    """'2026-11-11T18:04:06+0000' / '+00:00' / 'Z' → datetime UTC sin tz (o None)."""
    if not txt:
        return None
    try:
        s = str(txt).strip().replace('Z', '+00:00')
        s = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', s)
        d = datetime.fromisoformat(s)
        if d.tzinfo:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d
    except Exception:
        return None


def _con_lock(job, minimo_seg, fn):
    """Corre fn() si ningún otro worker la está corriendo y pasó el intervalo mínimo desde la
    última corrida. Devuelve el resultado de fn() o None si se salteó."""
    _, _, _, get_conn = _db()
    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT GET_LOCK(%s, 0) AS l", (f'zn_job_{job}',))
            if not (c.fetchone() or {}).get('l'):
                return None
        try:
            with conn.cursor() as c:
                c.execute("SELECT ultimo FROM zipnova_jobs WHERE job=%s", (job,))
                r = c.fetchone()
            if minimo_seg and r and r['ultimo'] and (datetime.utcnow() - r['ultimo']).total_seconds() < minimo_seg:
                return None
            try:
                res = fn()
                txt = str(res)[:500]
            except Exception as e:
                res, txt = None, f'ERROR: {e}'[:500]
                print(f'[ZIPNOVA] job {job} error: {e}', flush=True)
            with conn.cursor() as c:
                c.execute("INSERT INTO zipnova_jobs (job, ultimo, resultado) VALUES (%s, UTC_TIMESTAMP(), %s) "
                          "ON DUPLICATE KEY UPDATE ultimo=VALUES(ultimo), resultado=VALUES(resultado)", (job, txt))
            conn.commit()
            return res
        finally:
            with conn.cursor() as c:
                c.execute("SELECT RELEASE_LOCK(%s)", (f'zn_job_{job}',))
    finally:
        conn.close()


# ─────────────────────────── PDF de recolección ───────────────────────────

def parsear_pdf_recoleccion(ruta):
    """Lee el PDF de Zipnova. Devuelve dict con pickup_id, fecha_retiro, origen, generado_at,
    totales y envios=[{orden, external_id, guia, bultos, kg, detalle}]. No toma nombres ni
    direcciones."""
    from pypdf import PdfReader
    texto = '\n'.join((p.extract_text() or '') for p in PdfReader(ruta).pages)
    return parsear_texto_recoleccion(texto)


def parsear_texto_recoleccion(texto):
    t = texto.replace('\xa0', ' ')
    out = {'texto_ok': False, 'envios': []}
    m = re.search(r'PICKUP\s*#\s*(\d+)', t)
    if m:
        out['pickup_id'] = int(m.group(1))
    m = re.search(r'Recolecci[oó]n a (.+?) del (\d{2})/(\d{2})/(\d{2,4})', t)
    if m:
        out['origen'] = m.group(1).strip()
        a = int(m.group(4))
        out['fecha_retiro'] = date(a + 2000 if a < 100 else a, int(m.group(3)), int(m.group(2)))
    m = re.search(r'GENERADO EL (\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})', t)
    if m:
        out['generado_at'] = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)), int(m.group(5)))
    m = re.search(r'TOTALES:\s*(\d+)\s*ENV[IÍ]OS\s*\|\s*(\d+)\s*BULTOS\s*\|\s*([\d.,]+)\s*kg\s*\|\s*([\d.,]+)\s*m', t, re.I)
    if m:
        out['total_envios'] = int(m.group(1))
        out['total_bultos'] = int(m.group(2))
        out['total_kg'] = float(m.group(3).replace(',', '.'))
        out['total_m3'] = float(m.group(4).replace(',', '.'))
    # Filas: "<n> <id seller> <guía 0999-xxxxxxxx>" (la guía puede venir partida por la negrita)
    filas = list(re.finditer(r'(?m)^\s*(\d{1,3})\s+(\S{5,40}?)\s+(\d{4}-\d[\d ]*\d)\s*$', t))
    if not filas:
        filas = list(re.finditer(r'(?m)^\s*(\d{1,3})\s+(\S{5,40}?)\s+(\d{4}-\d[\d ]*\d)\b', t))
    fin_tabla = t.find('PICKUP #')
    for i, f in enumerate(filas):
        ini = f.end()
        fin = filas[i + 1].start() if i + 1 < len(filas) else (fin_tabla if fin_tabla > ini else len(t))
        bloque = t[ini:fin]
        e = {'orden': int(f.group(1)), 'external_id': f.group(2).strip(),
             'guia': re.sub(r'\s+', '', f.group(3))}
        mb = re.search(r'(\d+)\s*bultos?', bloque, re.I)
        e['bultos'] = int(mb.group(1)) if mb else None
        mk = re.search(r'([\d.,]+)\s*kg', bloque, re.I)
        e['kg'] = float(mk.group(1).replace(',', '.')) if mk else None
        skus = re.findall(r'(?:Bulto\s*\d+:\s*)?([A-Z0-9][A-Z0-9_\-]{2,})\s*\((\d+)\)', bloque)
        e['detalle'] = ', '.join(f'{s} x{c}' for s, c in skus)[:500]
        out['envios'].append(e)
    out['texto_ok'] = bool(out.get('pickup_id') and out.get('fecha_retiro') and out['envios'])
    return out


def parsear_resumen(texto):
    """Cuerpo del mail 'Resumen de recolecciones del día'. Devuelve (fecha, recolectados, no_recolectados)."""
    t = re.sub(r'\s+', ' ', texto)
    m = re.search(r'recolecciones del d[ií]a (\d{2})/(\d{2})/(\d{4})', t, re.I)
    fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    patron = r'Env[ií]o\s+(\S+?)\s*-\s*Gu[ií]a\s+(\d{4}-\d+)'
    idx_no = None
    mn = re.search(r'Env[ií]os? no recolectados', t, re.I)
    if mn:
        idx_no = mn.start()
    rec, norec = [], []
    for x in re.finditer(patron, t, re.I):
        item = {'external_id': x.group(1).rstrip('.'), 'guia': x.group(2)}
        (norec if idx_no is not None and x.start() > idx_no else rec).append(item)
    return fecha, rec, norec


def _html_a_texto(html):
    import html as _h
    t = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    return _h.unescape(re.sub(r'<[^>]+>', ' ', t))


def _cuerpo_texto(msg):
    for parte in msg.walk():
        if parte.get_content_type() in ('text/plain', 'text/html'):
            raw = parte.get_payload(decode=True) or b''
            t = raw.decode(parte.get_content_charset() or 'utf-8', 'replace')
            if parte.get_content_type() == 'text/html' or '<html' in t.lower():
                t = _html_a_texto(t)
            return t
    return ''


# ─────────────────────────── job: mails ───────────────────────────

def sync_mails(dias=10):
    """Lee la casilla y registra recolecciones nuevas y resúmenes. Idempotente."""
    host = os.getenv('ZIPNOVA_IMAP_HOST', 'imap.hostinger.com')
    user, pwd = os.getenv('ZIPNOVA_IMAP_USER', ''), os.getenv('ZIPNOVA_IMAP_PASS', '')
    if not user or not pwd:
        return 'sin credenciales IMAP'
    query_db, query_one, execute_db, _ = _db()
    ya = {r['mail_message_id'] for r in query_db(
        "SELECT mail_message_id FROM zipnova_recolecciones WHERE mail_message_id IS NOT NULL "
        "UNION SELECT mail_message_id FROM zipnova_resumenes WHERE mail_message_id IS NOT NULL")}
    os.makedirs(PDF_DIR, exist_ok=True)
    nuevas, resumenes, errores = 0, 0, []
    desde = (date.today() - timedelta(days=dias)).strftime('%d-%b-%Y')
    M = imaplib.IMAP4_SSL(host, 993, timeout=60)
    try:
        M.login(user, pwd)
        M.select('INBOX', readonly=True)
        typ, data = M.search(None, 'FROM', '"zipnova.app"', 'SINCE', desde)
        for num in (data[0] or b'').split():
            typ, hd = M.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT MESSAGE-ID DATE)])')
            h = email.message_from_bytes(hd[0][1])
            asunto = str(make_header(decode_header(h.get('Subject', ''))))
            mid = (h.get('Message-ID') or '').strip()[:255]
            es_reco = 'nueva recolecci' in asunto.lower()
            es_res = 'resumen de recolecciones' in asunto.lower()
            if not (es_reco or es_res) or (mid and mid in ya):
                continue
            try:
                recibido = parsedate_to_datetime(h.get('Date')).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                recibido = None
            typ, full = M.fetch(num, '(BODY.PEEK[])')
            msg = email.message_from_bytes(full[0][1])
            try:
                if es_reco:
                    nuevas += _registrar_recoleccion(msg, mid, recibido)
                else:
                    resumenes += _registrar_resumen(msg, mid, recibido)
            except Exception as e:
                errores.append(f'{asunto[:60]}: {e}')
                print(f'[ZIPNOVA] mail {asunto!r}: {e}', flush=True)
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return f'recolecciones nuevas={nuevas} resúmenes={resumenes}' + (f' errores={errores}' if errores else '')


def _registrar_recoleccion(msg, mid, recibido):
    _, query_one, execute_db, get_conn = _db()
    for parte in msg.walk():
        fn = parte.get_filename()
        if not fn:
            continue
        fn = str(make_header(decode_header(fn)))
        if not fn.lower().endswith('.pdf'):
            continue
        datos_pdf = parte.get_payload(decode=True)
        tmp = os.path.join(PDF_DIR, f'_tmp_{os.getpid()}.pdf')
        with open(tmp, 'wb') as fh:
            fh.write(datos_pdf)
        d = parsear_pdf_recoleccion(tmp)
        if not d['texto_ok']:
            os.remove(tmp)
            raise ValueError(f'no se pudo leer el PDF {fn}')
        destino = os.path.join(PDF_DIR, f"pickup_{d['pickup_id']}.pdf")
        os.replace(tmp, destino)
        conn = get_conn()
        try:
            with conn.cursor() as c:
                c.execute("""INSERT INTO zipnova_recolecciones (pickup_id, fecha_retiro, origen, generado_at,
                             mail_message_id, mail_recibido_at, pdf_archivo, total_envios, total_bultos, total_kg, total_m3)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                             ON DUPLICATE KEY UPDATE fecha_retiro=VALUES(fecha_retiro), origen=VALUES(origen),
                               generado_at=VALUES(generado_at), mail_message_id=VALUES(mail_message_id),
                               mail_recibido_at=VALUES(mail_recibido_at), pdf_archivo=VALUES(pdf_archivo),
                               total_envios=VALUES(total_envios), total_bultos=VALUES(total_bultos),
                               total_kg=VALUES(total_kg), total_m3=VALUES(total_m3)""",
                          (d['pickup_id'], d['fecha_retiro'], d.get('origen'), d.get('generado_at'), mid or None,
                           recibido, os.path.basename(destino), d.get('total_envios'), d.get('total_bultos'),
                           d.get('total_kg'), d.get('total_m3')))
                c.execute("DELETE FROM zipnova_recoleccion_envios WHERE pickup_id=%s", (d['pickup_id'],))
                for e in d['envios']:
                    c.execute("""INSERT INTO zipnova_recoleccion_envios (pickup_id, external_id, guia, orden, bultos, kg, detalle)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                              (d['pickup_id'], e['external_id'], e['guia'], e['orden'], e['bultos'], e['kg'], e['detalle']))
            conn.commit()
        finally:
            conn.close()
        return 1
    return 0


def _registrar_resumen(msg, mid, recibido):
    _, _, execute_db, _ = _db()
    texto = re.sub(r'\s+', ' ', _cuerpo_texto(msg)).strip()
    fecha, rec, norec = parsear_resumen(texto)
    if not fecha:
        raise ValueError('resumen sin fecha')
    execute_db("""INSERT INTO zipnova_resumenes (fecha, mail_message_id, mail_recibido_at, recolectados, no_recolectados, texto)
                  VALUES (%s,%s,%s,%s,%s,%s)
                  ON DUPLICATE KEY UPDATE mail_message_id=VALUES(mail_message_id), mail_recibido_at=VALUES(mail_recibido_at),
                    recolectados=VALUES(recolectados), no_recolectados=VALUES(no_recolectados), texto=VALUES(texto)""",
               (fecha, mid or None, recibido, json.dumps(rec), json.dumps(norec), texto[:6000]))
    return 1


# ─────────────────────────── job: envíos Zipnova ───────────────────────────

def _ml_token():
    from app import cargar_ml_token
    return cargar_ml_token()


def _ml_get(path, tok, params=None):
    r = requests.get(ML_API + path, headers={'Authorization': f'Bearer {tok}'}, params=params, timeout=20)
    return r.json() if r.status_code in (200, 206) else None


def sync_envios(desde=None, max_resolver=150):
    """Trae los envíos de Zipnova desde `desde` (default: últimos 45 días) y los enlaza a ventas."""
    query_db, query_one, execute_db, get_conn = _db()
    desde = desde or (date.today() - timedelta(days=45)).isoformat()
    previos = {r['zipnova_id']: r for r in query_db("SELECT zipnova_id, status, carrier FROM zipnova_envios")}
    envios, page = [], 1
    while page <= 60:
        r = requests.get(f'{ZN_BASE}/shipments', auth=_zn_auth(), timeout=30,
                         params={'account_id': os.getenv('ZIPNOVA_ACCOUNT_ID', '5786'), 'from': desde,
                                 'page': page, 'per_page': 100})
        if r.status_code not in (200, 206):
            raise RuntimeError(f'Zipnova HTTP {r.status_code}: {r.text[:150]}')
        d = r.json()
        data = d.get('data', []) if isinstance(d, dict) else d
        envios.extend(data)
        meta = d.get('meta') or {} if isinstance(d, dict) else {}
        if not data or page >= int(meta.get('last_page') or page):
            break
        page += 1
    conn = get_conn()
    a_detallar = []
    try:
        with conn.cursor() as c:
            for e in envios:
                zid = e.get('id')
                if not zid:
                    continue
                c.execute("""INSERT INTO zipnova_envios (zipnova_id, external_id, guia, status, status_name, carrier_id,
                             tracking_url, tracking_ext_url, creado_at)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                             ON DUPLICATE KEY UPDATE external_id=VALUES(external_id), guia=VALUES(guia),
                               status=VALUES(status), status_name=VALUES(status_name), carrier_id=VALUES(carrier_id),
                               tracking_url=VALUES(tracking_url), tracking_ext_url=VALUES(tracking_ext_url)""",
                          (zid, str(e.get('external_id') or '')[:40] or None, e.get('delivery_id'), e.get('status'),
                           e.get('status_name'), e.get('carrier_id'), e.get('tracking'), e.get('tracking_external'),
                           _utc_naive(e.get('created_at'))))
                prev = previos.get(zid)
                if not prev or prev['status'] != e.get('status') or not prev['carrier']:
                    a_detallar.append(zid)
        conn.commit()
    finally:
        conn.close()

    # Detalle (transporte y hora del último estado) solo de los que cambiaron
    detallados = 0
    for zid in a_detallar[:80]:
        r = requests.get(f'{ZN_BASE}/shipments/{zid}', auth=_zn_auth(), timeout=20)
        if r.status_code not in (200, 206):
            continue
        det = r.json()
        car = det.get('carrier')
        nombre = (car.get('name') if isinstance(car, dict) else car) or None
        execute_db("UPDATE zipnova_envios SET carrier=%s, last_status_at=%s WHERE zipnova_id=%s",
                   (str(nombre)[:80] if nombre else None, _utc_naive(det.get('last_status_at')), zid))
        detallados += 1

    # Enlazar a ventas
    resueltos = 0
    pend = query_db("SELECT zipnova_id, external_id FROM zipnova_envios WHERE numero_venta IS NULL "
                    "AND external_id IS NOT NULL ORDER BY creado_at DESC LIMIT %s", (max_resolver,))
    tok = None
    for p in pend:
        ext = p['external_id']
        nv = ''
        if query_one("SELECT 1 AS x FROM ventas WHERE numero_venta=%s", (ext,)):
            nv = ext
        elif ext.isdigit():
            tok = tok or _ml_token()
            if not tok:
                break
            sh = _ml_get(f'/shipments/{ext}', tok)
            oid = (sh or {}).get('order_id')
            if sh is None:
                continue          # error transitorio: reintenta en la próxima corrida
            cands = [f'ML-{oid}'] if oid else []
            if oid:
                o = _ml_get(f'/orders/{oid}', tok) or {}
                if o.get('pack_id'):
                    cands.append(f"ML-{o['pack_id']}")
            for cand in cands:
                if query_one("SELECT 1 AS x FROM ventas WHERE numero_venta=%s", (cand,)):
                    nv = cand
                    break
        execute_db("UPDATE zipnova_envios SET numero_venta=%s WHERE zipnova_id=%s", (nv, p['zipnova_id']))
        resueltos += 1
    return f'envíos={len(envios)} detallados={detallados} enlazados={resueltos}'


# ─────────────────────────── job: mensajes ML sin leer ───────────────────────────

def sync_ml_no_leidos():
    query_db, query_one, execute_db, get_conn = _db()
    tok = _ml_token()
    if not tok:
        return 'sin token ML'
    d = _ml_get('/messages/unread', tok, {'role': 'seller', 'tag': 'post_sale'})
    if d is None:
        raise RuntimeError('ML /messages/unread no respondió')
    conocidos = {}
    for r in query_db("SELECT order_id, pack_id FROM ml_mensajes_no_leidos"):
        conocidos.setdefault(r['pack_id'], []).append(r['order_id'])
    filas = []
    for it in d.get('results') or []:
        m = re.search(r'/packs/(\d+)', it.get('resource') or '')
        if not m:
            continue
        pack = int(m.group(1))
        cant = int(it.get('count') or 0)
        if cant <= 0:
            continue
        orders = conocidos.get(pack)
        if not orders:
            if query_one("SELECT 1 AS x FROM ventas WHERE numero_venta=%s", (f'ML-{pack}',)):
                orders = [pack]
            else:
                pk = _ml_get(f'/packs/{pack}', tok)
                orders = [int(o['id']) for o in (pk or {}).get('orders') or [] if o.get('id')] or [pack]
        for oid in orders:
            filas.append((oid, pack, cant))
    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM ml_mensajes_no_leidos")
            for f in filas:
                c.execute("INSERT INTO ml_mensajes_no_leidos (order_id, pack_id, cantidad) VALUES (%s,%s,%s) "
                          "ON DUPLICATE KEY UPDATE cantidad=VALUES(cantidad), pack_id=VALUES(pack_id)", f)
        conn.commit()
    finally:
        conn.close()
    return f'packs con mensajes sin leer={len(d.get("results") or [])} órdenes={len(filas)}'


# Entradas para el scheduler (cada worker las llama; trabaja uno)
def _job(nombre, minimo, fn):
    try:
        _con_lock(nombre, minimo, fn)
    except Exception as e:      # p. ej. tablas sin crear todavía
        print(f'[ZIPNOVA] job {nombre} no corrió: {e}', flush=True)


def job_zipnova_mails():
    _job('mails', 8 * 60, sync_mails)


def job_zipnova_envios():
    _job('envios', 25 * 60, sync_envios)


def job_ml_no_leidos():
    _job('ml_no_leidos', 150, sync_ml_no_leidos)


# ─────────────────────────── helpers para templates ───────────────────────────

def _mapa_zipnova():
    if 'zn_mapa' not in g:
        try:
            query_db = _db()[0]
            rows = query_db("SELECT zipnova_id, numero_venta, guia, status, status_name, carrier, tracking_url, "
                            "tracking_ext_url, last_status_at FROM zipnova_envios "
                            "WHERE numero_venta IS NOT NULL AND numero_venta != '' ORDER BY creado_at")
            g.zn_mapa = {r['numero_venta']: r for r in rows}   # el más nuevo pisa
        except Exception:
            g.zn_mapa = {}
    return g.zn_mapa


def _mapa_no_leidos():
    if 'ml_nl_mapa' not in g:
        try:
            query_db = _db()[0]
            g.ml_nl_mapa = {int(r['order_id']): int(r['cantidad'])
                            for r in query_db("SELECT order_id, cantidad FROM ml_mensajes_no_leidos")}
        except Exception:
            g.ml_nl_mapa = {}
    return g.ml_nl_mapa


def _ml_order_id(numero_venta):
    m = re.match(r'^ML-(\d+)$', str(numero_venta or ''))
    return int(m.group(1)) if m else None


@zipnova_bp.app_context_processor
def _inject_links_venta():
    def zn_envio(numero_venta):
        return _mapa_zipnova().get(numero_venta) if numero_venta else None

    def ml_orden(numero_venta):
        return _ml_order_id(numero_venta)

    def ml_no_leidos(numero_venta):
        oid = _ml_order_id(numero_venta)
        return _mapa_no_leidos().get(oid, 0) if oid else 0

    return {'zn_envio': zn_envio, 'ml_orden': ml_orden, 'ml_no_leidos': ml_no_leidos,
            'zn_panel_url': ZN_PANEL_URL}


# ─────────────────────────── página ───────────────────────────

def _puede():
    return current_user.is_authenticated and current_user.rol in ('admin', 'vendedor')


@zipnova_bp.route('/zipnova')
@login_required
def zipnova_recolecciones():
    if not _puede():
        flash('❌ No tenés permisos para acceder a esta sección', 'danger')
        return redirect(url_for('index'))
    query_db, query_one, _, _ = _db()
    dias = request.args.get('dias', '45')
    dias = int(dias) if str(dias).isdigit() else 45
    try:
        recos = query_db("SELECT * FROM zipnova_recolecciones WHERE fecha_retiro >= CURDATE() - INTERVAL %s DAY "
                         "ORDER BY fecha_retiro DESC, pickup_id DESC", (dias,))
        envios = query_db("""SELECT re.*, ze.zipnova_id, ze.status, ze.status_name, ze.carrier, ze.tracking_url,
                                    ze.tracking_ext_url, ze.numero_venta, ze.last_status_at,
                                    v.id AS venta_id, v.nombre_cliente, v.estado_entrega AS venta_estado
                             FROM zipnova_recoleccion_envios re
                             LEFT JOIN zipnova_envios ze ON ze.zipnova_id = (
                                  SELECT MAX(z2.zipnova_id) FROM zipnova_envios z2
                                  WHERE z2.external_id = re.external_id OR z2.guia = re.guia)
                             LEFT JOIN ventas v ON v.numero_venta = ze.numero_venta COLLATE utf8mb4_unicode_ci
                                                 AND ze.numero_venta != ''
                             WHERE re.pickup_id IN (SELECT pickup_id FROM zipnova_recolecciones
                                                    WHERE fecha_retiro >= CURDATE() - INTERVAL %s DAY)
                             ORDER BY re.pickup_id, re.orden""", (dias,))
        resumenes = {r['fecha']: r for r in query_db(
            "SELECT * FROM zipnova_resumenes WHERE fecha >= CURDATE() - INTERVAL %s DAY", (dias,))}
        jobs = {r['job']: r for r in query_db("SELECT * FROM zipnova_jobs")}
        sin_tablas = False
    except Exception as e:
        print(f'[ZIPNOVA] página: {e}', flush=True)
        if "doesn't exist" not in str(e):
            raise
        recos, envios, resumenes, jobs, sin_tablas = [], [], {}, {}, True

    por_pickup = {}
    for e in envios:
        por_pickup.setdefault(e['pickup_id'], []).append(e)
    hoy = date.today()
    for r in recos:
        lista = por_pickup.get(r['pickup_id'], [])
        res = resumenes.get(r['fecha_retiro'])
        rec_ids = set()
        norec_ids = set()
        if res:
            for x in json.loads(res['recolectados'] or '[]'):
                rec_ids.add(x['external_id']); rec_ids.add(x['guia'])
            for x in json.loads(res['no_recolectados'] or '[]'):
                norec_ids.add(x['external_id']); norec_ids.add(x['guia'])
        faltan = 0
        for e in lista:
            despachado_api = e.get('status') and e['status'] not in ('new', 'documentation_ready', 'ready_to_ship', 'cancelled')
            if res:
                e['recolectado'] = (e['external_id'] in rec_ids or e['guia'] in rec_ids)
                if e['external_id'] in norec_ids or e['guia'] in norec_ids:
                    e['recolectado'] = False
            else:
                e['recolectado'] = None
            e['despachado_api'] = bool(despachado_api)
            if res and not e['recolectado']:
                faltan += 1
        r['envios'] = lista
        r['resumen'] = res
        r['faltan'] = faltan
        r['es_futura'] = r['fecha_retiro'] > hoy
        # Recolectados en el resumen que no estaban en el PDF
        if res:
            en_pdf = {e['external_id'] for e in lista} | {e['guia'] for e in lista}
            r['extras'] = [x for x in json.loads(res['recolectados'] or '[]')
                           if x['external_id'] not in en_pdf and x['guia'] not in en_pdf]
        else:
            r['extras'] = []
    return render_template('zipnova.html', recolecciones=recos, jobs=jobs, dias=dias, sin_tablas=sin_tablas,
                           zn_panel_url=ZN_PANEL_URL)


@zipnova_bp.route('/zipnova/recoleccion/<int:pickup_id>.pdf')
@login_required
def zipnova_recoleccion_pdf(pickup_id):
    if not _puede():
        abort(403)
    query_one = _db()[1]
    r = query_one("SELECT pdf_archivo FROM zipnova_recolecciones WHERE pickup_id=%s", (pickup_id,))
    if not r or not r['pdf_archivo']:
        abort(404)
    ruta = os.path.join(PDF_DIR, os.path.basename(r['pdf_archivo']))
    if not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, mimetype='application/pdf', as_attachment=False,
                     download_name=f'recoleccion_zipnova_{pickup_id}.pdf')


@zipnova_bp.route('/zipnova/sincronizar', methods=['POST'])
@login_required
def zipnova_sincronizar():
    if not _puede():
        abort(403)
    msgs = []
    for nombre, job, fn in (('Mails', 'mails', sync_mails), ('Envíos', 'envios', sync_envios)):
        res = _con_lock(job, 0, fn)
        msgs.append(f'{nombre}: {res if res is not None else "ya se estaba sincronizando"}')
    flash(' · '.join(msgs), 'info')
    return redirect(url_for('zipnova.zipnova_recolecciones'))
