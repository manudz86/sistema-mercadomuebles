import sys, time
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('config/.env')
from tiendanube_bp import tn_request, get_db

db = get_db()
cursor = db.cursor()
cursor.execute("""
    SELECT m.sku_interno, m.tiendanube_product_id, m.tiendanube_variant_id, p.precio_base 
    FROM sku_tiendanube_mapeo m 
    JOIN productos_base p ON p.sku = m.sku_interno 
    WHERE m.tipo = 'almohada' AND m.activo = 1
""")
mapeos = cursor.fetchall()

for m in mapeos:
    try:
        tn_request('PUT', f'products/{m["tiendanube_product_id"]}/variants/{m["tiendanube_variant_id"]}', {'price': str(int(m['precio_base']))})
        print(f'OK: {m["sku_interno"]} -> ${m["precio_base"]:,.0f}')
        time.sleep(0.3)
    except Exception as e:
        print(f'ERROR: {m["sku_interno"]} -> {e}')

cursor.close()
db.close()
