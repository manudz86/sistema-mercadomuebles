# -*- coding: utf-8 -*-
"""
competencia_informe.py
Lógica compartida del Informe de Competencia (precios propios vs scraping) y del
snapshot histórico de precios de competencia.

NO importa app.py (para poder usarse también desde un script de seeding sin
disparar el scheduler). Los precios propios se calculan en la ruta y se pasan
acá ya resueltos.

Limpieza de ruido usando los flags que el propio scraper ya calcula:
  - medida_origen == 'inferida'  → título no certero (la "*" del panel) → se descarta
  - almohadas != 0               → publicación con almohadas → se descarta
  - pack != 1                    → packs → se descartan
  - título con palabras de bundle (almohada/cubre/regalo/...) → se descarta
Luego, por (tienda, sku), se elige el contado que forma "escalera" coherente con
los precios en cuotas y se colapsa cada modalidad a un precio representativo (mediana).
"""
import csv, statistics
from collections import defaultdict

BUNDLE_KW = ['almohad', 'cubre', 'regalo', 'combo', 'sabana', 'sábana', 'protector']
PASAJES_INV_DEFAULT = {'colchon': {6: 3, 9: 6, 12: 9, 18: 12},
                       'sommier': {6: 3, 12: 9, 18: 12}}
ORDER = ['sin', '3', '6', '9', '12', 'simple']
LBL = {'sin': 'Contado', '3': '3 cuotas', '6': '6 cuotas',
       '9': '9 cuotas', '12': '12 cuotas', 'simple': 'C. Simple'}
MYKEY = {'sin': 'precio_sin_cuotas', 'simple': 'precio_1c', '3': 'precio_3c',
         '6': 'precio_6c', '9': 'precio_9c', '12': 'precio_12c'}
COMPS_DEFAULT = ('TMS', 'Lanus', 'Ivana')


def _es_bundle(t):
    t = (t or '').lower()
    return any(k in t for k in BUNDLE_KW)


def fila_limpia(r):
    """True si la fila del scraping es comparable (mismo sku, 1 unidad, sin adicionales)."""
    if (r.get('pack', '1') or '1') != '1':
        return False
    try:
        if int(r.get('almohadas', '0') or 0) != 0:
            return False
    except (ValueError, TypeError):
        return False
    if r.get('medida_origen') == 'inferida':
        return False
    if _es_bundle(r.get('titulo_orig')):
        return False
    return True


def real_cuota(most, tipo, inv):
    """Pasa la cuota MOSTRADA en ML a la cuota REAL (descontando el pasaje)."""
    try:
        n = int(most)
    except (ValueError, TypeError):
        return None
    return inv.get(tipo, {}).get(n, n)


def bucket_of(r, tipo, inv):
    if r.get('cuotas_simple', '0') == '1':
        return 'simple'
    cs = (r.get('cuotas_si') or '').strip()
    if not cs:
        return 'sin'
    rc = real_cuota(cs, tipo, inv)
    return str(rc) if rc in (3, 6, 9, 12) else None


def representativos(rows, tipo, inv, ref=None):
    """
    Devuelve {bucket: (precio_rep, n_usados, n_total)} para un grupo (tienda, sku).
    Elige el contado base 'cstar' que mejor encaja con la escalera de cuotas y
    descarta los precios incoherentes. 'ref' (mi contado) sólo se usa como desempate.
    """
    raw = defaultdict(list)
    for r in rows:
        try:
            p = int(r['precio'])
        except (ValueError, TypeError, KeyError):
            continue
        if p <= 0:
            continue
        b = bucket_of(r, tipo, inv)
        if b:
            raw[b].append(p)
    if not raw:
        return {}

    cont = sorted(raw.get('sin', []))
    cuota_med = {b: statistics.median(v) for b, v in raw.items()
                 if b in ('3', '6', '9', '12', 'simple')}

    if cont:
        best = None
        for c in sorted(set(cont)):
            score = sum(1 for m in cuota_med.values() if 0.98 * c <= m <= 1.75 * c)
            near = sum(1 for v in cont if 0.9 * c <= v <= 1.15 * c)
            tie = (-abs(c - ref)) if ref else 0
            key = (score, near, tie)
            if best is None or key > best[0]:
                best = (key, c)
        cstar = best[1]
    elif ref:
        cstar = ref
    else:
        cstar = statistics.median([v for vs in raw.values() for v in vs])

    out = {}
    if cont:
        clu = [v for v in cont if 0.9 * cstar <= v <= 1.15 * cstar] or cont
        out['sin'] = (int(round(statistics.median(clu))), len(clu), len(cont))
    for b in ('3', '6', '9', '12', 'simple'):
        vals = raw.get(b, [])
        if not vals:
            continue
        lo, hi = (0.90, 1.7) if b == 'simple' else (0.95, 1.8)
        keep = [v for v in vals if lo * cstar <= v <= hi * cstar]
        if not keep:
            continue
        out[b] = (int(round(statistics.median(keep))), len(keep), len(vals))
    return out


