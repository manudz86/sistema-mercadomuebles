"""
backfill_costos_ml.py
Rellena costo_comision y costo_envio_vendedor para ventas ML desde 01/04/2026.
Correr en el VPS: python3 backfill_costos_ml.py
"""

import pymysql
import requests
import time
import re

# ── Config DB ──────────────────────────────────────────────────────────────
DB_HOST = 'localhost'
DB_USER = 'cannon'
DB_PASS = 'Sistema@32267845'
DB_NAME = 'inventario_cannon'

# ── Config ─────────────────────────────────────────────────────────────────
DESDE          = '2026-04-01'
COSTO_FLEX_DEF = 35000.0   # fallback si no está en configuracion
SLEEP_ENTRE    = 0.4        # segundos entre llamadas ML (rate limit)

# ───────────────────────────────────────────────────────────────────────────

def get_conn():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS,
                           db=DB_NAME, charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

def main():
    conn = get_conn()
    cur  = conn.cursor()

    # Token ML
    cur.execute("SELECT valor FROM configuracion WHERE clave='ml_token'")
    row = cur.fetchone()
    if not row:
        print("❌ No se encontró ml_token en configuracion")
        return
    token   = row['valor'].strip()
    import json as _json
    if token.startswith('{'):
        token = _json.loads(token).get('access_token', token)
    headers = {'Authorization': f'Bearer {token}'}

    # Costo flete propio desde DB
    cur.execute("SELECT valor FROM configuracion WHERE clave='costo_flete_propio'")
    fp_row = cur.fetchone()
    costo_flete_propio = float(fp_row['valor']) if fp_row and fp_row.get('valor') else COSTO_FLEX_DEF

    # Ventas ML sin costos desde DESDE
    cur.execute("""
        SELECT id, numero_venta, metodo_envio, importe_total
        FROM ventas
        WHERE canal = 'Mercado Libre'
          AND costo_comision IS NULL
          AND DATE(fecha_venta) >= %s
        ORDER BY fecha_venta ASC
    """, (DESDE,))
    ventas = cur.fetchall()

    print(f"📋 Ventas a procesar: {len(ventas)}")
    ok = err = skip = 0

    for v in ventas:
        # Extraer order_id del numero_venta (formato ML-XXXXXXXX)
        m = re.search(r'\d{10,}', v['numero_venta'] or '')
        if not m:
            print(f"  ⚠️  {v['numero_venta']} — no se pudo extraer order_id, saltando")
            skip += 1
            continue

        order_id = m.group(0)
        print(f"  🔄 {v['numero_venta']} (order {order_id})...", end=' ', flush=True)

        # ── Llamada a la orden ──────────────────────────────────────────
        try:
            r = requests.get(f'https://api.mercadolibre.com/orders/{order_id}',
                             headers=headers, timeout=10)
            time.sleep(SLEEP_ENTRE)
        except Exception as e:
            print(f"❌ error red: {e}")
            err += 1
            continue

        if r.status_code == 401:
            print("❌ Token vencido — renovalo y volvé a correr el script")
            break

        if r.status_code != 200:
            print(f"❌ HTTP {r.status_code}")
            err += 1
            continue

        orden_json   = r.json()
        order_items  = orden_json.get('order_items', [])
        sale_fee_sum = sum(float(it.get('sale_fee') or 0) for it in order_items)
        costo_comision = round(sale_fee_sum / 1.21, 2)

        # ── Costo envío vendedor ────────────────────────────────────────
        # Primero: list_cost del shipment (lo que ML nos cobra)
        list_cost_vendedor = 0.0
        shipping_id = orden_json.get('shipping', {}).get('id')
        if shipping_id:
            try:
                rs = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}',
                                  headers=headers, timeout=10)
                time.sleep(SLEEP_ENTRE)
                if rs.status_code == 200:
                    so = rs.json().get('shipping_option', {})
                    if so:
                        so_cost = so.get('cost')
                        so_list = float(so.get('list_cost') or 0)
                        if so_cost is not None and float(so_cost) == 0:
                            list_cost_vendedor = so_list
            except Exception as e:
                print(f"(shipment err: {e})", end=' ')

        # Segundo: sumar flete propio si aplica
        flete_extra = 0.0
        if v['metodo_envio'] in ('Flex', 'Flete Propio'):
            flete_extra = costo_flete_propio

        costo_envio_vendedor = round(list_cost_vendedor + flete_extra, 2)

        # ── UPDATE ─────────────────────────────────────────────────────
        try:
            cur.execute("""
                UPDATE ventas
                SET costo_comision = %s, costo_envio_vendedor = %s
                WHERE id = %s
            """, (costo_comision, costo_envio_vendedor, v['id']))
            conn.commit()
            print(f"✅ comision=${costo_comision:,.0f}  envío=${costo_envio_vendedor:,.0f}")
            ok += 1
        except Exception as e:
            conn.rollback()
            print(f"❌ DB error: {e}")
            err += 1

    cur.close()
    conn.close()
    print(f"\n{'='*50}")
    print(f"✅ OK: {ok}  ❌ Errores: {err}  ⚠️  Saltados: {skip}")

if __name__ == '__main__':
    main()
