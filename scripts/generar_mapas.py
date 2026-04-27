#!/usr/bin/env python3
"""
Generador de SYSTEM_MAP.md y DB_MAP.md
Lee app.py y tienda_bp.py, parsea con AST, y genera dos archivos markdown:
- SYSTEM_MAP.md: índice de rutas/funciones con tablas y templates
- DB_MAP.md: índice de tablas con columnas y funciones que las usan

Uso (desde la carpeta sistema_cannon_simple):
    python scripts/generar_mapas.py
"""
import ast
import os
import re
import sys
from collections import defaultdict

# ── Configuración ─────────────────────────────────────────────────────────
ARCHIVOS = [
    'app.py',
    'tienda_bp.py',
]
OUT_SYSTEM = 'SYSTEM_MAP.md'
OUT_DB     = 'DB_MAP.md'

# ── Helpers ───────────────────────────────────────────────────────────────

def get_decorators(node):
    """Devuelve lista de decoradores legibles."""
    out = []
    for d in node.decorator_list:
        try:
            out.append(ast.unparse(d))
        except Exception:
            out.append('?')
    return out

def get_route_info(decorators):
    """Extrae (url, methods) de decoradores @app.route o @tienda_bp.route."""
    for d in decorators:
        m = re.match(r"(?:app|tienda_bp)\.route\(['\"]([^'\"]+)['\"](?:,\s*methods\s*=\s*\[([^\]]+)\])?", d)
        if m:
            url = m.group(1)
            methods_raw = m.group(2) or "'GET'"
            methods = ', '.join(re.findall(r"'(\w+)'", methods_raw))
            return url, methods
    return None, None

def extract_strings_from_calls(node, target_func_names):
    """
    Recorre el AST de una función y devuelve los strings literales pasados
    al primer argumento de las llamadas a las funciones target.
    Ej: render_template('foo.html') → 'foo.html'
    """
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            fn_name = ''
            if isinstance(sub.func, ast.Name):
                fn_name = sub.func.id
            elif isinstance(sub.func, ast.Attribute):
                fn_name = sub.func.attr
            if fn_name in target_func_names and sub.args:
                first = sub.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    out.append(first.value)
    return out

def extract_tables_from_sql(node, tablas_conocidas):
    """
    Busca strings con SQL dentro de la función y detecta nombres de tablas mencionadas.
    """
    encontradas = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            txt = sub.value
            if len(txt) < 8:
                continue
            # Heurística: buscar patrones SQL típicos
            txt_low = txt.lower()
            if any(kw in txt_low for kw in ('select ', 'insert into ', 'update ', 'delete from ', 'from ', 'join ')):
                # Buscar tablas conocidas
                for t in tablas_conocidas:
                    if re.search(rf'\b{re.escape(t)}\b', txt_low):
                        encontradas.add(t)
    return encontradas

def detect_actions(node, tabla):
    """Detecta si la función hace SELECT/INSERT/UPDATE/DELETE sobre una tabla."""
    acciones = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            txt = sub.value.lower()
            if not re.search(rf'\b{re.escape(tabla)}\b', txt):
                continue
            if re.search(r'\bselect\b.*\bfrom\b', txt) or re.search(rf'\bfrom\s+{re.escape(tabla)}\b', txt):
                acciones.add('R')
            if re.search(rf'\binsert\s+into\s+{re.escape(tabla)}\b', txt):
                acciones.add('W')
            if re.search(rf'\bupdate\s+{re.escape(tabla)}\b', txt):
                acciones.add('W')
            if re.search(rf'\bdelete\s+from\s+{re.escape(tabla)}\b', txt):
                acciones.add('W')
    return acciones

def get_docstring(node):
    """Primera línea del docstring."""
    doc = ast.get_docstring(node)
    if not doc:
        return ''
    return doc.strip().split('\n')[0][:200]

# ── Tablas conocidas (hardcoded de la BD) ────────────────────────────────
TABLAS_BD = {
    'ventas': 'Ventas (cabecera): número, cliente, total, estado, canal, método envío',
    'items_venta': 'Detalle de productos vendidos en cada venta',
    'productos_base': 'Productos individuales (colchones, almohadas, bases): SKU, precio, stock, dimensiones',
    'productos_compuestos': 'Productos armados (sommiers): SKU, nombre, activo',
    'componentes': 'Relación productos_compuestos ↔ productos_base con cantidades',
    'conjunto_configuracion': 'Config de sommiers: colchón + base default + cantidad bases',
    'productos_fotos': 'Fotos de productos: SKU, filename, orden',
    'usuarios': 'Login del sistema: username, password_hash, rol, activo',
    'configuracion': 'Configuración general del sistema (key/value): demora_sin_stock, ml_token, etc.',
    'cupones': 'Cupones de descuento: código, tipo, valor, mínimo, vencimiento',
    'cupones_uso': 'Registro de uso de cupones por email',
    'suscriptores': 'Suscriptores newsletter: email, cupón asignado',
    'ofertas_home': 'Ofertas destacadas en home tienda: SKU, descuento, orden',
    'pedidos_pendientes': 'Pedidos en checkout antes del webhook MP',
    'fletes': 'Cobros y pagos a fleteros',
    'viajes': 'Hojas de ruta de envíos',
    'auto_import_log': 'Log del job de auto-import ML',
    'ml_publicaciones': 'Publicaciones de MercadoLibre con su SKU local',
    'costos': 'Costos de productos para cálculo de rentabilidad',
}

# ── Parser principal ─────────────────────────────────────────────────────