def cargar_filas(csv_path):
    with open(csv_path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _agrupar(rows):
    """{(tienda, sku): [filas limpias]}, {sku: tipo}."""
    by = defaultdict(list)
    tipos = {}
    for r in rows:
        sku = (r.get('sku_match') or '').strip()
        if not sku or not fila_limpia(r):
            continue
        by[(r['tienda'], sku)].append(r)
        tipos.setdefault(sku, r.get('tipo') or ('sommier' if sku.startswith('S') else 'colchon'))
    return by, tipos


def construir_snapshot(csv_path, inv):
    """Reps de competencia (sin precios propios) para guardar en el histórico."""
    by, tipos = _agrupar(cargar_filas(csv_path))
    out = []
    for (tienda, sku), rr in by.items():
        tipo = tipos.get(sku, 'colchon')
        for bt, (rep, nk, _nt) in representativos(rr, tipo, inv).items():
            out.append({'tienda': tienda, 'sku': sku, 'bucket': bt, 'precio': rep, 'n': nk})
    return out


def construir_comparacion(csv_path, mis_precios, inv, comps=COMPS_DEFAULT):
    """Una línea por (sku, competidor, bucket) con mi precio vs el del competidor."""
    by, tipos = _agrupar(cargar_filas(csv_path))
    lines = []
    for sku, my in mis_precios.items():
        tipo = 'sommier' if sku.startswith('S') else 'colchon'
        my_sc = my['precio_sin_cuotas']
        for comp in comps:
            rr = by.get((comp, sku))
            if not rr:
                continue
            reps = representativos(rr, tipo, inv, ref=my_sc)
            for bt in ORDER:
                if bt not in reps:
                    continue
                rep, nk, _nt = reps[bt]
                myp = my.get(MYKEY[bt])
                if not myp:
                    continue
                lines.append({'sku': sku, 'tipo': tipo, 'comp': comp, 'bt': bt,
                              'comp_price': rep, 'n': nk, 'my': myp,
                              'diff': (myp / rep - 1) * 100})
    return lines


def recargo_por_tienda(csv_path, inv, comps=COMPS_DEFAULT):
    """Mediana del recargo % de cada competidor por cuota (3/6/9/12) vs su contado."""
    by, tipos = _agrupar(cargar_filas(csv_path))
    perc = defaultdict(lambda: defaultdict(list))
    for (tienda, sku), rr in by.items():
        if tienda not in comps:
            continue
        reps = representativos(rr, tipos.get(sku, 'colchon'), inv)
        base = reps.get('sin', (None,))[0]
        if not base:
            continue
        for c in ('3', '6', '9', '12'):
            if c in reps:
                perc[tienda][c].append((reps[c][0] / base - 1) * 100)
    out = {}
    for c in comps:
        out[c] = {cu: (statistics.median(perc[c][cu]) if perc[c].get(cu) else None)
                  for cu in ('3', '6', '9', '12')}
    return out


def inv_desde_pasajes(pasajes):
    """Convierte el dict de pasajes (mostrada->real) a {tipo: {hasta: desde}}."""
    inv = {'colchon': {}, 'sommier': {}}
    for t in ('colchon', 'sommier'):
        for desde, hasta in (pasajes or {}).get(t, []):
            try:
                inv[t][int(hasta)] = int(desde)
            except (ValueError, TypeError):
                continue
    if not inv['colchon'] and not inv['sommier']:
        return PASAJES_INV_DEFAULT
    return inv
