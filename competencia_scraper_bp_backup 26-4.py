"""
competencia_scraper_bp.py
Panel para visualizar datos del scraping de competidores.
Lee desde la tabla competencia_scraper en BD (o del CSV si no hay tabla).
"""
import json, os, csv
from flask import Blueprint, render_template, jsonify, request

competencia_scraper_bp = Blueprint('competencia_scraper', __name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'competencia_procesado.csv')

def _cargar_productos():
    """Carga productos del CSV procesado."""
    if not os.path.exists(CSV_PATH):
        return []

    from collections import defaultdict
    import re

    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Agrupar por titulo
    grupos = defaultdict(list)
    for r in rows:
        grupos[r['titulo_orig']].append(r)

    productos = []
    for titulo, variantes in grupos.items():
        base = variantes[0]
        opciones = []
        for v in variantes:
            precio = v.get('precio', '') or ''
            cuotas_si = v.get('cuotas_si', '') or ''
            if precio:
                opciones.append({
                    'precio': precio,
                    'cuotas_si': cuotas_si,
                })

        precio_min = min((int(o['precio']) for o in opciones if o['precio']), default=0)

        productos.append({
            'tienda':    base['tienda'],
            'tipo':      base['tipo'],
            'modelo':    base['modelo'],
            'medida':    base['medida'],
            'almohadas': base.get('almohadas', '0'),
            'sku_match': base.get('sku_match', ''),
            'titulo':    titulo,
            'url':       base['url'],
            'opciones':  opciones,
            'precio_min': precio_min,
            'fecha':     base.get('fecha', ''),
        })

    productos.sort(key=lambda x: (x['tienda'], x['modelo'], x['medida']))
    return productos

def _get_filtros(productos):
    modelos = sorted(set(p['modelo'] for p in productos if p['modelo'] not in ('DESCONOCIDO', '')))
    medidas = sorted(set(p['medida'] for p in productos if p['medida'] and p['medida'] != '?'),
                     key=lambda x: (int(x.split('x')[0]) if 'x' in x else 999, x))
    return modelos, medidas

@competencia_scraper_bp.route('/admin/competencia-scraper')
def competencia_scraper_page():
    productos = _cargar_productos()
    modelos, medidas = _get_filtros(productos)
    return render_template(
        'competencia_scraper.html',
        productos=productos,
        modelos=modelos,
        medidas=medidas,
    )

@competencia_scraper_bp.route('/admin/competencia-scraper/upload', methods=['POST'])
def upload_csv():
    """Recibe el CSV del scraper y lo guarda."""
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    f.save(CSV_PATH)
    return jsonify({'ok': True, 'rows': sum(1 for _ in open(CSV_PATH, encoding='utf-8')) - 1})
