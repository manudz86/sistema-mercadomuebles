# ═══════════════════════════════════════════════════════
# 📦 PASO 3: PROBAR API - TRAER ÓRDENES DE MERCADO LIBRE
# ═══════════════════════════════════════════════════════
# 
# INSTRUCCIONES:
# 1. Reemplazá ACCESS_TOKEN con el token del Paso 2
# 2. DEJÁ LAS COMILLAS ("")
# 3. Ejecutá el script
# 4. Vas a ver tus últimas ventas de ML
# 
# ═══════════════════════════════════════════════════════

import requests
import json
from datetime import datetime

# ✏️ REEMPLAZÁ ESTO:
ACCESS_TOKEN = "APP_USR-2109946238600277-021620-7c8a1d74b33c020e6a7fb84c08f48643-29563319"  # ← Token del Paso 2

# ═══════════════════════════════════════════════════════
# EJEMPLO DE CÓMO DEBE QUEDAR:
# 
# ACCESS_TOKEN = "APP_USR-1234567890-021523-abcdef123456-987654321"
# 
# ═══════════════════════════════════════════════════════
# NO TOCAR ABAJO
# ═══════════════════════════════════════════════════════

print("\n" + "="*70)
print("🔍 BUSCANDO ÓRDENES EN MERCADO LIBRE...")
print("="*70)

# Headers con el token
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

try:
    # 1. Primero obtenemos el USER_ID
    print("\n1️⃣ Obteniendo información del usuario...")
    user_response = requests.get(
        "https://api.mercadolibre.com/users/me",
        headers=headers
    )
    
    if user_response.status_code != 200:
        print(f"\n❌ ERROR obteniendo usuario:")
        print(f"Status: {user_response.status_code}")
        print(f"Respuesta: {user_response.text}")
        exit()
    
    user_data = user_response.json()
    user_id = user_data['id']
    nickname = user_data['nickname']
    
    print(f"✅ Usuario: {nickname} (ID: {user_id})")
    
    # 2. Buscar órdenes como vendedor
    print("\n2️⃣ Buscando órdenes como vendedor...")
    orders_response = requests.get(
        f"https://api.mercadolibre.com/orders/search?seller={user_id}&sort=date_desc",
        headers=headers
    )
    
    if orders_response.status_code != 200:
        print(f"\n❌ ERROR obteniendo órdenes:")
        print(f"Status: {orders_response.status_code}")
        print(f"Respuesta: {orders_response.text}")
        exit()
    
    orders_data = orders_response.json()
    
    print(f"\n✅ Total de órdenes encontradas: {orders_data['paging']['total']}")
    print(f"📄 Mostrando primeras {len(orders_data['results'])} órdenes:\n")
    
    # 3. Mostrar detalle de cada orden
    print("="*70)
    for i, order in enumerate(orders_data['results'], 1):
        print(f"\n🛒 ORDEN #{i}")
        print("-"*70)
        print(f"ID Orden:       {order['id']}")
        
        # Fecha
        fecha = datetime.fromisoformat(order['date_created'].replace('Z', '+00:00'))
        print(f"Fecha:          {fecha.strftime('%d/%m/%Y %H:%M')}")
        
        # Estado
        print(f"Estado:         {order['status']}")
        
        # Items
        print(f"\nProductos:")
        for item in order['order_items']:
            print(f"  • {item['item']['title']}")
            print(f"    Cantidad: {item['quantity']}")
            print(f"    Precio: ${item['unit_price']:.2f}")
            print(f"    Subtotal: ${item['full_unit_price']:.2f}")
        
        # Total
        print(f"\n💰 TOTAL: ${order['total_amount']:.2f}")
        
        # Comprador
        buyer = order.get('buyer', {})
        print(f"\n👤 Comprador:")
        print(f"  • Nombre: {buyer.get('first_name', 'N/A')} {buyer.get('last_name', 'N/A')}")
        print(f"  • Nickname: {buyer.get('nickname', 'N/A')}")
        
        # Shipping
        if 'shipping' in order:
            shipping = order['shipping']
            print(f"\n📦 Envío:")
            print(f"  • Tipo: {shipping.get('shipping_mode', 'N/A')}")
            
            if 'receiver_address' in shipping:
                address = shipping['receiver_address']
                print(f"  • Dirección: {address.get('address_line', 'N/A')}")
                print(f"  • Ciudad: {address.get('city', {}).get('name', 'N/A')}")
                print(f"  • Provincia: {address.get('state', {}).get('name', 'N/A')}")
                print(f"  • CP: {address.get('zip_code', 'N/A')}")
        
        print("="*70)
    
    # 4. Guardar JSON completo
    print(f"\n💾 Guardando datos completos en ml_ordenes.json...")
    with open('ml_ordenes.json', 'w', encoding='utf-8') as f:
        json.dump(orders_data, f, indent=4, ensure_ascii=False)
    
    print("\n✅ ¡Listo! Podés ver el JSON completo en: ml_ordenes.json")
    print("\n" + "="*70)
    print("\n🎯 DATOS QUE PODÉS USAR PARA TU SISTEMA:")
    print("   ✅ ID de orden (order['id'])")
    print("   ✅ Productos vendidos (order['order_items'])")
    print("   ✅ Cantidad de cada producto")
    print("   ✅ Precio y total")
    print("   ✅ Datos del comprador")
    print("   ✅ Dirección de entrega completa")
    print("   ✅ Fecha de venta")
    print("\n" + "="*70)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n⚠️ Verificá que:")
    print("   1. El ACCESS_TOKEN sea correcto")
    print("   2. El token no haya expirado (dura ~6 horas)")
    print("   3. Tengas instalado 'requests': pip install requests")

print("\n")
