import sys, time
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('config/.env')
from tiendanube_bp import tn_request, get_db

PRECIOS_CONJUNTO = {
    'CPR8020_CONJ':  269000,
    'CPR9020_CONJ':  288000,
    'CPR10020_CONJ': 314000,
    'CPR14020_CONJ': 411000,
    'CPR8023_CONJ':  311000,
    'CPR9023_CONJ':  332000,
    'CPR10023_CONJ': 366000,
    'CPR14023_CONJ': 482000,
    'CEX80_CONJ':  350000,
    'CEX90_CONJ':  378000,
    'CEX100_CONJ': 414000,
    'CEX140_CONJ': 543000,
    'CEX150_CONJ': 590000,
    'CEX160_CONJ': 768000,
    'CEX180_CONJ': 876000,
    'CEX200_CONJ': 1002000,
    'CEXP80_CONJ':  413000,
    'CEXP90_CONJ':  434000,
    'CEXP100_CONJ': 464000,
    'CEXP140_CONJ': 606000,
    'CEXP150_CONJ': 657000,
    'CEXP160_CONJ': 850000,
    'CEXP180_CONJ': 975000,
    'CEXP200_CONJ': 1055000,
    'CRE80_CONJ':  406000,
    'CRE90_CONJ':  440000,
    'CRE100_CONJ': 483000,
    'CRE140_CONJ': 635000,
    'CRE150_CONJ': 689000,
    'CRE160_CONJ': 888000,
    'CRE180_CONJ': 977000,
    'CRE200_CONJ': 1064000,
    'CREP80_CONJ':  487000,
    'CREP90_CONJ':  531000,
    'CREP100_CONJ': 582000,
    'CREP140_CONJ': 769000,
    'CREP160_CONJ': 1002000,
    'CREP180_CONJ': 1230000,
    'CREP200_CONJ': 1271000,
    'CSO80_CONJ':  373000,
    'CSO90_CONJ':  397000,
    'CSO100_CONJ': 432000,
    'CSO140_CONJ': 536000,
    'CDO80_CONJ':  406000,
    'CDO90_CONJ':  435000,
    'CDO100_CONJ': 467000,
    'CDO140_CONJ': 610000,
    'CDO160_CONJ': 886000,
    'CDO180_CONJ': 915000,
    'CDO200_CONJ': 976000,
    'CDOP140_CONJ': 745000,
    'CDOP150_CONJ': 825000,
    'CDOP160_CONJ': 1042000,
    'CDOP180_CONJ': 1065000,
    'CDOP200_CONJ': 1146000,
    'CSUP140_CONJ': 963000,
    'CSUP150_CONJ': 1023000,
    'CSUP160_CONJ': 1230000,
    'CSUP180_CONJ': 1377000,
    'CSUP200_CONJ': 1526000,
}

db = get_db()
cursor = db.cursor()
cursor.execute("SELECT sku_interno, tiendanube_product_id, tiendanube_variant_id FROM sku_tiendanube_mapeo WHERE tipo = 'conjunto' AND activo = 1")
mapeos = cursor.fetchall()

actualizados = 0
errores = 0

for m in mapeos:
    sku = m['sku_interno']
    precio = PRECIOS_CONJUNTO.get(sku)
    if not precio:
        print(f'SIN PRECIO: {sku}')
        continue
    try:
        tn_request('PUT', f'products/{m["tiendanube_product_id"]}/variants/{m["tiendanube_variant_id"]}', {'price': str(precio)})
        actualizados += 1
        print(f'OK: {sku} -> ${precio:,}')
        time.sleep(0.3)
    except Exception as e:
        errores += 1
        print(f'ERROR: {sku} -> {e}')

cursor.close()
db.close()
print(f'\nFINAL: {actualizados} actualizados, {errores} errores')
