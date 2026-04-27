#!/usr/bin/env python3
"""
Actualiza nombre_cliente Y datos de facturación desde ML
para ventas donde nombre = apodo o está vacío.
Usa la estructura nueva de billing_info (additional_info array).
"""
import requests, json, pymysql, time

conn = pymysql.connect(host='localhost', user='cannon', password='Sistema@32267845',
                       db='inventario_cannon', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
cursor = conn.cursor()

cursor.execute("SELECT valor FROM configuracion WHERE clave = 'ml_token'")
token = json.loads(cursor.fetchone()['valor'])['access_token']
headers = {'Authorization': f'Bearer {token}'}

cursor.execute("""
    SELECT id, numero_venta, mla_code, nombre_cliente,
           factura_doc_number, factura_taxpayer_type, factura_state
    FROM ventas
    WHERE canal = 'Mercado Libre'
    AND (nombre_cliente = mla_code OR nombre_cliente IS NULL OR nombre_cliente = ''
         OR factura_doc_number IS NULL)
    ORDER BY fecha_venta DESC
""")
ventas = cursor.fetchall()
print(f"Ventas a corregir: {len(ventas)}\n")
print(f"{'ID':>6} | {'Numero Venta':<25} | {'Nombre':<25} | {'Doc':<12} | {'IVA':<22} | Estado")
print("-"*110)

IVA_MAP = {
    'IVA Exento': 'Exento',
    'IVA Responsable Inscripto': 'Responsable Inscripto',
    'Monotributo': 'Responsable Monotributo',
}

actualizadas = errores = 0

for v in ventas:
    venta_id = v['id']
    numero   = v['numero_venta']
    orden_id = numero.replace('ML-', '').strip()
    if not orden_id.isdigit():
        print(f"  [{venta_id}] ID no numérico, saltando")
        continue
    try:
        # Nombre real
        r = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}',
                         headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"  [{venta_id}] Error ML orden {r.status_code}")
            errores += 1; continue
        buyer = r.json().get('buyer', {})
        fn = (buyer.get('first_name') or '').strip()
        ln = (buyer.get('last_name') or '').strip()
        nombre_real = f"{fn} {ln}".strip().title() or v['mla_code']

        # Billing info
        bi = {'business_name': None, 'doc_type': None, 'doc_number': None,
              'taxpayer_type': None, 'city': None, 'street': None,
              'state': None, 'zip_code': None}
        try:
            rb = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}/billing_info',
                              headers=headers, timeout=10)
            if rb.status_code == 200:
                bd = rb.json()
                bi_root = bd.get('billing_info', {})
                add_info = bi_root.get('additional_info', [])
                if add_info:
                    ai = {item['type']: item['value'] for item in add_info}
                    tp = ai.get('TAXPAYER_TYPE_ID', '')
                    bi = {
                        'business_name': ai.get('BUSINESS_NAME') or None,
                        'doc_type':      bi_root.get('doc_type') or ai.get('DOC_TYPE'),
                        'doc_number':    bi_root.get('doc_number') or ai.get('DOC_NUMBER'),
                        'taxpayer_type': IVA_MAP.get(tp, tp) or None,
                        'city':          ai.get('CITY_NAME'),
                        'street':        ai.get('STREET_NAME'),
                        'state':         ai.get('STATE_NAME'),
                        'zip_code':      ai.get('ZIP_CODE'),
                    }
                else:
                    # Estructura vieja
                    braw = bd.get('buyer', {}).get('billing_info', {})
                    tp = braw.get('taxpayer_type', {})
                    if isinstance(tp, dict): tp = tp.get('description', '')
                    bi = {
                        'business_name': braw.get('business_name'),
                        'doc_type':      braw.get('doc_type'),
                        'doc_number':    braw.get('doc_number'),
                        'taxpayer_type': IVA_MAP.get(tp, tp),
                        'city':          braw.get('city'),
                        'street':        braw.get('street'),
                        'state':         braw.get('state'),
                        'zip_code':      braw.get('zip_code'),
                    }
        except Exception as e_b:
            print(f"    billing err: {e_b}")

        cursor.execute("""
            UPDATE ventas SET
                nombre_cliente=%s, factura_business_name=%s, factura_doc_type=%s,
                factura_doc_number=%s, factura_taxpayer_type=%s, factura_city=%s,
                factura_street=%s, factura_state=%s, factura_zip_code=%s
            WHERE id=%s
        """, (nombre_real, bi['business_name'], bi['doc_type'], bi['doc_number'],
              bi['taxpayer_type'], bi['city'], bi['street'], bi['state'],
              bi['zip_code'], venta_id))
        conn.commit()

        doc   = bi['doc_number'] or '-'
        iva   = bi['taxpayer_type'] or '-'
        state = bi['state'] or '-'
        print(f"{venta_id:>6} | {numero:<25} | {nombre_real:<25} | {doc:<12} | {iva:<22} | {state}")
        actualizadas += 1
        time.sleep(0.3)
    except Exception as e:
        print(f"  [{venta_id}] Excepcion: {e}")
        errores += 1

print(f"\nActualizadas: {actualizadas} | Errores: {errores}")
cursor.close()
conn.close()