def parsear_archivo(ruta):
    """Devuelve lista de funciones con su info."""
    if not os.path.exists(ruta):
        print(f"⚠️  No encontrado: {ruta}")
        return []
    with open(ruta, encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)
    resultados = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            decorators = get_decorators(node)
            url, methods = get_route_info(decorators)
            templates = extract_strings_from_calls(node, ['render_template'])
            tablas = extract_tables_from_sql(node, TABLAS_BD.keys())
            doc = get_docstring(node)
            es_login = any('login_required' in d for d in decorators)
            resultados.append({
                'archivo': os.path.basename(ruta),
                'nombre': node.name,
                'linea': node.lineno,
                'url': url,
                'methods': methods,
                'templates': templates,
                'tablas': sorted(tablas),
                'doc': doc,
                'login_required': es_login,
                'node': node,  # para detectar acciones después
            })
    return resultados

# ── Generar SYSTEM_MAP.md ────────────────────────────────────────────────

def gen_system_map(funciones):
    lines = []
    lines.append('# 📘 SYSTEM_MAP — Mapa del Sistema Cannon')
    lines.append('')
    lines.append('Generado automáticamente por `scripts/generar_mapas.py`. **No editar a mano.**')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Separar rutas (con URL) de helpers (sin URL)
    rutas    = [f for f in funciones if f['url']]
    helpers  = [f for f in funciones if not f['url']]

    lines.append(f'## 🌐 Rutas HTTP — {len(rutas)} endpoints')
    lines.append('')
    # Agrupar por archivo
    por_archivo = defaultdict(list)
    for r in rutas:
        por_archivo[r['archivo']].append(r)

    for archivo in sorted(por_archivo.keys()):
        lines.append(f'### `{archivo}`')
        lines.append('')
        for r in sorted(por_archivo[archivo], key=lambda x: x['url']):
            auth = '🔒' if r['login_required'] else '🔓'
            lines.append(f'#### `{r["methods"]} {r["url"]}` {auth}')
            lines.append(f'- **Función:** `{r["nombre"]}()` (línea {r["linea"]})')
            if r['doc']:
                lines.append(f'- **Descripción:** {r["doc"]}')
            if r['templates']:
                lines.append(f'- **Templates:** {", ".join("`" + t + "`" for t in r["templates"])}')
            if r['tablas']:
                lines.append(f'- **Tablas:** {", ".join("`" + t + "`" for t in r["tablas"])}')
            lines.append('')

    lines.append('---')
    lines.append('')
    lines.append(f'## 🔧 Helpers (sin ruta HTTP) — {len(helpers)} funciones')
    lines.append('')
    por_archivo_h = defaultdict(list)
    for h in helpers:
        por_archivo_h[h['archivo']].append(h)

    for archivo in sorted(por_archivo_h.keys()):
        lines.append(f'### `{archivo}`')
        lines.append('')
        for h in sorted(por_archivo_h[archivo], key=lambda x: x['nombre']):
            doc = f' — {h["doc"]}' if h['doc'] else ''
            tabs = f' [tablas: {", ".join(h["tablas"])}]' if h['tablas'] else ''
            lines.append(f'- `{h["nombre"]}()` (L{h["linea"]}){doc}{tabs}')
        lines.append('')

    return '\n'.join(lines)

# ── Generar DB_MAP.md ────────────────────────────────────────────────────

def gen_db_map(funciones):
    lines = []
    lines.append('# 🗄️ DB_MAP — Mapa de la Base de Datos')
    lines.append('')
    lines.append('Generado automáticamente por `scripts/generar_mapas.py`. **No editar a mano.**')
    lines.append('')
    lines.append('Cada tabla muestra las funciones que la **leen** (R) o **modifican** (W).')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Para cada tabla, recorrer todas las funciones y detectar acciones
    for tabla, descripcion in TABLAS_BD.items():
        lectores  = []
        escritores = []
        for f in funciones:
            if tabla not in f['tablas']:
                continue
            acciones = detect_actions(f['node'], tabla)
            label = f'`{f["nombre"]}()` ({f["archivo"]}:L{f["linea"]})'
            if 'W' in acciones:
                escritores.append(label)
            elif 'R' in acciones:
                lectores.append(label)
            else:
                lectores.append(label)  # si no se pudo detectar, asumir lectura

        lines.append(f'## `{tabla}`')
        lines.append(f'_{descripcion}_')
        lines.append('')
        if escritores:
            lines.append(f'**✏️ Modifican ({len(escritores)}):**')
            for e in sorted(set(escritores)):
                lines.append(f'- {e}')
            lines.append('')
        if lectores:
            lines.append(f'**👁️ Leen ({len(lectores)}):**')
            for l in sorted(set(lectores)):
                lines.append(f'- {l}')
            lines.append('')
        if not lectores and not escritores:
            lines.append('_Sin uso detectado en el código._')
            lines.append('')

    return '\n'.join(lines)

# ── Main ─────────────────────────────────────────────────────────────────

def main():
    todas_funciones = []
    for archivo in ARCHIVOS:
        funcs = parsear_archivo(archivo)
        todas_funciones.extend(funcs)
        print(f'✅ {archivo}: {len(funcs)} funciones parseadas')

    sys_md = gen_system_map(todas_funciones)
    db_md  = gen_db_map(todas_funciones)

    with open(OUT_SYSTEM, 'w', encoding='utf-8') as f:
        f.write(sys_md)
    with open(OUT_DB, 'w', encoding='utf-8') as f:
        f.write(db_md)

    print(f'✅ Generado: {OUT_SYSTEM} ({len(sys_md):,} caracteres)')
    print(f'✅ Generado: {OUT_DB} ({len(db_md):,} caracteres)')

if __name__ == '__main__':
    main()
