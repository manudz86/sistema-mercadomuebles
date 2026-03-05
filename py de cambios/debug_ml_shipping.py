# ============================================================================
# SCRIPT DE DEBUGGING - VER QUÉ TRAE ML
# Ejecutar esto desde Python para ver los datos reales
# ============================================================================

import requests
import json

# TU ACCESS_TOKEN
ACCESS_TOKEN = "TU_ACCESS_TOKEN_AQUI"  # Reemplazar

# ID de una orden de prueba
ORDEN_ID = "2000015174126338"  # Reemplazar con una orden real

headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}

# 1. Obtener orden
print("\n" + "="*70)
print("📦 OBTENIENDO ORDEN...")
print("="*70)

response = requests.get(f'https://api.mercadolibre.com/orders/{ORDEN_ID}', headers=headers)
orden = response.json()

# Guardar orden completa
with open('debug_orden_completa.json', 'w', encoding='utf-8') as f:
    json.dump(orden, f, indent=4, ensure_ascii=False)

print(f"\n✅ Orden guardada en: debug_orden_completa.json")

# 2. Ver datos de shipping básicos
print("\n" + "="*70)
print("🚚 DATOS DE SHIPPING EN ORDEN:")
print("="*70)

shipping = orden.get('shipping', {})
print(f"Shipping ID: {shipping.get('id')}")
print(f"Shipping Mode: {shipping.get('shipping_mode')}")
print(f"Logistic Type: {shipping.get('logistic_type')}")
print(f"Receiver Address: {shipping.get('receiver_address')}")

# 3. Si tiene shipping_id, obtener detalles completos
shipping_id = shipping.get('id')
if shipping_id:
    print("\n" + "="*70)
    print("📍 OBTENIENDO DETALLES DE ENVÍO...")
    print("="*70)
    
    response2 = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}', headers=headers)
    shipment = response2.json()
    
    # Guardar shipment completo
    with open('debug_shipment_completo.json', 'w', encoding='utf-8') as f:
        json.dump(shipment, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Shipment guardado en: debug_shipment_completo.json")
    
    # Mostrar dirección
    receiver_address = shipment.get('receiver_address', {})
    print(f"\n📍 DIRECCIÓN COMPLETA:")
    print(f"Address Line: {receiver_address.get('address_line')}")
    print(f"Street Name: {receiver_address.get('street_name')}")
    print(f"Street Number: {receiver_address.get('street_number')}")
    print(f"City: {receiver_address.get('city', {}).get('name')}")
    print(f"State: {receiver_address.get('state', {}).get('name')}")
    print(f"ZIP Code: {receiver_address.get('zip_code')}")

print("\n" + "="*70)
print("✅ DEBUG COMPLETO")
print("="*70)
print("\nRevisa los archivos JSON creados para ver toda la info.")
