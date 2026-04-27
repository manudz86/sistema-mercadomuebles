#!/usr/bin/env python3
"""
Actualiza nombre_cliente desde ML para ventas donde nombre = apodo o está vacío.
"""
import requests
import json
import pymysql
import time

# Conexión BD
conn = pymysql.connect(
    host='localhost',
    user='cannon',
    password='Sistema@32267845',
    db='inventario_cannon',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cursor = conn.cursor()

# Obtener token ML
cursor.execute("SELECT valor FROM configuracion WHERE clave = 'ml_token'")
row = cursor.fetchone()
token = json.loads(row['valor'])['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Ventas a corregir
cursor.execute("""
    SELECT id, numero_venta, mla_code, nombre_cliente
    FROM ventas
    WHERE canal = 'Mercado Libre'
    AND (nombre_cliente = mla_code OR nombre_cliente IS NULL OR nombre_cliente = '')
    ORDER BY fecha_venta DESC
""")
ventas = cursor.fetchall()
print(f"Ventas a corregir: {len(ventas)}\n")

actualizadas = 0
errores = 0

for venta in ventas:
    venta_id   = venta['id']
    numero     = venta['numero_venta']
    mla_code   = venta['mla_code']
    
    # Extraer orden_id del numero_venta (ML-XXXXXXXXXXXXXXXX)
    orden_id = numero.replace('ML-', '').strip()
    if not orden_id.isdigit():
        print(f"  [{venta_id}] {numero} — ID no numérico, saltando")
        continue
    
    try:
        r = requests.get(
            f'https://api.mercadolibre.com/orders/{orden_id}',
            headers=headers,
            timeout=10
        )
        if r.status_code != 200:
            print(f"  [{venta_id}] {numero} — Error ML {r.status_code}")
            errores += 1
            continue
        
        orden = r.json()
        buyer = orden.get('buyer', {})
        fn = (buyer.get('first_name') or '').strip()
        ln = (buyer.get('last_name') or '').strip()
        nombre_real = f"{fn} {ln}".strip().title()
        
        if not nombre_real:
            print(f"  [{venta_id}] {numero} ({mla_code}) — ML no devuelve nombre, sin cambios")
            continue
        
        # Actualizar
        cursor.execute(
            "UPDATE ventas SET nombre_cliente = %s WHERE id = %s",
            (nombre_real, venta_id)
        )
        conn.commit()
        print(f"  [{venta_id}] {numero} ({mla_code}) → {nombre_real} ✅")
        actualizadas += 1
        time.sleep(0.3)
        
    except Exception as e:
        print(f"  [{venta_id}] {numero} — Excepción: {e}")
        errores += 1

print(f"\n✅ Actualizadas: {actualizadas} | ❌ Errores: {errores}")
cursor.close()
conn.close()
