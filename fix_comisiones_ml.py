"""
fix_comisiones_ml.py
Busca ventas ML con costo_comision = 0 y las recalcula desde la API de ML.
Solo toca costo_comision, no modifica nada más.
Correr en el VPS: python3 fix_comisiones_ml.py
"""

import pymysql
import requests
import time
import re
import json as _json

# ── Config DB ──────────────────────────────────────────────────────────────
DB_HOST = 'localhost'
DB_USER = 'cannon'
DB_PASS = 'Sistema@32267845'
DB_NAME = 'inventario_cannon'

# ── Config ─────────────────────────────────────────────────────────────────
DESDE       = '2026-04-01'
SLEEP_ENTRE = 0.4

def get_conn():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS,
                           db=DB_NAME, charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

def main():
    conn = get_conn()
    cur  = conn.cursor()

    cur.execute("SELECT valor FROM configuracion WHERE clave='ml_token'")
    row = cur.fetchone()
    if not row:
        print("❌ No se encontró ml_token en configuracion")
        return
    token = row['valor'].strip()
    if token.startswith('{'):
        token = _json.loads(token).get('access_token', token)
    headers = {'Authorization': f'Bearer {token}'}

    # Ventas ML con comision 0 desde DESDE
    cur.execute("""
        SELECT id, numero_venta, importe_total, costo_comision
        FROM ventas
        WHERE canal = 'Mercado Libre'
          AND costo_comision = 0
          AND estado_entrega = 'entregada'
          AND DATE(fecha_venta) >= %s
        ORDER BY fecha_venta DESC
    """, (DESDE,))
    ventas = cur.fetchall()

    print(f"📋 Ventas a revisar: {len(ventas)}")
    ok = err = sin_cambio = 0

    for v in ventas:
        m = re.search(r'\d{10,}', v['numero_venta'] or '')
        if not m:
            sin_cambio += 1
            continue

        order_id = m.group(0)
        print(f"  🔄 {v['numero_venta']}...", end=' ', flush=True)

        try:
            r = requests.get(f'https://api.mercadolibre.com/orders/{order_id}',
                             headers=headers, timeout=10)
            time.sleep(SLEEP_ENTRE)
        except Exception as e:
            print(f"❌ red: {e}")
            err += 1
            continue

        if r.status_code == 401:
            print("❌ Token vencido — renová y volvé a correr")
            break

        if r.status_code != 200:
            print(f"❌ HTTP {r.status_code}")
            err += 1
            continue

        oj = r.json()
        sale_fee_total = sum(float(it.get('sale_fee') or 0) for it in oj.get('order_items', []))
        nueva_comision = round(sale_fee_total / 1.21, 2)

        if nueva_comision == 0:
            print(f"⏭️  ML también devuelve 0 — sin cambios")
            sin_cambio += 1
            continue

        try:
            cur.execute("UPDATE ventas SET costo_comision = %s WHERE id = %s",
                        (nueva_comision, v['id']))
            conn.commit()
            print(f"✅ actualizada: comision = ${nueva_comision:,.0f}")
            ok += 1
        except Exception as e:
            conn.rollback()
            print(f"❌ DB error: {e}")
            err += 1

    cur.close()
    conn.close()
    print(f"\n{'='*50}")
    print(f"✅ Actualizadas: {ok}  ⏭️  Sin cambios: {sin_cambio}  ❌ Errores: {err}")

if __name__ == '__main__':
    main()
