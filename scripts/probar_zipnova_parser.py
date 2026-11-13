#!/usr/bin/env python3
"""Prueba el lector de PDF de recolección y del resumen diario de Zipnova (sin base ni red).

Uso: venv/bin/python scripts/probar_zipnova_parser.py reportes/zipnova_recolecciones/*.pdf
"""
import sys

sys.path.insert(0, '/home/cannon/app')
import zipnova_bp as Z  # noqa: E402

fallas = 0
for ruta in sys.argv[1:]:
    d = Z.parsear_pdf_recoleccion(ruta)
    print(f"\n{ruta}\n  pickup={d.get('pickup_id')} fecha={d.get('fecha_retiro')} origen={d.get('origen')} "
          f"generado={d.get('generado_at')} totales={d.get('total_envios')}/{d.get('total_bultos')}/"
          f"{d.get('total_kg')}/{d.get('total_m3')} ok={d['texto_ok']}")
    for e in d['envios']:
        print(f"   {e['orden']:>2} {e['external_id']:<14} {e['guia']:<15} bultos={e['bultos']} kg={e['kg']} | {e['detalle']}")
    if not d['texto_ok'] or len(d['envios']) != d.get('total_envios'):
        fallas += 1
        print('  FALLA: envíos leídos', len(d['envios']), 'vs total', d.get('total_envios'))
    if d.get('total_bultos') is not None and sum(e['bultos'] or 0 for e in d['envios']) != d['total_bultos']:
        fallas += 1
        print('  FALLA: suma de bultos')

txt = ("¡Hola Mercadomuebles! Te informamos el estado de las recolecciones del día 12/11/2026 . Envíos recolectados. "
       "Recolectados por Zipnova (Recolección Unificada). · Envío 48431284524 - Guía 0999-32438211. "
       "· Envío 48436256495 - Guía 0999-32476607. · Envío MP-123 - Guía 0999-1. Envíos no recolectados. "
       "· Envío 48478001182 - Guía 0999-32787576. En caso de observar")
f, rec, norec = Z.parsear_resumen(txt)
print('\nResumen:', f, rec, norec)
if str(f) != '2026-11-12' or len(rec) != 3 or len(norec) != 1 or rec[2]['external_id'] != 'MP-123':
    fallas += 1
    print('FALLA resumen')
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
