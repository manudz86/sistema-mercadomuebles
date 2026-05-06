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

    # Costos fijos desde DB
    cur.execute("SELECT valor FROM configuracion WHERE clave='costo_flete_propio'")
    fp_row = cur.fetchone()
    costo_flete_propio = float(fp_row['valor']) if fp_row and fp_row.get('valor') else COSTO_FLEX_DEF
    cur.execute("SELECT valor FROM configuracion WHERE clave='costo_delega'")
    del_row = cur.fetchone()
    costo_delega = float(del_row['valor']) if del_row and del_row.get('valor') else 5000.0

    # Mapa precio compra para calcular costo_productos
    precio_compra_map = {}
    comp_map = {}
    try:
        cur.execute(
            'SELECT cp.sku, clp.precio_lista, cp.descripcion '
            'FROM cannon_productos cp '
            'JOIN cannon_lista_precios clp ON clp.codigo_material = cp.codigo_material '
            'WHERE cp.sku IS NOT NULL'
        )
        raw_prods = cur.fetchall()
        cur.execute('SELECT clave, valor FROM cannon_descuentos WHERE tipo="descuento_linea"')
        desc_rows = {r['clave']: float(r['valor']) for r in cur.fetchall()}
        for r in raw_prods:
            sku = r['sku']; precio = float(r['precio_lista'])
            desc = (r['descripcion'] or '').upper()
            clave = None
            if 'EUROPILLOW' in desc: clave = 'sublime_europillow' if 'SUBLIME' in desc else 'renovation_europillow'
            elif 'PRINCESS' in desc: clave = 'princess_23' if '23' in desc else 'princess_20'
            elif 'EXCLUSIVE' in desc: clave = 'exclusive'
            elif 'RENOVATION' in desc: clave = 'renovation'
            elif 'TROPICAL' in desc: clave = 'tropical'
            elif 'PLATINO' in desc: clave = 'platino'
            elif 'DORAL' in desc: clave = 'doral'
            elif 'SUBLIME' in desc: clave = 'sublime'
            elif desc.startswith('ALM') or sku.upper() in ('CLASICA','PLATINO','CERVICAL','RENOVATION','SUBLIME','DORAL','DUAL','EXCLUSIVE'): clave = 'almohadas'
            elif desc.startswith('BASE') or sku.upper().startswith('BASE_'): clave = 'bases'
            pct = desc_rows.get(clave, 0) if clave else 0
            sin_desc = clave in ('almohadas', 'ctr80')
            if not sin_desc and pct:
                precio = precio * (1 - pct/100) * (1/(1.05))
            precio_compra_map[sku] = round(precio, 2)
        cur.execute(
            'SELECT pc.sku sc, pb.sku sb, c.cantidad_necesaria cn '
            'FROM productos_compuestos pc '
            'JOIN componentes c ON pc.id=c.producto_compuesto_id '
            'JOIN productos_base pb ON c.producto_base_id=pb.id'
        )
        for cr in cur.fetchall():
            comp_map.setdefault(cr['sc'], []).append({'sku': cr['sb'], 'cant': float(cr['cn'])})
    except Exception as e_pm:
        print(f'  Aviso: no se pudo cargar mapa precios: {e_pm}')

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
                            list_cost_vendedor = round(so_list / 1.21, 2)
            except Exception as e:
                print(f"(shipment err: {e})", end=' ')

        metodo = v['metodo_envio']
        total  = float(v['importe_total'] or 0)
        SKUS_ALM = {'CERVICAL','CLASICA','DORAL','DUAL','EXCLUSIVE','PLATINO','PRUEBA',
                    'RENOVATION','SUBLIME','DORALX2','DUALX2','EXCLUSIVEX2','PLATINOX2','PLATINOX4'}

        # Obtener SKUs de la orden para lógica Turbo
        items_skus = [it.get('item',{}).get('seller_sku','').upper() for it in order_items]

        if metodo in ('Flex', 'Flete Propio'):
            costo_envio_vendedor = costo_flete_propio
        elif metodo == 'Delega':
            costo_envio_vendedor = costo_delega if list_cost_vendedor > 0 else 0.0
        elif metodo == 'Turbo':
            todos_alm = all(s in SKUS_ALM for s in items_skus if s)
            if not todos_alm:
                costo_envio_vendedor = costo_flete_propio
            elif total < 33000:
                costo_envio_vendedor = 0.0
            else:
                costo_envio_vendedor = round(costo_delega * 1.5, 2)
        else:
            # Colecta, Zippin, Retiro: list_cost sin IVA
            costo_envio_vendedor = list_cost_vendedor

        # ── Costo productos ────────────────────────────────────────────
        costo_productos = 0.0
        try:
            cur.execute('SELECT sku, cantidad FROM items_venta WHERE venta_id=%s', (v['id'],))
            for it in cur.fetchall():
                sr = it['sku']; sb = sr.replace('_DEP','').replace('_FULL','')
                pc = precio_compra_map.get(sr, precio_compra_map.get(sb, 0))
                if not pc:
                    for c in comp_map.get(sr, comp_map.get(sb, [])):
                        pc += precio_compra_map.get(c['sku'], 0) * c['cant']
                costo_productos += pc * float(it['cantidad'])
            costo_productos = round(costo_productos, 2)
        except Exception as e_cp:
            print(f"(costo_prod err: {e_cp})", end=' ')

        # ── UPDATE ─────────────────────────────────────────────────────
        try:
            cur.execute("""
                UPDATE ventas
                SET costo_comision = %s, costo_envio_vendedor = %s, costo_productos = %s
                WHERE id = %s
            """, (costo_comision, costo_envio_vendedor, costo_productos, v['id']))
            conn.commit()
            print(f"✅ comision=${costo_comision:,.0f}  envío=${costo_envio_vendedor:,.0f}  prod=${costo_productos:,.0f}")
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
