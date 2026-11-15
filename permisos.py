"""Permisos por rol, configurables desde /configuracion/permisos.

- Cada ruta del panel pertenece a un MÓDULO (REGLAS, la primera que coincide gana).
- Cada rol tiene, por módulo, un nivel: 'ninguno' | 'ver' | 'editar'.
  GET pide 'ver'; POST/PUT/DELETE piden 'editar' (salvo las excepciones marcadas en REGLAS).
- admin siempre tiene todo y no se configura (así nunca queda nadie afuera).
- Los niveles por defecto están en MODULOS; lo que se guarda desde la página va a la
  tabla permisos_rol y pisa el defecto. Si la tabla no existe, se usan los defectos.
- Una ruta del panel que no coincide con ninguna regla queda SOLO PARA ADMIN.
"""
import time
from fnmatch import fnmatch

from flask import (Blueprint, flash, g, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import current_user

permisos_bp = Blueprint('permisos', __name__)

ROLES_CONFIGURABLES = ('vendedor', 'viewer', 'agencia')
NIVELES = ('ninguno', 'ver', 'editar')
_ORDEN = {'ninguno': 0, 'ver': 1, 'editar': 2}

# (clave, nombre, detalle, url de inicio, defectos {vendedor, viewer, agencia})
MODULOS = [
    ('dashboard', 'Dashboard', 'Pantalla de inicio con los números del día', '/',
     {'vendedor': 'ver', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('ventas', 'Ventas', 'Activas, proceso, históricas, calendario; crear, editar, cancelar, entregar, TRID, PDFs, WhatsApp de entrega', '/ventas/activas',
     {'vendedor': 'editar', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('importar_ml', 'Importar ventas ML', 'Importación manual de órdenes de ML y auto-import', '/ventas/ml/importar',
     {'vendedor': 'editar', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('stock', 'Stock', 'Ver stock, dashboard visual, cargar, bajar, transferir, historial', '/dashboard-visual',
     {'vendedor': 'editar', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('alertas', 'Alertas de stock', 'Alertas de stock bajo / sin stock y su acción en ML', '/alertas',
     {'vendedor': 'editar', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('publis_ml', 'Publicaciones ML', 'Stock, estado, demora, Flex/ME1, mapeo SKU-MLA, catálogo', '/cargar-stock-ml',
     {'vendedor': 'editar', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('precios_ml', 'Precios ML', 'Cambiar precios de publicaciones de ML', None,
     {'vendedor': 'editar', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('promos_ml', 'Promociones ML', 'Entrar/salir de campañas de ML, topes de aporte', '/promociones-ml',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('preguntas', 'Preguntas y reclamos ML', 'Responder preguntas y reclamos de ML', '/preguntas',
     {'vendedor': 'editar', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('envios', 'Envíos', 'Zipnova, fletes, viajes, cotizador, corrector ZPL', '/zipnova',
     {'vendedor': 'editar', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('intentos_pago', 'Intentos de pago', 'Rechazos de tarjeta, blocklist y excepciones antifraude', '/intentos-pago',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('estadisticas', 'Estadísticas', 'Ventas por canal, producto y origen', '/estadisticas',
     {'vendedor': 'ver', 'viewer': 'ver', 'agencia': 'ninguno'}),
    ('atribucion', 'Atribución web', 'Recorrido de cada venta de la tienda (Meta, Google, etc.)', '/tienda/admin/atribucion',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('agencia', 'Dashboard Agencia', 'Facturación, origen de ventas y GA4', '/agencia',
     {'vendedor': 'ver', 'viewer': 'ver', 'agencia': 'ver'}),
    ('tienda_catalogo', 'Tienda: catálogo', 'Productos de la tienda y sus fotos', '/productos',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('tienda_precios', 'Tienda: precios', 'Precios y descuentos de la tienda web', '/tienda-admin/precios',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('tienda_marketing', 'Tienda: ofertas, cupones y mails', 'Ofertas del home, cupones, suscriptores, recupero de carritos, mails', '/tienda-admin/ofertas',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('competencia', 'Competencia', 'Monitor, scraper, competencia V2 y ventas de competidores', '/admin/competencia',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('bot_precios', 'Bot de precios ML', 'Asistente que consulta la base y cambia precios en ML', '/admin/bot-precios',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('whatsapp', 'Bot WhatsApp', 'Conversaciones del bot de WhatsApp con clientes', '/admin/whatsapp',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('costos', 'Costos y rentabilidad', 'Costos, rentabilidad, pagos a Cannon', '/costos',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
    ('configuracion', 'Configuración', 'Medios de pago, cuotas, eventos, token de ML, porcentajes', '/configuracion',
     {'vendedor': 'ninguno', 'viewer': 'ninguno', 'agencia': 'ninguno'}),
]
_MODULO = {m[0]: m for m in MODULOS}

# Módulos especiales (no configurables):
#   _publico  → sin login (tienda, webhooks, login)
#   _logueado → cualquier usuario con sesión
#   _admin    → solo admin
#   _propio   → la ruta trae su propia autenticación (token del scraper)
# Tercer elemento: nivel forzado ('ver' para POST que solo consultan, 'editar' para GET
# que abren formularios o escriben). None = según el método.
REGLAS = [
    # ── Solo admin, fijo ──
    ('/admin/logs*', '_admin', None),
    ('/debug*', '_admin', None),
    ('/test/*', '_admin', None),
    ('/configuracion/resetear*', '_admin', None),
    ('/configuracion/permisos*', '_admin', None),
    ('/tienda/test-payway*', '_admin', None),
    ('/push/test', '_admin', None),
    ('/push/stats', '_admin', None),
    ('/auditoria-ml*', '_admin', None),
    # ── Autenticación propia / públicos ──
    ('/admin/competencia-scraper/sondas/*', '_propio', None),
    ('/admin/competencia-scraper/upload', '_propio', None),
    ('/admin/competencia-scraper/alert', '_propio', None),
    ('/login', '_publico', None),
    ('/logout', '_publico', None),
    ('/sw.js', '_publico', None),
    ('/static/*', '_publico', None),
    ('/push/public-key', '_publico', None),
    ('/webhook/*', '_publico', None),
    ('/cocinar*', '_publico', None),
    ('/tienda/admin/atribucion*', 'atribucion', None),
    ('/tienda', '_publico', None),
    ('/tienda/*', '_publico', None),
    # ── Cualquier usuario logueado ──
    ('/push/subscribe', '_logueado', None),
    ('/push/unsubscribe', '_logueado', None),
    ('/api/productos', '_logueado', None),
    # ── Publicaciones ML (antes que /cargar-stock y /bajar-stock) ──
    ('/cargar-stock-ml*', 'publis_ml', None),
    ('/cargar-stock-mla*', 'publis_ml', None),
    ('/cargar-stock-masivo*', 'publis_ml', None),
    ('/buscar-sku-ml*', 'publis_ml', 'ver'),
    ('/bajar-stock-mla-cero*', 'publis_ml', None),
    ('/bajar-stock-cero-masivo*', 'publis_ml', None),
    ('/activar-mla*', 'publis_ml', None),
    ('/activar-pausadas-masivo*', 'publis_ml', None),
    ('/cargar-demora-*', 'publis_ml', None),
    ('/quitar-demora-*', 'publis_ml', None),
    ('/ml/cambiar-envio-*', 'publis_ml', None),
    ('/mapeo-sku-mla/*', 'publis_ml', None),
    ('/faltantes-catalogo-ml/refresh', 'publis_ml', 'ver'),
    ('/faltantes-catalogo-ml*', 'publis_ml', None),
    ('/publicar-catalogo-cuota*', 'publis_ml', None),
    ('/configuracion/porcentajes-ml*', 'publis_ml', None),
    ('/configuracion/ml-z-sin-stock*', 'publis_ml', None),
    # ── Precios y promos ML ──
    ('/cambiar-precio*', 'precios_ml', None),
    ('/promociones-ml/buscar', 'promos_ml', 'ver'),
    ('/promociones-ml/campania', 'promos_ml', 'ver'),
    ('/promociones-ml*', 'promos_ml', None),
    # ── Stock ──
    ('/cargar-stock*', 'stock', 'editar'),
    ('/bajar-stock*', 'stock', 'editar'),
    ('/transferir-stock*', 'stock', 'editar'),
    ('/stock', 'stock', None),
    ('/dashboard-visual*', 'stock', None),
    ('/historial-stock*', 'stock', None),
    ('/alertas*', 'alertas', None),
    # ── Importar ML / token ──
    ('/ventas/ml/configurar_token*', 'configuracion', None),
    ('/ml/callback*', 'configuracion', None),
    ('/ventas/ml/*', 'importar_ml', 'editar'),
    ('/ventas/nueva/ml*', 'importar_ml', 'editar'),
    ('/ventas/auto-import-toggle', 'importar_ml', None),
    # ── Ventas ──
    ('/ventas/editar/*', 'ventas', 'editar'),
    ('/nueva-venta*', 'ventas', 'editar'),
    ('/ventas/historicas/facturar-multiple*', 'ventas', 'editar'),
    ('/ventas/historicas/*/generar-factura-excel', 'ventas', 'editar'),
    ('/ventas/nuevas-reset', 'ventas', 'ver'),
    ('/ventas/etiquetas-ml-masivo', 'ventas', 'ver'),
    ('/ventas*', 'ventas', None),
    # ── Envíos ──
    ('/zipnova/sincronizar', 'envios', 'ver'),
    ('/zipnova*', 'envios', None),
    ('/fletes*', 'envios', None),
    ('/viajes/nuevo', 'envios', 'editar'),
    ('/viajes*', 'envios', None),
    ('/cotizador-envio/cotizar', 'envios', 'ver'),
    ('/cotizador-envio*', 'envios', None),
    ('/herramientas/corrector-zpl*', 'envios', None),
    # ── Preguntas / reclamos / pagos ──
    ('/preguntas/sync', 'preguntas', 'ver'),
    ('/preguntas*', 'preguntas', None),
    ('/reclamos/sync', 'preguntas', 'ver'),
    ('/reclamos*', 'preguntas', None),
    ('/intentos-pago/sync', 'intentos_pago', 'ver'),
    ('/intentos-pago*', 'intentos_pago', None),
    # ── Análisis ──
    ('/', 'dashboard', None),
    ('/estadisticas*', 'estadisticas', None),
    ('/agencia*', 'agencia', None),
    # ── Tienda (admin del sitio) ──
    ('/productos/nuevo', 'tienda_catalogo', 'editar'),
    ('/productos/editar/*', 'tienda_catalogo', 'editar'),
    ('/productos/demora', 'configuracion', None),
    ('/productos/cuotas-coeficientes', 'configuracion', None),
    ('/productos/medio-toggle', 'configuracion', None),
    ('/productos/evento-guardar', 'configuracion', None),
    ('/productos/flete-almohadas', 'configuracion', None),
    ('/productos/newsletter-cupon', 'tienda_marketing', None),
    ('/productos*', 'tienda_catalogo', None),
    ('/tienda-admin/precios*', 'tienda_precios', None),
    ('/tienda-admin/*', 'tienda_marketing', None),
    # ── Bots / competencia / WhatsApp ──
    ('/admin/competencia*', 'competencia', None),
    ('/admin/ventas-competidores*', 'competencia', None),
    ('/admin/bot-precios*', 'bot_precios', None),
    ('/admin/whatsapp*', 'whatsapp', None),
    # ── Costos / configuración ──
    ('/costos/envio/barrido-ml', 'costos', 'editar'),
    ('/costos*', 'costos', None),
    ('/rentabilidad*', 'costos', None),
    ('/pagos-cannon*', 'costos', None),
    ('/configuracion*', 'configuracion', None),
]


def regla_de(path, method):
    """(modulo, nivel) para una ruta, o (None, None) si no coincide con ninguna regla."""
    for patron, modulo, forzado in REGLAS:
        if fnmatch(path, patron):
            return modulo, forzado or ('ver' if method in ('GET', 'HEAD') else 'editar')
    return None, None


# ── Lectura de la tabla, con caché corta por worker ────────────────────────
_CACHE = {'ts': 0.0, 'datos': None}
_CACHE_SEG = 20


def _db():
    from app import query_db, execute_db
    return query_db, execute_db


def tabla_de_permisos(forzar=False):
    """{rol: {modulo: nivel}} con defectos + lo guardado en permisos_rol."""
    if not forzar and _CACHE['datos'] is not None and time.time() - _CACHE['ts'] < _CACHE_SEG:
        return _CACHE['datos']
    datos = {r: {m[0]: m[4][r] for m in MODULOS} for r in ROLES_CONFIGURABLES}
    try:
        query_db, _ = _db()
        for f in query_db("SELECT rol, modulo, nivel FROM permisos_rol") or []:
            if f['rol'] in datos and f['modulo'] in _MODULO and f['nivel'] in _ORDEN:
                datos[f['rol']][f['modulo']] = f['nivel']
    except Exception as e:
        if "doesn't exist" not in str(e):
            print(f"[PERMISOS] no se pudo leer permisos_rol, uso defectos: {e}")
    _CACHE.update(ts=time.time(), datos=datos)
    return datos


def permite(rol, modulo, nivel='ver'):
    if modulo in ('_publico', '_propio', '_logueado'):
        return True
    if rol == 'admin':
        return True
    if modulo == '_admin' or rol not in ROLES_CONFIGURABLES or modulo not in _MODULO:
        return False
    return _ORDEN[tabla_de_permisos()[rol].get(modulo, 'ninguno')] >= _ORDEN[nivel]


def puede(modulo, nivel='ver'):
    """Para templates: ¿el usuario actual tiene este módulo con este nivel?"""
    if not current_user.is_authenticated:
        return False
    return permite(current_user.rol, modulo, nivel)


def inicio_de(rol):
    """Primera pantalla a la que el rol tiene acceso (para redirigir)."""
    for clave, _, _, url, _ in MODULOS:
        if url and permite(rol, clave, 'ver'):
            return url
    return None


def ruta_permitida(rol, path, method='GET'):
    modulo, nivel = regla_de(path, method)
    if modulo is None:
        return rol == 'admin'
    return permite(rol, modulo, nivel)


def controlar(req):
    """before_request: corta antes de la vista si el usuario no tiene permiso."""
    modulo, nivel = regla_de(req.path, req.method)
    if modulo in ('_publico', '_propio'):
        return None
    if modulo is None and not current_user.is_authenticated:
        return None   # ruta sin regla: decide el login_required de la vista
    # JSON para llamadas AJAX; un formulario HTML común recibe aviso + redirect.
    es_form = (req.method not in ('GET', 'HEAD') and not req.is_json
               and (req.mimetype or '') in ('application/x-www-form-urlencoded', 'multipart/form-data')
               and 'application/json' not in (req.headers.get('Accept') or '')
               and req.headers.get('X-Requested-With') != 'XMLHttpRequest')
    quiere_json = not es_form and (
        req.method not in ('GET', 'HEAD') or req.is_json
        or 'application/json' in (req.headers.get('Accept') or ''))
    if not current_user.is_authenticated:
        if quiere_json:
            return jsonify({'ok': False, 'error': 'Sesión vencida: volvé a iniciar sesión'}), 401
        return redirect(url_for('login', next=req.full_path.rstrip('?') if req.method == 'GET' else None))
    if modulo is None:
        modulo, nivel = '_admin', 'editar'
    if permite(current_user.rol, modulo, nivel):
        g.permiso_ok = True
        return None
    if quiere_json:
        return jsonify({'ok': False, 'error': 'No tenés permisos para esta acción'}), 403
    if es_form:
        flash('❌ No tenés permisos para hacer esta acción', 'danger')
        ref = req.referrer or ''
        host = req.host_url.rstrip('/')
        return redirect(ref if ref.startswith(host + '/') else (inicio_de(current_user.rol) or '/'))
    flash('❌ No tenés permisos para acceder a esta sección', 'danger')
    destino = inicio_de(current_user.rol)
    if destino and destino != req.path:
        return redirect(destino)
    return render_template('sin_permisos.html'), 403


# ── Página de configuración ────────────────────────────────────────────────
@permisos_bp.route('/configuracion/permisos', methods=['GET', 'POST'])
def permisos_pagina():
    # El acceso (solo admin) lo resuelve controlar() con la regla '/configuracion/permisos*'.
    if request.method == 'POST':
        query_db, execute_db = _db()
        cambios = 0
        actual = tabla_de_permisos(forzar=True)
        for rol in ROLES_CONFIGURABLES:
            for clave, *_ in MODULOS:
                nivel = request.form.get(f'{rol}__{clave}', '')
                if nivel not in _ORDEN or nivel == actual[rol][clave]:
                    continue
                execute_db("INSERT INTO permisos_rol (rol, modulo, nivel, actualizado_por) VALUES (%s,%s,%s,%s) "
                           "ON DUPLICATE KEY UPDATE nivel=VALUES(nivel), actualizado_por=VALUES(actualizado_por)",
                           (rol, clave, nivel, current_user.username))
                cambios += 1
        tabla_de_permisos(forzar=True)
        flash(f'✅ Permisos guardados ({cambios} cambio{"s" if cambios != 1 else ""}). '
              f'Se aplican en menos de {_CACHE_SEG} segundos.', 'success')
        return redirect(url_for('permisos.permisos_pagina'))
    try:
        query_db, _ = _db()
        query_db("SELECT 1 FROM permisos_rol LIMIT 1")
        tabla_ok = True
    except Exception:
        tabla_ok = False
    return render_template('permisos.html', modulos=MODULOS, roles=ROLES_CONFIGURABLES,
                           niveles=NIVELES, tabla=tabla_de_permisos(forzar=True), tabla_ok=tabla_ok)


@permisos_bp.app_context_processor
def _ctx_permisos():
    return {'puede': puede}
